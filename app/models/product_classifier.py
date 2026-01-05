# app/models/product_classifier.py

import re
from typing import Dict, Tuple, List

class UniversalProductClassifier:
    """
    Generic product classifier that works for ANY product category
    Filters toy versions of real products (toy cars, toy laptops, toy furniture, etc.)
    """
    
    def __init__(self):
        # Universal spam/scam indicators
        self.spam_keywords = [
            'click here', 'limited time offer', 'act now',
            'guarantee', '100% free', 'no risk',
            'buy now', 'order now', 'call now',
            'amazing deal', 'unbelievable price'
        ]
        
        # Universal toy indicators - applies to ALL product categories
        self.toy_indicators = [
            # General toy markers
            'toy', 'pretend', 'play set', 'playset', 'playhouse',
            'kids', 'children', 'toddler', 'child', 'baby',
            'for kids', 'for children', 'kids\'',
            
            # Toy brands
            'leapfrog', 'vtech', 'fisher-price', 'little tikes',
            'step2', 'melissa & doug', 'kidkraft', 'power wheels',
            
            # Educational toys
            'educational toy', 'learning toy', 'stem toy',
            
            # Size/scale indicators for toys
            'miniature', 'mini version', 'dollhouse', 'doll house',
            
            # Play/pretend keywords
            'pretend play', 'role play', 'imaginative play',
            
            # Toy-specific descriptors
            'play kitchen', 'play food', 'play tools',
            'wooden toy', 'plastic toy'
        ]
        
        # Toy-specific patterns for different categories
        self.toy_category_patterns = {
            # Toy vehicles
            'vehicle': [
                'ride on', 'ride-on', 'push car', 'pedal car',
                'remote control', 'rc ', 'r/c', 'r.c.',
                '12v', '6v', '24v battery',  # Battery-powered toys
                'electric car for kids', 'kids electric',
                'model car', 'die-cast', 'diecast', 'scale model',
                '1:24', '1:18', '1:12', '1:64', '1:43',  # Scale ratios
                'hot wheels', 'matchbox', 'tonka'
            ],
            
            # Toy furniture
            'furniture': [
                'play kitchen', 'toy kitchen', 'kids kitchen',
                'play table', 'kids table', 'toddler table',
                'play chair', 'kids chair', 'toddler chair',
                'toy storage', 'kids storage',
                'play tent', 'kids tent', 'play house',
                'doll furniture', 'dollhouse furniture',
                'plastic furniture', 'foam furniture'
            ],
            
            # Toy electronics/computers
            'electronics': [
                'toy laptop', 'kids laptop', 'learning laptop',
                'toy tablet', 'kids tablet', 'learning tablet',
                'toy phone', 'kids phone', 'play phone',
                'toy computer', 'kids computer',
                'electronic learning', 'learning system',
                'educational tablet', 'kidizoom'
            ],
            
            # Toy appliances
            'appliances': [
                'toy blender', 'play blender', 'kids blender',
                'toy vacuum', 'play vacuum', 'kids vacuum',
                'toy microwave', 'play microwave',
                'toy washing machine', 'play washer',
                'play appliance', 'toy appliance'
            ]
        }
        
        # Digital/non-physical products
        self.digital_indicators = [
            'download', 'digital code', 'gift card',
            'e-book', 'ebook', 'software license',
            'digital download', 'instant download'
        ]
    
    def is_valid_product(self, product: Dict, query: str = "") -> Tuple[bool, str]:
        """
        Universal validation - works for any product
        Filters out toy versions UNLESS user specifically searches for toys
        
        Args:
            product: Product dictionary
            query: Original search query (for context)
            
        Returns:
            (is_valid, reason)
        """
        title = product.get('title', '').lower()
        price = product.get('price', 0)
        
        # Check 1: Must have a title
        if not title or len(title) < 5:
            return False, "Invalid or missing title"
        
        # Check 2: Must have a valid price
        if price <= 0:
            return False, "No valid price found"
        
        # Check 3: Check for spam keywords
        spam_count = sum(1 for keyword in self.spam_keywords if keyword in title)
        if spam_count >= 2:  # Multiple spam indicators
            return False, "Contains multiple spam/scam keywords"
        
        # Check 4: TOY DETECTION - Filter ALL toy products unless searching for toys
        if not self._is_searching_for_toys(query):
            is_toy, toy_reason = self._is_toy_product(title, price, query)
            if is_toy:
                return False, toy_reason
        
        # Check 5: Warn about digital products (optional - still valid)
        digital_matches = sum(1 for keyword in self.digital_indicators if keyword in title)
        if digital_matches >= 1:
            return True, "Warning: Digital product detected"
        
        return True, "Valid product"
    
    def _is_searching_for_toys(self, query: str) -> bool:
        """Check if user explicitly wants toys"""
        query_lower = query.lower()
        toy_search_terms = ['toy', 'toys', 'kids', 'children', 'toddler', 'baby']
        return any(term in query_lower for term in toy_search_terms)
    
    def _is_toy_product(self, title: str, price: float, query: str) -> Tuple[bool, str]:
        """
        Comprehensive toy detection across ALL categories
        
        Returns:
            (is_toy, reason)
        """
        
        # Strategy 1: Check general toy indicators
        toy_indicator_matches = sum(1 for keyword in self.toy_indicators if keyword in title)
        if toy_indicator_matches >= 1:
            return True, "Product is a toy (contains toy indicators)"
        
        # Strategy 2: Check category-specific toy patterns
        # Detect what category the user is searching for
        query_lower = query.lower()
        
        # Check each category
        for category, patterns in self.toy_category_patterns.items():
            # If searching for this category
            if self._query_matches_category(query_lower, category):
                # Check if this is a toy version
                pattern_matches = sum(1 for pattern in patterns if pattern in title)
                if pattern_matches >= 1:
                    return True, f"Product is a toy {category}, not a real {category}"
        
        # Strategy 3: Price-based heuristics for specific categories
        # Cars under $1000 with electric/battery mentions
        if any(word in query_lower for word in ['car', 'vehicle', 'auto']):
            if 0 < price < 1000:
                electric_toy_indicators = ['electric', 'battery', '12v', '6v', 'rechargeable']
                if any(indicator in title for indicator in electric_toy_indicators):
                    # Check for toy brands
                    toy_brands = ['aosom', 'costway', 'best ride on', 'kid trax']
                    if any(brand in title for brand in toy_brands):
                        return True, "Product is a battery-powered toy car"
        
        # Laptops/tablets under $50 are likely toys
        if any(word in query_lower for word in ['laptop', 'tablet', 'computer']):
            if 0 < price < 50:
                if any(word in title for word in ['kids', 'learning', 'educational']):
                    return True, "Product is a toy laptop/tablet"
        
        # Furniture under $100 with plastic/play mentions
        if any(word in query_lower for word in ['furniture', 'table', 'chair', 'kitchen']):
            if 0 < price < 100:
                toy_furniture_indicators = ['plastic', 'play', 'kids', 'little tikes']
                if any(indicator in title for indicator in toy_furniture_indicators):
                    return True, "Product is toy furniture"
        
        return False, ""
    
    def _query_matches_category(self, query: str, category: str) -> bool:
        """Check if search query is for a specific category"""
        category_keywords = {
            'vehicle': ['car', 'cars', 'truck', 'vehicle', 'auto', 'suv', 'van'],
            'furniture': ['furniture', 'table', 'chair', 'desk', 'sofa', 'couch', 'bed', 'kitchen'],
            'electronics': ['laptop', 'computer', 'tablet', 'phone', 'iphone', 'ipad'],
            'appliances': ['blender', 'vacuum', 'microwave', 'washer', 'dryer', 'refrigerator']
        }
        
        keywords = category_keywords.get(category, [])
        return any(keyword in query for keyword in keywords)
    
    def extract_universal_specs(self, product: Dict) -> Dict:
        """
        Universal spec extraction - captures ANY numerical specs
        """
        title = product.get('title', '').lower()
        specs = {}
        
        # Storage/Memory (GB, TB)
        memory_matches = re.finditer(r'(\d+)\s*(gb|tb)(?:\s+(ram|ssd|storage|memory|emmc))?', title)
        for match in memory_matches:
            amount = int(match.group(1))
            unit = match.group(2)
            type_hint = match.group(3) if match.group(3) else 'storage'
            
            # Convert to GB
            if unit == 'tb':
                amount *= 1000
            
            # Store with hint
            if type_hint in ['ram', 'memory']:
                specs['ram_gb'] = amount
            else:
                specs['storage_gb'] = amount
        
        # Screen/Display size (inches)
        screen_match = re.search(r'(\d+\.?\d*)\s*(?:inch|"|\')', title)
        if screen_match:
            specs['screen_size_inches'] = float(screen_match.group(1))
        
        # Year (for cars, electronics, etc.)
        year_match = re.search(r'\b(19\d{2}|20[0-2]\d)\b', title)
        if year_match:
            specs['year'] = int(year_match.group(1))
        
        # Mileage (for vehicles)
        mileage_match = re.search(r'(\d+)k?\s*(?:miles?|km)', title)
        if mileage_match:
            miles_str = mileage_match.group(0)
            miles = int(mileage_match.group(1))
            if 'k' in miles_str.lower():
                miles *= 1000
            specs['mileage'] = miles
        
        # Weight (lbs, kg, oz)
        weight_match = re.search(r'(\d+\.?\d*)\s*(lbs?|kg|oz|pounds?)', title)
        if weight_match:
            specs['weight'] = float(weight_match.group(1))
            specs['weight_unit'] = weight_match.group(2)
        
        # Dimensions (X x Y x Z)
        dimension_match = re.search(r'(\d+\.?\d*)\s*x\s*(\d+\.?\d*)\s*x\s*(\d+\.?\d*)', title)
        if dimension_match:
            specs['dimensions'] = f"{dimension_match.group(1)}x{dimension_match.group(2)}x{dimension_match.group(3)}"
        
        # Voltage/Power (V, W)
        power_match = re.search(r'(\d+)\s*(v|w|volt|watt)(?!\s*battery)', title)  # Exclude "12v battery" for toys
        if power_match:
            specs['power'] = int(power_match.group(1))
            specs['power_unit'] = power_match.group(2)
        
        # Capacity (for batteries, containers, etc.)
        capacity_match = re.search(r'(\d+)\s*(mah|ah|l|ml|oz)', title)
        if capacity_match:
            specs['capacity'] = int(capacity_match.group(1))
            specs['capacity_unit'] = capacity_match.group(2)
        
        # Condition detection (use product's condition field if available)
        product_condition = product.get('condition', 'unknown')
        if product_condition != 'unknown':
            specs['condition'] = product_condition
        else:
            # Detect from title
            if any(word in title for word in ['refurbished', 'restored', 'renewed', 'refurb']):
                specs['condition'] = 'refurbished'
            elif 'used' in title or 'pre-owned' in title:
                specs['condition'] = 'used'
            elif 'new' in title or 'brand new' in title:
                specs['condition'] = 'new'
            else:
                specs['condition'] = 'unknown'
        
        # Extract brand (first capitalized word often)
        words = product.get('title', '').split()
        for word in words[:3]:  # Check first 3 words
            if word and len(word) > 2 and word[0].isupper():
                specs['brand'] = word
                break
        
        return specs
    
    def extract_key_features(self, product: Dict) -> List[str]:
        """
        Extract key features/keywords from title
        """
        title = product.get('title', '').lower()
        
        # Common feature words
        feature_keywords = [
            'wireless', 'bluetooth', 'wifi', 'smart', 'digital',
            'automatic', 'manual', 'portable', 'compact', 'lightweight',
            'heavy duty', 'professional', 'premium', 'deluxe',
            'certified', 'unlocked', 'sealed', 'brand new'
        ]
        
        found_features = []
        for keyword in feature_keywords:
            if keyword in title:
                found_features.append(keyword)
        
        return found_features