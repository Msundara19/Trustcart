"""
Synthetic dataset generator for TrustCart fraud detection benchmark.

Generates labeled e-commerce product listings across 8 categories
using realistic price distributions and documented fraud patterns.

Usage:
    python data/synthetic_generator.py

Output:
    data/synthetic_dataset.json  (~10k labeled products)
"""

import json
import random
from pathlib import Path
from typing import Dict, List

import numpy as np

random.seed(42)
np.random.seed(42)

# ── Category definitions ──────────────────────────────────────────────────────

CATEGORIES: Dict[str, Dict] = {
    "iphone": {
        "titles":              ["iPhone 13", "iPhone 13 Pro", "iPhone 14", "iPhone 12", "iPhone 13 Mini"],
        "price_mean":          550,
        "price_std":           150,
        "price_min":           80,
        "price_max":           1200,
        "fraud_price_max":     150,   # below this → strong fraud signal
        "suspicious_price_max": 280,  # below this → suspicious
        "trusted_sellers":     ["apple store", "best buy", "walmart", "target", "verizon", "at&t"],
        "conditions":          ["new", "used", "refurbished"],
    },
    "gaming_laptop": {
        "titles":              ["Gaming Laptop", "ASUS ROG Laptop", "Alienware Laptop", "MSI Gaming Laptop", "Razer Blade"],
        "price_mean":          1100,
        "price_std":           400,
        "price_min":           150,
        "price_max":           3500,
        "fraud_price_max":     200,
        "suspicious_price_max": 450,
        "trusted_sellers":     ["best buy", "walmart", "newegg", "dell", "microsoft store"],
        "conditions":          ["new", "used", "refurbished"],
    },
    "used_car": {
        "titles":              ["Honda Civic Used", "Toyota Camry Used", "Ford F-150 Used", "Chevy Silverado", "Toyota Corolla"],
        "price_mean":          9000,
        "price_std":           6000,
        "price_min":           500,
        "price_max":           45000,
        "fraud_price_max":     800,
        "suspicious_price_max": 2000,
        "trusted_sellers":     ["carmax", "carvana", "autotrader"],
        "conditions":          ["used"],
    },
    "books": {
        "titles":              ["Marvel Comic Book", "First Edition Novel", "Rare Vintage Book", "Textbook", "Collectible Comic"],
        "price_mean":          25,
        "price_std":           30,
        "price_min":           2,
        "price_max":           500,
        "fraud_price_max":     1,
        "suspicious_price_max": 4,
        "trusted_sellers":     ["barnes & noble", "books a million", "abebooks"],
        "conditions":          ["new", "used"],
    },
    "hair_dryer": {
        "titles":              ["Dyson Supersonic Hair Dryer", "Professional Hair Dryer", "Ionic Hair Dryer", "Travel Hair Dryer"],
        "price_mean":          85,
        "price_std":           65,
        "price_min":           5,
        "price_max":           500,
        "fraud_price_max":     12,
        "suspicious_price_max": 20,
        "trusted_sellers":     ["target", "walmart", "ulta", "dyson", "best buy"],
        "conditions":          ["new", "refurbished"],
    },
    "ps5": {
        "titles":              ["PS5 Console", "PlayStation 5 Bundle", "PS5 Digital Edition", "PlayStation 5 Disc"],
        "price_mean":          480,
        "price_std":           70,
        "price_min":           50,
        "price_max":           900,
        "fraud_price_max":     100,
        "suspicious_price_max": 220,
        "trusted_sellers":     ["sony", "best buy", "walmart", "target", "gamestop"],
        "conditions":          ["new", "used"],
    },
    "headphones": {
        "titles":              ["AirPods Pro", "Sony WH-1000XM5", "Bose QuietComfort 45", "Jabra Evolve2", "Beats Studio Pro"],
        "price_mean":          200,
        "price_std":           110,
        "price_min":           12,
        "price_max":           650,
        "fraud_price_max":     18,
        "suspicious_price_max": 50,
        "trusted_sellers":     ["apple", "best buy", "target", "walmart", "sony"],
        "conditions":          ["new", "used", "refurbished"],
    },
    "furniture": {
        "titles":              ["Modern Sofa Couch", "Dining Table Set", "L-Shaped Office Desk", "Sectional Sofa", "Platform Bed Frame"],
        "price_mean":          650,
        "price_std":           450,
        "price_min":           40,
        "price_max":           5000,
        "fraud_price_max":     25,
        "suspicious_price_max": 70,
        "trusted_sellers":     ["ikea", "wayfair", "west elm", "crate & barrel", "target"],
        "conditions":          ["new", "used"],
    },
}

FRAUD_SELLERS = [
    "quick_deals_99", "bestprice_store", "amazingdeals2024", "cheap_tech_hub",
    "super_saver_shop", "deal_hunter_pro", "bargain_basement", "flash_sale_king",
    "ebay_seller_123", "unknown_vendor", "hot_deals_online", "price_drop_zone",
    "liquidation_center", "wholesale_direct", "clearance_hub", "fast_ship_deals",
]

LEGIT_SELLERS = [
    "Best Buy", "Walmart", "Target", "Apple Store", "Amazon",
    "Dyson Official", "Sony Store", "Dell Technologies", "Newegg",
    "GameStop", "Barnes & Noble", "Ulta Beauty", "Wayfair", "IKEA",
    "Microsoft Store", "CarMax", "Carvana",
]

PLATFORMS = ["google_shopping", "ebay"]

# ── Product generators ────────────────────────────────────────────────────────

def _fraud_product(category: str, cfg: Dict) -> Dict:
    fraud_type = random.choice(["extremely_cheap", "no_reviews_cheap", "low_rating"])

    if fraud_type == "extremely_cheap":
        price   = round(random.uniform(cfg["price_min"], cfg["fraud_price_max"]), 2)
        rating  = round(random.uniform(0, 2.5), 1)
        reviews = random.randint(0, 5)
    elif fraud_type == "no_reviews_cheap":
        price   = round(random.uniform(cfg["fraud_price_max"], cfg["suspicious_price_max"]), 2)
        rating  = 0
        reviews = 0
    else:  # low_rating
        price   = round(random.uniform(cfg["suspicious_price_max"], cfg["price_mean"] * 0.4), 2)
        rating  = round(random.uniform(1.0, 2.8), 1)
        reviews = random.randint(1, 20)

    base_title  = random.choice(cfg["titles"])
    condition   = random.choice(cfg["conditions"])
    seller_name = random.choice(FRAUD_SELLERS)
    platform    = random.choice(PLATFORMS)

    title = random.choice([
        f"{base_title} - AMAZING DEAL!!!",
        f"CHEAP {base_title} MUST GO",
        f"{base_title} {condition} LOW PRICE",
        f"FAST SHIP {base_title} deal",
        f"{base_title} urgent sale",
    ])

    return {
        "title":         title,
        "price":         max(round(price, 2), 0.01),
        "rating":        rating,
        "reviews":       reviews,
        "quantity_sold": random.randint(0, 8),   # fraud listings rarely have many sales
        "platform":      platform,
        "source":        seller_name,
        "condition":     condition,
        "category":      category,
        "seller":    {
            "name":         seller_name,
            "rating":       round(random.uniform(0, 2.5), 1) if random.random() > 0.3 else 0,
            "reviews":      random.randint(0, 50),
            "feedback_pct": round(random.uniform(40, 85), 1),
            "link":         "",
        },
        "link":        f"https://{platform}.com/item/{random.randint(100000, 999999)}",
        "thumbnail":   "",
        "true_label":  "fraud",
        "fraud_type":  fraud_type,
    }


def _legit_product(category: str, cfg: Dict) -> Dict:
    price   = float(np.clip(np.random.normal(cfg["price_mean"], cfg["price_std"]),
                            cfg["price_min"] * 2, cfg["price_max"]))
    rating  = round(random.uniform(3.8, 5.0), 1)
    reviews = random.randint(50, 10000)

    base_title  = random.choice(cfg["titles"])
    condition   = random.choice(cfg["conditions"])
    seller_name = random.choice(LEGIT_SELLERS + cfg["trusted_sellers"])
    platform    = random.choice(PLATFORMS)

    title = random.choice([
        f"{base_title} - {condition.capitalize()}",
        f"{base_title} with Warranty",
        f"Certified {base_title}",
        f"{base_title} {random.randint(2022, 2024)} Model",
        f"{seller_name} {base_title}",
    ])

    qty           = random.randint(50, 8000)
    feedback_pct  = round(random.uniform(97, 100), 1)
    seller_reviews_count = random.randint(200, 80000)

    return {
        "title":         title,
        "price":         round(price, 2),
        "rating":        rating,
        "reviews":       reviews,
        "quantity_sold": qty,
        "platform":      platform,
        "source":        seller_name.lower(),
        "condition":     condition,
        "category":      category,
        "seller":    {
            "name":         seller_name,
            "rating":       round(random.uniform(4.0, 5.0), 1),
            "reviews":      seller_reviews_count,
            "feedback_pct": feedback_pct,
            "link":         "",
        },
        "link":       f"https://{platform}.com/item/{random.randint(100000, 999999)}",
        "thumbnail":  "",
        "true_label": "legitimate",
        "fraud_type": None,
    }


def _edge_case(category: str, cfg: Dict) -> Dict:
    """Ambiguous products — cheaper but not obviously fraudulent."""
    price   = round(random.uniform(cfg["suspicious_price_max"], cfg["price_mean"] * 0.5), 2)
    rating  = round(random.uniform(2.5, 4.0), 1)
    reviews = random.randint(1, 30)

    base_title  = random.choice(cfg["titles"])
    condition   = random.choice(["used", "refurbished", "unknown"])
    seller_name = random.choice(FRAUD_SELLERS)
    platform    = "ebay"

    # Label based on how far below typical price
    true_label = "fraud" if (price / cfg["price_mean"]) < 0.3 else "legitimate"

    return {
        "title":         f"{base_title} {condition} - good deal",
        "price":         max(price, 0.01),
        "rating":        rating,
        "reviews":       reviews,
        "quantity_sold": random.randint(0, 60),
        "platform":      platform,
        "source":        seller_name,
        "condition":     condition,
        "category":      category,
        "seller":    {
            "name":         seller_name,
            "rating":       round(random.uniform(2.5, 4.0), 1),
            "reviews":      random.randint(10, 500),
            "feedback_pct": round(random.uniform(70, 97), 1),
            "link":         "",
        },
        "link":       f"https://ebay.com/item/{random.randint(100000, 999999)}",
        "thumbnail":  "",
        "true_label": true_label,
        "fraud_type": "edge_case",
    }


# ── Main generator ────────────────────────────────────────────────────────────

def generate(n_total: int = 10000) -> List[Dict]:
    """
    Generate a balanced labeled dataset.
    Distribution per category: 35% fraud, 45% legitimate, 20% edge cases.
    """
    categories  = list(CATEGORIES.keys())
    n_per_cat   = n_total // len(categories)
    dataset: List[Dict] = []

    for cat in categories:
        cfg    = CATEGORIES[cat]
        n_f    = int(n_per_cat * 0.35)
        n_l    = int(n_per_cat * 0.45)
        n_e    = n_per_cat - n_f - n_l

        for _ in range(n_f): dataset.append(_fraud_product(cat, cfg))
        for _ in range(n_l): dataset.append(_legit_product(cat, cfg))
        for _ in range(n_e): dataset.append(_edge_case(cat, cfg))

    random.shuffle(dataset)
    return dataset


if __name__ == "__main__":
    print("Generating synthetic dataset...")
    dataset = generate(10000)

    fraud_count = sum(1 for p in dataset if p["true_label"] == "fraud")
    legit_count = sum(1 for p in dataset if p["true_label"] == "legitimate")

    print(f"Generated {len(dataset):,} products")
    print(f"  Fraud:      {fraud_count:,} ({fraud_count / len(dataset):.1%})")
    print(f"  Legitimate: {legit_count:,} ({legit_count / len(dataset):.1%})")

    from collections import Counter
    cats = Counter(p["category"] for p in dataset)
    print("\nCategory breakdown:")
    for cat, count in cats.most_common():
        print(f"  {cat:<20} {count:,}")

    out = Path(__file__).parent / "synthetic_dataset.json"
    with open(out, "w") as f:
        json.dump(dataset, f, indent=2)

    print(f"\nSaved to {out}")
