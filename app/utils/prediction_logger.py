# app/utils/prediction_logger.py

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


class PredictionLogger:
    """
    Appends per-product prediction records to a rotating JSONL log.

    Each line is a self-contained JSON object — easy to tail, grep, or
    stream into a re-training pipeline without loading the whole file.

    Rotation: a new file is started each calendar day (UTC).
    File path: data/prediction_logs/YYYY-MM-DD.jsonl

    Records include:
        query, platform, title, price, risk_score, risk_level,
        xgb_score, xgb_risk_level, duplicate_group, is_cross_platform,
        timestamp (ISO-8601 UTC)
    """

    LOG_DIR = Path(__file__).parent.parent.parent / "data" / "prediction_logs"

    def __init__(self):
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)

    # ── Public API ────────────────────────────────────────────────────

    def log_search(self, query: str, products: List[Dict]) -> int:
        """
        Log prediction records for all valid products in a search result.

        Returns the number of records written.
        """
        if not products:
            return 0

        log_path = self._today_log_path()
        records = [self._build_record(query, p) for p in products]

        with open(log_path, "a", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return len(records)

    def recent_stats(self, days: int = 7) -> Dict:
        """
        Return aggregate stats over the last ``days`` calendar days.

        {
            "days_covered": int,
            "total_logged": int,
            "fraud_rate": float,   # fraction of HIGH-risk predictions
            "xgb_available_rate": float,
            "log_files": [str, ...]
        }
        """
        files = sorted(self.LOG_DIR.glob("*.jsonl"))[-days:]
        total = fraud = xgb_present = 0

        for path in files:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                        total += 1
                        # Use XGBoost level when available — it's the primary classifier
                        effective_level = r.get("xgb_risk_level") or r.get("risk_level")
                        if effective_level == "HIGH":
                            fraud += 1
                        if r.get("xgb_score") is not None:
                            xgb_present += 1
                    except json.JSONDecodeError:
                        pass

        return {
            "days_covered":      len(files),
            "total_logged":      total,
            "fraud_rate":        round(fraud / total, 4) if total else 0.0,
            "xgb_available_rate": round(xgb_present / total, 4) if total else 0.0,
            "log_files":         [p.name for p in files],
        }

    # ── Internals ─────────────────────────────────────────────────────

    def _today_log_path(self) -> Path:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.LOG_DIR / f"{today}.jsonl"

    @staticmethod
    def _build_record(query: str, product: Dict) -> Dict:
        return {
            "timestamp":        datetime.now(timezone.utc).isoformat(),
            "query":            query,
            "platform":         product.get("platform", ""),
            "title":            product.get("title", ""),
            "price":            product.get("price"),
            "condition":        product.get("condition", "unknown"),
            "seller_name":      (product.get("seller") or {}).get("name", ""),
            "seller_rating":    (product.get("seller") or {}).get("rating", None),
            "rating":           product.get("rating"),
            "reviews":          product.get("reviews"),
            "risk_score":       product.get("risk_score"),
            "risk_level":       product.get("risk_level"),
            "xgb_score":        product.get("xgb_score"),
            "xgb_risk_level":   product.get("xgb_risk_level"),
            "price_percentile": product.get("price_percentile"),
            "price_tier":       product.get("price_tier"),
            "duplicate_group":  product.get("duplicate_group"),
            "is_cross_platform": product.get("is_cross_platform", False),
        }
