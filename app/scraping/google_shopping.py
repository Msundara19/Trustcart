# app/scraping/google_shopping.py

from typing import Dict, List
from serpapi import GoogleSearch
from .base_scraper import BaseScraper
import os

class GoogleShoppingScraper(BaseScraper):
    """Scraper for Google Shopping using SerpAPI"""
    
    def __init__(self, api_key: str = None):
        super().__init__()
        # Get API key from environment or parameter
        self.api_key = api_key or os.getenv('SERPAPI_KEY')
        if not self.api_key:
            raise ValueError("SerpAPI key required. Get one at serpapi.com")
    
    def search(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        Search Google Shopping for products
        
        Args:
            query: Search term (e.g., "gaming laptop")
            num_results: Number of results to return
            
        Returns:
            List of normalized product dictionaries
        """
        params = {
            "engine": "google_shopping",
            "q": query,
            "api_key": self.api_key,
            "num": num_results,
            "gl": "us",  # country
            "hl": "en"   # language
        }
        
        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            
            # Extract shopping results
            shopping_results = results.get("shopping_results", [])
            
            # Parse each product
            products = []
            for item in shopping_results:
                try:
                    parsed = self.parse_product(item)
                    if parsed:
                        products.append(parsed)
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
            return {
                "title": raw_data.get("title", ""),
                "price": self.normalize_price(raw_data.get("price", "0")),
                "price_raw": raw_data.get("price", ""),
                "source": raw_data.get("source", ""),
                "link": raw_data.get("link", ""),
                "product_link": raw_data.get("product_link", ""),
                "thumbnail": raw_data.get("thumbnail", ""),
                "rating": raw_data.get("rating", 0),
                "reviews": raw_data.get("reviews", 0),
                "seller": {
                    "name": raw_data.get("source", ""),
                    "rating": raw_data.get("rating", 0),
                },
                "delivery": raw_data.get("delivery", ""),
                "extracted_price": self.normalize_price(raw_data.get("price", "0")),
                "product_id": raw_data.get("product_id", ""),
                "platform": "google_shopping",
                "condition": "new",  # Google Shopping mostly has new items
                "raw_data": raw_data  # Keep original for debugging
            }
        except Exception as e:
            print(f"Parse error: {e}")
            return None