# app/scraping/base_scraper.py

from abc import ABC, abstractmethod
from typing import Dict, List
import time
import re

class BaseScraper(ABC):
    """Base class for all scrapers"""
    
    def __init__(self):
        self.results = []
        self.rate_limit_delay = 1  # seconds between requests
    
    @abstractmethod
    def search(self, query: str, **kwargs) -> List[Dict]:
        """Search for products"""
        pass
    
    @abstractmethod
    def parse_product(self, raw_data: Dict) -> Dict:
        """Parse raw product data into standard format"""
        pass
    
    def normalize_price(self, price_str: str) -> float:
        """Convert price string to float"""
        if not price_str:
            return 0.0
        
        try:
            # Remove currency symbols, commas, and extra text
            cleaned = re.sub(r'[^\d.]', '', str(price_str))
            return float(cleaned) if cleaned else 0.0
        except:
            return 0.0
    
    def rate_limit(self):
        """Simple rate limiting"""
        time.sleep(self.rate_limit_delay)