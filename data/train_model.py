"""
Train XGBoost fraud classifier.

Strategy:
  - Train on synthetic dataset (10k labeled products)
  - Evaluate on held-out synthetic test set (20%)
  - Evaluate on real validation set (714 LLM-labeled products)
  - Report comparison vs rule-based baseline

Usage:
    python data/train_model.py

Output:
    data/fraud_model.pkl        (saved model — loaded by API at startup)
    data/training_results.json  (metrics + feature importance)
"""

import json
import pickle
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

DATA_DIR = Path(__file__).parent


# ── Feature preparation ───────────────────────────────────────────────────────

def featurize(products, detector, classifier):
    """
    Compute price percentiles within category groups (mirrors real search
    behaviour), then extract XGBoost feature vectors.
    """
    by_category = defaultdict(list)
    for p in products:
        by_category[p.get("category", "unknown")].append(p)

    rows = []
    for cat_products in by_category.values():
        for product in cat_products:
            if len(cat_products) >= 5:
                tier = detector._classify_price_tier(
                    product.get("price", 0), cat_products
                )
                product["price_percentile"] = tier["percentile"]
            else:
                product["price_percentile"] = 50.0

            features = classifier.extract_features(product)
            label    = 1 if product.get("true_label") == "fraud" else 0
            rows.append((features, label))

    return rows


# ── Metrics ───────────────────────────────────────────────────────────────────

def metrics(y_true, y_pred, y_prob):
    from sklearn.metrics import (
        precision_score, recall_score, f1_score,
        accuracy_score, roc_auc_score,
    )
    auc = roc_auc_score(y_true, y_prob) if len(set(y_true)) > 1 else 0.0
    return {
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
        "recall":    round(recall_score(y_true, y_pred,    zero_division=0), 4),
        "f1":        round(f1_score(y_true, y_pred,        zero_division=0), 4),
        "accuracy":  round(accuracy_score(y_true, y_pred),                   4),
        "auc":       round(float(auc),                                        4),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def train():
    from xgboost import XGBClassifier
    from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score

    from app.models.fraud_detector import UniversalFraudDetector
    from app.models.xgb_model import XGBFraudClassifier

    # ── Load data ─────────────────────────────────────────────────────
    syn_path  = DATA_DIR / "synthetic_dataset.json"
    real_path = DATA_DIR / "validation_dataset.json"

    if not syn_path.exists():
        print("ERROR: synthetic_dataset.json not found. Run synthetic_generator.py first.")
        return

    print("Loading datasets...")
    with open(syn_path)  as f: synthetic = json.load(f)
    real = []
    if real_path.exists():
        with open(real_path) as f: real = json.load(f)

    print(f"  Synthetic : {len(synthetic):,} products")
    print(f"  Real      : {len(real):,} products")

    # ── Featurize ─────────────────────────────────────────────────────
    detector   = UniversalFraudDetector()
    classifier = XGBFraudClassifier.__new__(XGBFraudClassifier)
    classifier.model   = None
    classifier.enabled = False

    print("\nExtracting features...")
    syn_rows  = featurize(synthetic, detector, classifier)
    X_syn     = np.array([r[0] for r in syn_rows])
    y_syn     = np.array([r[1] for r in syn_rows])

    X_train, X_test, y_train, y_test = train_test_split(
        X_syn, y_syn, test_size=0.2, random_state=42, stratify=y_syn
    )
    print(f"  Train: {len(X_train):,}  |  Test: {len(X_test):,}")
    print(f"  Fraud rate (train): {y_train.mean():.1%}")

    # ── Train ─────────────────────────────────────────────────────────
    print("\nTraining XGBoost...")
    scale = float((y_train == 0).sum() / max((y_train == 1).sum(), 1))
    model = XGBClassifier(
        n_estimators      = 300,
        max_depth         = 6,
        learning_rate     = 0.05,
        subsample         = 0.8,
        colsample_bytree  = 0.8,
        scale_pos_weight  = scale,
        random_state      = 42,
        eval_metric       = "logloss",
        verbosity         = 0,
    )
    model.fit(X_train, y_train)

    # ── Evaluate: synthetic test set ──────────────────────────────────
    print("\n── Synthetic test set (20% holdout) ──────────────────")
    syn_m = metrics(y_test, model.predict(X_test), model.predict_proba(X_test)[:, 1])
    for k, v in syn_m.items():
        print(f"  {k:<12} {v}")

    # ── Evaluate: real validation set ─────────────────────────────────
    real_m = None
    if real:
        print("\n── Real validation set (LLM-labeled) ────────────────")
        real_rows = featurize(real, detector, classifier)
        X_real    = np.array([r[0] for r in real_rows])
        y_real    = np.array([r[1] for r in real_rows])

        real_m = metrics(y_real, model.predict(X_real), model.predict_proba(X_real)[:, 1])
        for k, v in real_m.items():
            print(f"  {k:<12} {v}")

        # Comparison vs rule-based baseline
        print("\n── vs rule-based baseline ────────────────────────────")
        print(f"  {'Metric':<12} {'XGBoost':>10} {'Rule-based':>12}")
        print(f"  {'-'*36}")
        baseline = {"f1": 0.8452, "auc": 0.9357, "precision": 0.9322, "recall": 0.7730}
        for k in ["precision", "recall", "f1", "auc"]:
            xgb_val  = real_m[k]
            base_val = baseline.get(k, 0)
            delta    = xgb_val - base_val
            arrow    = "▲" if delta > 0 else "▼"
            print(f"  {k:<12} {xgb_val:>10.4f} {base_val:>12.4f}  {arrow}{abs(delta):.4f}")

    # ── Cross-validation ──────────────────────────────────────────────
    print("\n── 5-fold cross-validation (synthetic) ──────────────")
    cv       = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X_syn, y_syn, cv=cv, scoring="f1")
    print(f"  F1: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # ── Feature importance ────────────────────────────────────────────
    importance = dict(sorted(
        zip(XGBFraudClassifier.FEATURE_NAMES, model.feature_importances_),
        key=lambda x: x[1], reverse=True,
    ))
    print("\n── Feature importance ────────────────────────────────")
    for feat, imp in importance.items():
        bar = "█" * int(imp * 60)
        print(f"  {feat:<25} {imp:.4f}  {bar}")

    # ── Save ──────────────────────────────────────────────────────────
    model_path = DATA_DIR / "fraud_model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    print(f"\nSaved model → {model_path}")

    results = {
        "synthetic_test":    syn_m,
        "real_validation":   real_m,
        "cv_f1_mean":        round(float(cv_scores.mean()), 4),
        "cv_f1_std":         round(float(cv_scores.std()),  4),
        "feature_importance": {k: round(float(v), 4) for k, v in importance.items()},
        "n_train":           len(X_train),
        "n_features":        len(XGBFraudClassifier.FEATURE_NAMES),
        "features":          XGBFraudClassifier.FEATURE_NAMES,
        "baseline_real":     {"f1": 0.8452, "auc": 0.9357},
    }
    results_path = DATA_DIR / "training_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved results → {results_path}")
    print("\n✅ Restart the server to load the XGBoost model.")


if __name__ == "__main__":
    train()
