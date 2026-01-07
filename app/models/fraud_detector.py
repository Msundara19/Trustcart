# app/models/fraud_detector.py

from typing import Dict, List
from .product_classifier import UniversalProductClassifier
from .llm_reasoner import LLMFraudExplainer
import statistics

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
    
    def _calculate_risk(self, product: Dict, all_products: List[Dict]) -> tuple:
        """Calculate risk score with seller reputation consideration"""
        risk_score = 0.0
        risk_factors = []
        
        price = product.get('price', 0)
        rating = product.get('rating', 0)
        reviews = product.get('reviews', 0)
        seller = product.get('seller', {})
        seller_name = seller.get('name', '').lower()
        source = product.get('source', '').lower()
        platform = product.get('platform', '').lower()
        
        # TRUSTED SELLERS - Major retailers get risk reduction
        trusted_sellers = ['target', 'walmart', 'best buy', 'amazon', 'ulta', 'kohl', 
                        'dyson', 'macy', 'laifen', 'ikea', 'west elm', 'crate & barrel']
        
        is_trusted = any(trusted in seller_name or trusted in source 
                        for trusted in trusted_sellers)
        
        # Price analysis - ADJUSTED for trusted sellers
        if len(all_products) > 3:
            prices = [p.get('price', 0) for p in all_products if p.get('price', 0) > 0]
            if prices:
                avg_price = statistics.mean(prices)
                
                if price < avg_price * 0.5:
                    if is_trusted and platform == 'google_shopping':
                        # Trusted retailer with low price = Clearance/sale, not scam
                        risk_score += 0.1  # Much lower risk
                        risk_factors.append(f"Low price (possible clearance sale)")
                    else:
                        # Unknown seller with low price = Suspicious
                        risk_score += 0.5
                        percent_below = int(((avg_price - price) / avg_price) * 100)
                        risk_factors.append(f"Extremely cheap: {percent_below}% below market average")
                        
                elif price < avg_price * 0.7:
                    if is_trusted:
                        risk_score += 0.05  # Very low risk for trusted sellers
                    else:
                        risk_score += 0.3
                        percent_below = int(((avg_price - price) / avg_price) * 100)
                        risk_factors.append(f"Price {percent_below}% below market average")
        
        # Rating/reviews - LESS impact for trusted retailers
        if rating == 0 and not is_trusted:
            risk_score += 0.15
            risk_factors.append("No rating available")
        elif rating == 0 and is_trusted:
            risk_score += 0.05  # Minimal impact for known stores
            
        if reviews == 0 and not is_trusted:
            risk_score += 0.15
            risk_factors.append("Very few reviews (0)")
        elif reviews == 0 and is_trusted:
            risk_score += 0.05  # Minimal impact for known stores
        
        return min(risk_score, 1.0), risk_factors
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to level - FIXED: Lower threshold for HIGH"""
        if risk_score >= 0.55:
            return "HIGH"
        elif risk_score >= 0.25:
            return "MEDIUM"
        else:
            return "LOW"
    
    def get_price_statistics(self, products: List[Dict]) -> Dict:
        """Calculate price statistics for context"""
        prices = [p.get('price', 0) for p in products if p.get('price', 0) > 0]
        
        if not prices:
            return {}
        
        return {
            "count": len(prices),
            "min": min(prices),
            "max": max(prices),
            "average": statistics.mean(prices),
            "median": statistics.median(prices),
            "std_dev": statistics.stdev(prices) if len(prices) > 1 else 0,
            "range": max(prices) - min(prices)
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