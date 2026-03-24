"""
One-time script to collect real product data for the validation set.
Uses ~50 SerpAPI searches (~500-1,000 real products).

Run once:
    python data/collect_real_data.py

Output:
    data/raw_scraped.json
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import os
from app.scraping.google_shopping import GoogleShoppingScraper
from app.scraping.ebay import EbayScraper

# 50 searches × ~20 results = ~1,000 raw products
# Covers 8 categories with high/low risk mix
SEARCHES = [
    # Electronics
    {"query": "iphone 13",              "platform": "both",   "category": "iphone"},
    {"query": "iphone 13 used",         "platform": "ebay",   "category": "iphone"},
    {"query": "iphone 13 pro",          "platform": "both",   "category": "iphone"},
    {"query": "gaming laptop",          "platform": "both",   "category": "gaming_laptop"},
    {"query": "asus rog laptop",        "platform": "both",   "category": "gaming_laptop"},
    {"query": "macbook pro used",       "platform": "ebay",   "category": "gaming_laptop"},
    {"query": "airpods pro",            "platform": "both",   "category": "headphones"},
    {"query": "sony wh-1000xm5",        "platform": "both",   "category": "headphones"},
    {"query": "bose quietcomfort",      "platform": "google", "category": "headphones"},
    {"query": "ps5 console",            "platform": "both",   "category": "ps5"},
    {"query": "playstation 5 bundle",   "platform": "ebay",   "category": "ps5"},
    # Vehicles
    {"query": "used cars under 5000",   "platform": "ebay",   "category": "used_car"},
    {"query": "honda civic used",       "platform": "ebay",   "category": "used_car"},
    {"query": "toyota camry used",      "platform": "ebay",   "category": "used_car"},
    {"query": "ford f-150 used",        "platform": "ebay",   "category": "used_car"},
    # Books / Collectibles
    {"query": "marvel comic books",     "platform": "both",   "category": "books"},
    {"query": "first edition books",    "platform": "ebay",   "category": "books"},
    {"query": "rare vintage books",     "platform": "ebay",   "category": "books"},
    {"query": "pokemon cards",          "platform": "both",   "category": "books"},
    # Home
    {"query": "hair dryer",             "platform": "both",   "category": "hair_dryer"},
    {"query": "dyson hair dryer",       "platform": "both",   "category": "hair_dryer"},
    {"query": "professional hair dryer","platform": "google", "category": "hair_dryer"},
    # Furniture
    {"query": "sofa couch",             "platform": "google", "category": "furniture"},
    {"query": "office desk",            "platform": "both",   "category": "furniture"},
    {"query": "dining table set",       "platform": "google", "category": "furniture"},
    # Luxury / High-risk
    {"query": "rolex watch used",       "platform": "ebay",   "category": "luxury_watch"},
    {"query": "designer handbag",       "platform": "ebay",   "category": "luxury_handbag"},
]

RESULTS_PER_SEARCH = 20
MAX_SEARCHES       = 50   # hard cap — never exceed free tier quota carelessly


def collect():
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        print("ERROR: SERPAPI_KEY not set in .env")
        return

    google = GoogleShoppingScraper(api_key=api_key)
    ebay   = EbayScraper(api_key=api_key)

    all_products = []
    search_count = 0

    for search in SEARCHES:
        if search_count >= MAX_SEARCHES:
            print(f"\nReached {MAX_SEARCHES}-search safety limit. Stopping.")
            break

        query    = search["query"]
        platform = search["platform"]
        category = search["category"]

        print(f"[{search_count + 1}] '{query}' ({platform})")

        if platform in ("google", "both"):
            try:
                products = google.search(query=query, num_results=RESULTS_PER_SEARCH)
                for p in products:
                    p["category"]     = category
                    p["search_query"] = query
                all_products.extend(products)
                search_count += 1
                print(f"    Google: {len(products)} products")
            except Exception as e:
                print(f"    Google error: {e}")

        if platform in ("ebay", "both"):
            try:
                products = ebay.search(query=query, num_results=RESULTS_PER_SEARCH)
                for p in products:
                    p["category"]     = category
                    p["search_query"] = query
                all_products.extend(products)
                search_count += 1
                print(f"    eBay:   {len(products)} products")
            except Exception as e:
                print(f"    eBay error: {e}")

    out = Path(__file__).parent / "raw_scraped.json"
    with open(out, "w") as f:
        json.dump(all_products, f, indent=2)

    print(f"\nCollected {len(all_products):,} products from {search_count} searches")
    print(f"Saved to {out}")

    from collections import Counter
    cats = Counter(p.get("category", "unknown") for p in all_products)
    print("\nCategory breakdown:")
    for cat, count in cats.most_common():
        print(f"  {cat:<25} {count}")

    print("\nNext step: python data/llm_labeler.py")


if __name__ == "__main__":
    collect()
