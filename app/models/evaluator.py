# app/models/evaluator.py

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .fraud_detector import UniversalFraudDetector
from .xgb_model import XGBFraudClassifier


class FraudDetectionEvaluator:
    """
    Evaluates fraud detector performance against labeled datasets.

    Scoring is done within category groups (e.g. iPhones vs iPhones)
    to match real-world percentile calculation behaviour.

    Metrics: precision, recall, F1, AUC (ROC), confusion matrix,
             per-category breakdown, threshold sensitivity analysis.
    """

    DATA_DIR = Path(__file__).parent.parent.parent / "data"

    def __init__(self):
        self.detector        = UniversalFraudDetector()
        self.xgb_classifier  = self.detector.xgb_classifier

    # ── Public API ────────────────────────────────────────────────────

    def evaluate(
        self,
        labeled_products: List[Dict],
        threshold: float = 0.55,
        sample_size: Optional[int] = None,
    ) -> Dict:
        """
        Run evaluation on a labeled dataset.

        Each product must have:
            true_label  : 'fraud' | 'legitimate'
            category    : product category string (for grouped scoring)

        Args:
            labeled_products : list of labeled product dicts
            threshold        : risk score cutoff for fraud classification
            sample_size      : if set, randomly sample this many products first

        Returns:
            Full metrics dict including per-category breakdown and
            threshold sensitivity analysis.
        """
        if not labeled_products:
            return {"error": "Empty dataset"}

        import random
        products = [p.copy() for p in labeled_products]
        if sample_size and len(products) > sample_size:
            products = random.sample(products, sample_size)

        # Score within category groups (mirrors real search behaviour)
        scored = self._score_by_category(products)

        y_true   = [1 if p["true_label"] == "fraud" else 0 for p in scored]
        y_scores = [p["predicted_score"] for p in scored]
        y_pred   = [1 if s >= threshold else 0 for s in y_scores]

        rule_metrics = self._compute_metrics(y_true, y_pred, y_scores)
        rule_metrics.update({
            "threshold":          threshold,
            "dataset_size":       len(scored),
            "fraud_rate":         round(sum(y_true) / len(y_true), 3),
            "per_category":       self._per_category_metrics(scored, threshold),
            "threshold_analysis": self._threshold_analysis(y_true, y_scores),
            "evaluated_at":       datetime.utcnow().isoformat(),
        })

        # XGBoost evaluation (when model is available)
        xgb_metrics = None
        if self.xgb_classifier.enabled:
            xgb_scores = self.xgb_classifier.predict_batch(scored)
            xgb_pred   = [1 if s >= 0.5 else 0 for s in xgb_scores]
            xgb_metrics = self._compute_metrics(y_true, xgb_pred, xgb_scores)
            xgb_metrics.update({
                "threshold":          0.5,
                "dataset_size":       len(scored),
                "fraud_rate":         round(sum(y_true) / len(y_true), 3),
                "per_category":       self._per_category_metrics_xgb(scored, xgb_scores, xgb_pred),
                "threshold_analysis": self._threshold_analysis(y_true, xgb_scores),
                "feature_importance": self.xgb_classifier.feature_importance(),
            })

        result = {"rule_based": rule_metrics}
        if xgb_metrics:
            result["xgboost"]     = xgb_metrics
            result["improvement"] = {
                k: round(xgb_metrics[k] - rule_metrics[k], 4)
                for k in ["precision", "recall", "f1", "accuracy", "auc"]
            }
        return result

    def evaluate_from_file(
        self,
        path: Optional[str] = None,
        threshold: float = 0.55,
        sample_size: Optional[int] = None,
    ) -> Dict:
        """
        Load dataset from JSON file and evaluate.
        Defaults to data/validation_dataset.json, then data/synthetic_dataset.json.
        """
        if path:
            dataset_path = Path(path)
        elif (self.DATA_DIR / "validation_dataset.json").exists():
            dataset_path = self.DATA_DIR / "validation_dataset.json"
            source = "real (scraped + LLM-labeled)"
        elif (self.DATA_DIR / "synthetic_dataset.json").exists():
            dataset_path = self.DATA_DIR / "synthetic_dataset.json"
            source = "synthetic"
        else:
            return {
                "error": "No dataset found. Run data/synthetic_generator.py or data/collect_real_data.py first.",
                "instructions": {
                    "synthetic": "python data/synthetic_generator.py",
                    "real":      "python data/collect_real_data.py && python data/llm_labeler.py",
                }
            }

        with open(dataset_path) as f:
            products = json.load(f)

        result = self.evaluate(products, threshold=threshold, sample_size=sample_size)
        result["dataset_source"] = source if "source" in dir() else str(dataset_path.name)
        result["dataset_path"]   = str(dataset_path)
        result["evaluated_at"]   = datetime.utcnow().isoformat()
        return result

    # ── Scoring ───────────────────────────────────────────────────────

    def _score_by_category(self, products: List[Dict]) -> List[Dict]:
        """Score each product within its category group for accurate percentiles."""
        by_category = defaultdict(list)
        for p in products:
            by_category[p.get("category", "unknown")].append(p)

        scored = []
        for cat_products in by_category.values():
            for product in cat_products:
                score, factors = self.detector._calculate_risk(product, cat_products)
                product["predicted_score"] = round(score, 4)
                product["predicted_level"] = self.detector._get_risk_level(score)
                product["risk_factors"]    = factors
            scored.extend(cat_products)
        return scored

    # ── Metrics ───────────────────────────────────────────────────────

    def _compute_metrics(
        self,
        y_true:   List[int],
        y_pred:   List[int],
        y_scores: List[float],
    ) -> Dict:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
        tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)

        precision = tp / (tp + fp)        if (tp + fp) > 0 else 0.0
        recall    = tp / (tp + fn)        if (tp + fn) > 0 else 0.0
        f1        = (2 * precision * recall / (precision + recall)
                     if (precision + recall) > 0 else 0.0)
        accuracy  = (tp + tn) / len(y_true) if y_true else 0.0
        auc       = self._compute_auc(y_true, y_scores)

        return {
            "precision":        round(precision, 4),
            "recall":           round(recall,    4),
            "f1":               round(f1,        4),
            "accuracy":         round(accuracy,  4),
            "auc":              round(auc,       4),
            "confusion_matrix": {
                "true_positive":  tp,
                "false_positive": fp,
                "true_negative":  tn,
                "false_negative": fn,
            },
        }

    def _compute_auc(self, y_true: List[int], y_scores: List[float]) -> float:
        """ROC AUC via trapezoidal rule — no sklearn required."""
        n_pos = sum(y_true)
        n_neg = len(y_true) - n_pos
        if n_pos == 0 or n_neg == 0:
            return 0.0

        pairs = sorted(zip(y_scores, y_true), key=lambda x: x[0], reverse=True)

        tpr_pts, fpr_pts = [0.0], [0.0]
        tp = fp = 0
        for score, label in pairs:
            if label == 1:
                tp += 1
            else:
                fp += 1
            tpr_pts.append(tp / n_pos)
            fpr_pts.append(fp / n_neg)

        auc = 0.0
        for i in range(1, len(fpr_pts)):
            auc += (fpr_pts[i] - fpr_pts[i - 1]) * (tpr_pts[i] + tpr_pts[i - 1]) / 2
        return auc

    def _per_category_metrics(
        self, products: List[Dict], threshold: float
    ) -> Dict:
        by_cat = defaultdict(list)
        for p in products:
            by_cat[p.get("category", "unknown")].append(p)

        result = {}
        for cat, cat_products in by_cat.items():
            y_true   = [1 if p["true_label"] == "fraud" else 0 for p in cat_products]
            y_scores = [p["predicted_score"] for p in cat_products]
            y_pred   = [1 if s >= threshold else 0 for s in y_scores]
            m = self._compute_metrics(y_true, y_pred, y_scores)
            m["count"] = len(cat_products)
            result[cat] = m
        return result

    def _per_category_metrics_xgb(
        self, products: List[Dict], xgb_scores: List[float], xgb_pred: List[int]
    ) -> Dict:
        by_cat: Dict[str, list] = defaultdict(list)
        for p, score, pred in zip(products, xgb_scores, xgb_pred):
            by_cat[p.get("category", "unknown")].append((p, score, pred))

        result = {}
        for cat, items in by_cat.items():
            y_true = [1 if i[0]["true_label"] == "fraud" else 0 for i in items]
            scores = [i[1] for i in items]
            preds  = [i[2] for i in items]
            m = self._compute_metrics(y_true, preds, scores)
            m["count"] = len(items)
            result[cat] = m
        return result

    def _threshold_analysis(
        self, y_true: List[int], y_scores: List[float]
    ) -> List[Dict]:
        """Precision/recall/F1 at multiple thresholds to surface the optimal cutoff."""
        results = []
        for t in [0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]:
            y_pred = [1 if s >= t else 0 for s in y_scores]
            m = self._compute_metrics(y_true, y_pred, y_scores)
            results.append({
                "threshold": t,
                "precision": m["precision"],
                "recall":    m["recall"],
                "f1":        m["f1"],
            })
        return results
