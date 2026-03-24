"""
Labels real scraped products using Groq LLM + rule-based consensus.
Products where both methods agree become the validation set.

Run after collect_real_data.py:
    python data/llm_labeler.py

Output:
    data/validation_dataset.json   (agreed labels only — use for evaluation)
    data/labeling_summary.json     (stats: agreement rate, category breakdown)
"""

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.models.fraud_detector import UniversalFraudDetector


def _rule_label(product: Dict, all_products: List[Dict], detector: UniversalFraudDetector) -> str:
    score, _ = detector._calculate_risk(product, all_products)
    return "fraud" if detector._get_risk_level(score) == "HIGH" else "legitimate"


def _llm_label(product: Dict, client, model: str) -> Optional[str]:
    try:
        prompt = (
            f"You are a fraud detection expert. Label this e-commerce listing.\n\n"
            f"Product : {product.get('title', 'Unknown')}\n"
            f"Price   : ${product.get('price', 0)}\n"
            f"Platform: {product.get('platform', 'unknown')}\n"
            f"Rating  : {product.get('rating', 0)}/5\n"
            f"Reviews : {product.get('reviews', 0)}\n"
            f"Seller  : {product.get('seller', {}).get('name', 'Unknown')}\n"
            f"Condition: {product.get('condition', 'unknown')}\n\n"
            f"Respond with ONLY one word: FRAUD or LEGITIMATE"
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=10,
        )
        answer = resp.choices[0].message.content.strip().upper()
        if "FRAUD" in answer:
            return "fraud"
        if "LEGITIMATE" in answer:
            return "legitimate"
        return None
    except Exception as e:
        print(f"    LLM error: {e}")
        return None


def label(max_products: int = 1000):
    raw_path = Path(__file__).parent / "raw_scraped.json"
    if not raw_path.exists():
        print("ERROR: raw_scraped.json not found. Run collect_real_data.py first.")
        return

    with open(raw_path) as f:
        raw = json.load(f)

    detector = UniversalFraudDetector()
    if not detector.llm_explainer.enabled:
        print("ERROR: GROQ_API_KEY not set.")
        return

    client = detector.llm_explainer.client
    model  = detector.llm_explainer.fast_model

    # Filter products without prices
    products = [p for p in raw if p.get("price", 0) > 0][:max_products]
    print(f"Labeling {len(products):,} products...")

    labeled   = []
    agreements = 0

    for i, product in enumerate(products):
        if i % 100 == 0 and i > 0:
            rate = agreements / i
            print(f"  {i}/{len(products)} — agreement rate so far: {rate:.1%}")

        rule = _rule_label(product, products, detector)
        llm  = _llm_label(product, client, model)

        product["rule_label"]    = rule
        product["llm_label"]     = llm
        product["labels_agree"]  = (llm == rule)
        product["true_label"]    = rule if (llm == rule) else None
        labeled.append(product)

        if llm == rule:
            agreements += 1

    validation = [p for p in labeled if p["true_label"] is not None]
    agreement_rate = agreements / len(products) if products else 0

    fraud_count = sum(1 for p in validation if p["true_label"] == "fraud")
    legit_count = sum(1 for p in validation if p["true_label"] == "legitimate")

    print(f"\nLabeling complete")
    print(f"  Total processed  : {len(products):,}")
    print(f"  Agreement rate   : {agreement_rate:.1%}")
    print(f"  Validation set   : {len(validation):,}")
    print(f"  Fraud            : {fraud_count:,}")
    print(f"  Legitimate       : {legit_count:,}")

    out = Path(__file__).parent / "validation_dataset.json"
    with open(out, "w") as f:
        json.dump(validation, f, indent=2)

    summary = {
        "total_processed":    len(products),
        "agreement_rate":     round(agreement_rate, 4),
        "validation_set_size": len(validation),
        "fraud_count":        fraud_count,
        "legitimate_count":   legit_count,
        "categories":         dict(Counter(p.get("category", "unknown") for p in validation)),
    }
    summary_out = Path(__file__).parent / "labeling_summary.json"
    with open(summary_out, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nSaved validation set  → {out}")
    print(f"Saved labeling summary → {summary_out}")
    print(f"\nNext step: curl http://localhost:8000/api/evaluate")


if __name__ == "__main__":
    label()
