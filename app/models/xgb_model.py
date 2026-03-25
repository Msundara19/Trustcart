# app/models/xgb_model.py

import pickle
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np


class XGBFraudClassifier:
    """
    XGBoost-based fraud classifier.

    Trained on synthetic data, generalizes to real listings.
    Loaded automatically from data/fraud_model.pkl when available.
    Falls back gracefully — system continues with rule-based scoring if absent.
    """

    MODEL_PATH = Path(__file__).parent.parent.parent / "data" / "fraud_model.pkl"

    TRUSTED_SELLERS = [
        "target", "walmart", "best buy", "amazon", "ulta", "kohl",
        "barnes & noble", "books a million", "abebooks", "dyson",
        "ikea", "macy", "west elm", "crate & barrel", "wayfair",
    ]

    FEATURE_NAMES = [
        "log_price",
        "rating",
        "log_reviews",
        "seller_rating",
        "is_trusted",
        "platform_ebay",
        "condition_new",
        "condition_used",
        "condition_refurbished",
        "condition_unknown",
        "title_length",
        "has_rating",
        "has_reviews",
        "price_percentile",
    ]

    def __init__(self):
        self.model   = None
        self.enabled = False
        self._load()

    def _load(self):
        if self.MODEL_PATH.exists():
            try:
                with open(self.MODEL_PATH, "rb") as f:
                    self.model = pickle.load(f)
                self.enabled = True
                print("✅ XGBoost model loaded")
            except Exception as e:
                print(f"⚠️  XGBoost model failed to load: {e}")

    # ── Feature extraction ────────────────────────────────────────────

    def extract_features(self, product: Dict) -> List[float]:
        """
        Extract a fixed-length feature vector from a product dict.
        price_percentile must already be set on the product (done by
        FraudDetector._classify_price_tier before this is called).
        """
        price     = product.get("price", 0)
        rating    = product.get("rating", 0)
        reviews   = product.get("reviews", 0)
        seller    = product.get("seller", {})
        seller_nm = seller.get("name", "").lower()
        source    = product.get("source", "").lower()
        platform  = product.get("platform", "").lower()
        condition = product.get("condition", "unknown").lower()
        title     = product.get("title", "")
        pct       = product.get("price_percentile", 50)

        is_trusted = int(
            any(t in seller_nm or t in source for t in self.TRUSTED_SELLERS)
        )

        return [
            np.log1p(price),
            rating,
            np.log1p(reviews),
            seller.get("rating", 0),
            is_trusted,
            int(platform == "ebay"),
            int(condition == "new"),
            int(condition == "used"),
            int(condition == "refurbished"),
            int(condition == "unknown"),
            len(title),
            int(rating > 0),
            int(reviews > 0),
            pct,
        ]

    # ── Inference ─────────────────────────────────────────────────────

    def predict_proba(self, product: Dict) -> Optional[float]:
        """Return fraud probability [0,1] for a single product, or None if disabled."""
        if not self.enabled:
            return None
        features = np.array([self.extract_features(product)])
        return float(self.model.predict_proba(features)[0][1])

    def predict_batch(self, products: List[Dict]) -> List[Optional[float]]:
        """Return fraud probabilities for a list of products."""
        if not self.enabled:
            return [None] * len(products)
        features = np.array([self.extract_features(p) for p in products])
        return [float(s) for s in self.model.predict_proba(features)[:, 1]]

    # ── Introspection ─────────────────────────────────────────────────

    def feature_importance(self) -> Dict[str, float]:
        """Return feature importances sorted descending."""
        if not self.enabled:
            return {}
        return dict(sorted(
            {name: round(float(imp), 4)
             for name, imp in zip(self.FEATURE_NAMES, self.model.feature_importances_)}.items(),
            key=lambda x: x[1],
            reverse=True,
        ))
