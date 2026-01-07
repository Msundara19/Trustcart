# app/models/fraud_detector.py

from typing import Dict, List, Tuple, Optional
from .product_classifier import UniversalProductClassifier
from .llm_reasoner import LLMFraudExplainer
import statistics
import numpy as np

class UniversalFraudDetector:
    """Universal fraud detection with Groq-powered AI explanations"""
    
    def __init__(self):
        self.classifier = UniversalProductClassifier()
        self.llm_explainer = LLMFraudExplainer()
        print(f"🔍 Fraud Detector initialized (LLM enabled: {self.llm_explainer.enabled})")
    
    def analyze_products(self, products: List[Dict], query: str = "") -> List[Dict]:
        """
        Analyze products for fraud with AI-powered explanations
        OPTIMIZED: Only analyze top 5 risky products to keep response time under 5 seconds
        """
        
        print(f"\n🔍 Analyzing {len(products)} products...")
        
        # Step 1: Validate products
        for product in products:
            is_valid, reason = self.classifier.is_valid_product(product, query)
            product['is_valid_product'] = is_valid
            product['invalid_reason'] = reason if not is_valid else None
            product['specs'] = self.classifier.extract_universal_specs(product)
            product['features'] = self.classifier.extract_key_features(product)
        
        # Step 2: Calculate risk for valid products
        valid_products = [p for p in products if p.get('is_valid_product', True)]
        print(f"✅ {len(valid_products)} valid products")
        
        for product in valid_products:
            risk_score, risk_factors = self._calculate_risk(product, valid_products)
            product['risk_score'] = risk_score
            product['risk_factors'] = risk_factors
            product['risk_level'] = self._get_risk_level(risk_score)
        
        # Separate by risk level
        high_risk = [p for p in valid_products if p.get('risk_level') == 'HIGH']
        medium_risk = [p for p in valid_products if p.get('risk_level') == 'MEDIUM']
        low_risk = [p for p in valid_products if p.get('risk_level') == 'LOW']
        
        print(f"📊 Risk: HIGH={len(high_risk)}, MEDIUM={len(medium_risk)}, LOW={len(low_risk)}")
        
        # Step 3: LLM analysis - ONLY top 5 risky products (3 HIGH + 2 MEDIUM)
        products_to_analyze = high_risk[:3] + medium_risk[:2]
        
        if products_to_analyze and self.llm_explainer.enabled:
            print(f"🤖 Generating AI explanations for {len(products_to_analyze)} products...")
            price_stats = self.get_price_statistics(valid_products)
            
            for product in products_to_analyze:
                analysis = self.llm_explainer.explain_risk(
                    product=product,
                    risk_level=product.get('risk_level'),
                    risk_score=product.get('risk_score', 0),
                    risk_factors=product.get('risk_factors', []),
                    price_stats=price_stats
                )
                
                if analysis:
                    product['fraud_analysis'] = analysis
                    product['risk_explanation'] = analysis.get('reasoning', '')
            
            print(f"✅ {len(products_to_analyze)} products analyzed by AI")
        elif not self.llm_explainer.enabled:
            print("⚠️ LLM disabled - skipping AI explanations")
        
        # Step 4: Add default fraud analysis for products WITHOUT LLM analysis
        for product in valid_products:
            if 'fraud_analysis' not in product:
                product['fraud_analysis'] = self._get_default_analysis(product)
        
        return products
    
    def _calculate_risk(self, product: Dict, all_products: List[Dict]) -> Tuple[float, List[str]]:
        """
        Calculate risk score with percentile-based price tier classification
        ROBUST: Uses median and removes outliers for accurate assessment
        """
        risk_score = 0.0
        risk_factors = []
        
        price = product.get('price', 0)
        rating = product.get('rating', 0)
        reviews = product.get('reviews', 0)
        
        # Get seller trust info
        seller = product.get('seller', {})
        seller_name = seller.get('name', '').lower()
        source = product.get('source', '').lower()
        platform = product.get('platform', '').lower()
        
        # Trusted sellers list (major retailers)
        trusted_sellers = [
            'target', 'walmart', 'best buy', 'amazon', 'ulta', 'kohl',
            'barnes & noble', 'books a million', 'abebooks', 'dyson',
            'ikea', 'macy', 'west elm', 'crate & barrel', 'wayfair'
        ]
        
        is_trusted = any(trusted in seller_name or trusted in source 
                        for trusted in trusted_sellers)
        
        # Price analysis with percentiles (ROBUST TO OUTLIERS)
        if len(all_products) >= 5:  # Need minimum 5 products for meaningful analysis
            price_tier_info = self._classify_price_tier(price, all_products)
            
            # Add tier info to product for debugging
            product['price_tier'] = price_tier_info['tier']
            product['price_percentile'] = price_tier_info['percentile']
            
            # Risk assessment based on tier
            if price_tier_info['is_outlier_high']:
                # Extremely high-priced item (>10x median)
                risk_score += 0.15
                risk_factors.append("High-value or rare item - verify authenticity carefully")
                
            elif price_tier_info['tier'] == 'extremely_cheap':
                # Bottom 10% - SUSPICIOUS unless trusted seller
                if is_trusted and platform == 'google_shopping':
                    risk_score += 0.1
                    risk_factors.append("Significantly below typical price (possible clearance)")
                else:
                    risk_score += 0.5
                    percent_below = int(((price_tier_info['median'] - price) / price_tier_info['median']) * 100)
                    risk_factors.append(f"Extremely cheap: {percent_below}% below typical price")
                    
            elif price_tier_info['tier'] == 'budget':
                # 10-25th percentile
                if is_trusted:
                    risk_score += 0.0  # No risk for trusted sellers
                else:
                    risk_score += 0.2
                    risk_factors.append("Lower-priced option - verify condition and seller")
                    
            elif price_tier_info['tier'] == 'mid':
                # 25-75th percentile - Normal pricing
                risk_score += 0.0
                
            elif price_tier_info['tier'] in ['premium', 'luxury']:
                # 75%+ - High value items
                if not is_trusted and reviews == 0:
                    risk_score += 0.2
                    risk_factors.append("High-value item from seller with no reviews")
        
        # Rating analysis
        if rating == 0:
            if is_trusted:
                risk_score += 0.05  # Minimal impact for known stores
            else:
                risk_score += 0.15
                risk_factors.append("No rating available")
        elif rating < 3.0:
            risk_score += 0.25
            risk_factors.append(f"Low rating: {rating}/5")
        
        # Reviews analysis
        if reviews == 0:
            if is_trusted:
                risk_score += 0.05  # Minimal impact for known stores
            else:
                risk_score += 0.15
                risk_factors.append("Very few reviews (0)")
        elif reviews < 5:
            risk_score += 0.1
            risk_factors.append(f"Few reviews ({reviews})")
        
        # Seller rating analysis
        seller_rating = seller.get('rating', 0)
        if seller_rating > 0 and seller_rating < 3.0:
            risk_score += 0.2
            risk_factors.append(f"Low seller rating: {seller_rating}/5")
        
        return min(risk_score, 1.0), risk_factors
    
    def _classify_price_tier(self, price: float, all_products: List[Dict]) -> Dict:
        """
        Classify price into tier using percentiles (ROBUST to outliers)
        
        Returns:
        {
            'tier': 'extremely_cheap/budget/mid/premium/luxury',
            'percentile': 45.5,
            'is_outlier_high': False,
            'median': 100.0
        }
        """
        # Extract all prices
        prices = [p.get('price', 0) for p in all_products if p.get('price', 0) > 0]
        
        if len(prices) < 3:
            return {
                'tier': 'unknown',
                'percentile': 50,
                'is_outlier_high': False,
                'median': 0
            }
        
        # Step 1: Calculate initial median
        median_price = float(np.median(prices))
        
        # Step 2: Check if product is extreme outlier (>10x median)
        if price > median_price * 10:
            return {
                'tier': 'outlier_high',
                'percentile': 100,
                'is_outlier_high': True,
                'median': median_price
            }
        
        # Step 3: Filter extreme outliers from comparison (>10x median)
        filtered_prices = [p for p in prices if p <= median_price * 10]
        
        if len(filtered_prices) < 3:
            filtered_prices = prices  # Fallback
        
        # Step 4: Recalculate with clean data
        clean_median = float(np.median(filtered_prices))
        
        # Step 5: Calculate percentile of this product
        sorted_prices = sorted(filtered_prices)
        rank = sum(1 for p in sorted_prices if p <= price)
        percentile = (rank / len(sorted_prices)) * 100
        
        # Step 6: Classify into tier based on percentile
        if percentile <= 10:
            tier = 'extremely_cheap'
        elif percentile <= 25:
            tier = 'budget'
        elif percentile <= 75:
            tier = 'mid'
        elif percentile <= 90:
            tier = 'premium'
        else:
            tier = 'luxury'
        
        return {
            'tier': tier,
            'percentile': round(percentile, 1),
            'is_outlier_high': False,
            'median': clean_median
        }
    
    def _get_default_analysis(self, product: Dict) -> Dict:
        """Generate default fraud analysis for products not analyzed by LLM"""
        risk_level = product.get('risk_level', 'UNKNOWN')
        risk_score = product.get('risk_score', 0)
        risk_factors = product.get('risk_factors', [])
        
        if risk_level == 'LOW':
            return {
                "scam_probability": risk_score,
                "red_flags": [],
                "reasoning": "This listing appears legitimate with reasonable pricing and good seller reputation.",
                "recommendation": "SAFE TO BUY"
            }
        elif risk_level == 'MEDIUM':
            return {
                "scam_probability": risk_score,
                "red_flags": risk_factors,
                "reasoning": "This listing has some minor concerns. Verify seller details before purchasing.",
                "recommendation": "PROCEED WITH CAUTION"
            }
        else:  # HIGH
            return {
                "scam_probability": risk_score,
                "red_flags": risk_factors,
                "reasoning": "This listing shows multiple warning signs. Exercise extreme caution or avoid.",
                "recommendation": "AVOID"
            }
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to level"""
        if risk_score >= 0.55:
            return "HIGH"
        elif risk_score >= 0.25:
            return "MEDIUM"
        else:
            return "LOW"
    
    def get_price_statistics(self, products: List[Dict]) -> Dict:
        """Calculate price statistics for context (with outlier handling)"""
        prices = [p.get('price', 0) for p in products if p.get('price', 0) > 0]
        
        if not prices:
            return {}
        
        # Remove extreme outliers for statistics
        median = np.median(prices)
        filtered_prices = [p for p in prices if p <= median * 10]
        
        if len(filtered_prices) < 2:
            filtered_prices = prices
        
        return {
            "count": len(prices),
            "min": min(filtered_prices),
            "max": max(filtered_prices),
            "average": float(np.mean(filtered_prices)),
            "median": float(np.median(filtered_prices)),
            "std_dev": float(np.std(filtered_prices)) if len(filtered_prices) > 1 else 0,
            "range": max(filtered_prices) - min(filtered_prices)
        }
    
    def get_smart_recommendations(self, products: List[Dict]) -> Dict:
        """Generate smart buying recommendations"""
        if not products:
            return {}
        
        low_risk = [p for p in products if p.get('risk_level') == 'LOW']
        medium_risk = [p for p in products if p.get('risk_level') == 'MEDIUM']
        
        recommendations = {}
        
        if low_risk:
            best = min(low_risk, key=lambda x: x.get('price', float('inf')))
            recommendations['best_deal'] = {
                "title": best.get('title'),
                "price": best.get('price'),
                "link": best.get('link'),
                "reason": "Lowest price among low-risk products"
            }
        
        if medium_risk:
            recommendations['proceed_with_caution'] = len(medium_risk)
        
        return recommendations