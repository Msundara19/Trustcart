# app/scraping/google_shopping.py

from typing import Dict, List
from serpapi import GoogleSearch
from .base_scraper import BaseScraper
import os

class GoogleShoppingScraper(BaseScraper):
    """Scraper for Google Shopping using SerpAPI"""
    
    def __init__(self, api_key: str = None):
        super().__init__()
        self.api_key = api_key or os.getenv('SERPAPI_KEY')
        if not self.api_key:
            raise ValueError("SerpAPI key required. Get one at serpapi.com")
    
    def search(self, query: str, num_results: int = 10, max_price: int = None) -> List[Dict]:
        """
        Search Google Shopping for products
        
        Args:
            query: Search term (e.g., "gaming laptop")
            num_results: Number of results to return
            max_price: Maximum price filter (optional)
            
        Returns:
            List of normalized product dictionaries
        """
        params = {
            "engine": "google_shopping",
            "q": query,
            "api_key": self.api_key,
            "num": num_results * 2,  # Get more results to filter
            "gl": "us",
            "hl": "en"
        }
        
        # Try to add price filter (may not always work with Google Shopping API)
        if max_price:
            params["tbs"] = f"mr:1,price:1,ppr_max:{max_price}"
        
        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            
            shopping_results = results.get("shopping_results", [])
            
            products = []
            for item in shopping_results:
                try:
                    parsed = self.parse_product(item)
                    if parsed:
                        # FILTER BY MAX PRICE manually (since API filter doesn't always work)
                        if max_price is None or parsed['price'] <= max_price:
                            products.append(parsed)
                            
                            # Stop when we have enough results
                            if len(products) >= num_results:
                                break
                except Exception as e:
                    print(f"Error parsing product: {e}")
                    continue
            
            return products
            
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    def parse_product(self, raw_data: Dict) -> Dict:
        """Parse Google Shopping result into standard format"""
        try:
            # Ensure link is present
            link = raw_data.get("link") or raw_data.get("product_link") or ""
            
            return {
                "title": raw_data.get("title", ""),
                "price": self.normalize_price(raw_data.get("price", "0")),
                "price_raw": raw_data.get("price", ""),
                "source": raw_data.get("source", "Google Shopping"),
                "link": link,  # FIXED: Ensure link is always present
                "product_link": link,
                "thumbnail": raw_data.get("thumbnail", ""),
                "rating": raw_data.get("rating", 0),
                "reviews": raw_data.get("reviews", 0),
                "seller": {
                    "name": raw_data.get("source", "Unknown"),
                    "rating": raw_data.get("rating", 0),
                    "link": link
                },
                "delivery": raw_data.get("delivery", ""),
                "extracted_price": self.normalize_price(raw_data.get("price", "0")),
                "product_id": raw_data.get("product_id", ""),
                "platform": "google_shopping",
                "condition": "new",
                "raw_data": raw_data
            }
        except Exception as e:
            print(f"Parse error: {e}")
            return None