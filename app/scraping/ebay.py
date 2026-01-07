# app/scraping/ebay.py

from typing import Dict, List
from serpapi import GoogleSearch
from .base_scraper import BaseScraper
import os

class EbayScraper(BaseScraper):
    """Scraper for eBay using SerpAPI"""
    
    def __init__(self, api_key: str = None):
        super().__init__()
        self.api_key = api_key or os.getenv('SERPAPI_KEY')
        if not self.api_key:
            raise ValueError("SerpAPI key required")
    
    def search(self, query: str, num_results: int = 10, **kwargs) -> List[Dict]:
        """
        Search eBay for products
        
        kwargs:
        - max_price: int (maximum price filter)
        - condition: str ('new', 'used', 'refurbished')
        - buy_now: bool (True = Buy It Now only, False = include auctions)
        """
        max_price = kwargs.get('max_price')
        condition = kwargs.get('condition', 'all')
        buy_now_only = kwargs.get('buy_now', True)
        
        params = {
            "engine": "ebay",
            "ebay_domain": "ebay.com",
            "_nkw": query,
            "api_key": self.api_key,
        }
        
        # Add filters
        if max_price:
            params['_udhi'] = max_price
        
        if buy_now_only:
            params['LH_BIN'] = 1
        
        # Condition filter
        if condition == 'new':
            params['LH_ItemCondition'] = 3
        elif condition == 'used':
            params['LH_ItemCondition'] = 4
        elif condition == 'refurbished':
            params['LH_ItemCondition'] = 2000
        
        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            
            organic_results = results.get("organic_results", [])
            
            products = []
            for idx, item in enumerate(organic_results):
                if idx >= num_results:
                    break
                
                try:
                    parsed = self.parse_product(item)
                    if parsed:
                        products.append(parsed)
                except Exception as e:
                    print(f"Error parsing eBay product: {e}")
                    continue
            
            return products
        
        except Exception as e:
            print(f"eBay search error: {e}")
            return []
    
    def parse_product(self, raw_data: Dict) -> Dict:
        """Parse eBay result into standard format"""
        try:
            price_info = raw_data.get("price", {})
            price_raw = price_info.get("raw", "") if isinstance(price_info, dict) else str(price_info)
            
            detected_condition = self._detect_condition(raw_data)
            
            # Ensure link is always present
            product_link = raw_data.get("link", "")
            
            return {
                "title": raw_data.get("title", ""),
                "price": self.normalize_price(price_raw),
                "price_raw": price_raw,
                "source": "eBay",
                "link": product_link,  # Make sure link is here
                "product_link": product_link,
                "thumbnail": raw_data.get("thumbnail", ""),
                "rating": 0,
                "reviews": 0,
                "seller": {
                    "name": raw_data.get("seller", {}).get("name", "eBay Seller"),
                    "rating": raw_data.get("seller", {}).get("rating", 0),
                    "link": product_link
                },
                "delivery": raw_data.get("shipping", ""),
                "extracted_price": self.normalize_price(price_raw),
                "product_id": str(raw_data.get("position", "")),
                "platform": "ebay",
                "condition": detected_condition,
                "raw_data": raw_data
            }
        except Exception as e:
            print(f"eBay parse error: {e}")
            return None
    
    def _detect_condition(self, item: Dict) -> str:
        """Detect product condition from eBay listing"""
        title = item.get("title", "").lower()
        condition_info = item.get("condition", "").lower()
        
        # Check explicit condition field
        if "new" in condition_info:
            return "new"
        elif "refurbished" in condition_info or "renewed" in condition_info:
            return "refurbished"
        elif "used" in condition_info or "pre-owned" in condition_info:
            return "used"
        
        # Check title
        if any(word in title for word in ["brand new", "new in box", "nib", "sealed"]):
            return "new"
        elif any(word in title for word in ["refurbished", "renewed", "restored"]):
            return "refurbished"
        elif any(word in title for word in ["used", "pre-owned", "preowned"]):
            return "used"
        
        return "unknown"