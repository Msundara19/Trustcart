# app/models/fraud_detector.py

from typing import Dict, List
from .product_classifier import UniversalProductClassifier
from .llm_reasoner import LLMFraudExplainer  # Import from llm_reasoner.py
import statistics

class UniversalFraudDetector:
    """Universal fraud detection with Groq-powered AI explanations"""
    
    def __init__(self):
        self.classifier = UniversalProductClassifier()
        self.llm_explainer = LLMFraudExplainer()  # Initialize LLM explainer
        print(f"🔍 Fraud Detector initialized (LLM enabled: {self.llm_explainer.enabled})")
    
    def analyze_products(self, products: List[Dict], query: str = "") -> List[Dict]:
        """
        Analyze products for fraud with AI-powered explanations
        
        Steps:
        1. Validate products (filter toys, spam, etc.)
        2. Calculate risk scores
        3. Generate AI explanations for risky products
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
        
        # Count risk levels
        high = sum(1 for p in valid_products if p.get('risk_level') == 'HIGH')
        medium = sum(1 for p in valid_products if p.get('risk_level') == 'MEDIUM')
        low = sum(1 for p in valid_products if p.get('risk_level') == 'LOW')
        print(f"📊 Risk: HIGH={high}, MEDIUM={medium}, LOW={low}")
        
        # Step 3: Add AI explanations (Groq LLM)
        if valid_products and self.llm_explainer.enabled:
            print(f"🤖 Generating AI explanations...")
            price_stats = self.get_price_statistics(valid_products)
            valid_products = self.llm_explainer.batch_explain(valid_products, price_stats)
            
            # Count how many got explanations
            with_explanations = sum(1 for p in valid_products if 'fraud_analysis' in p)
            print(f"✅ {with_explanations}/{len(valid_products)} products analyzed by AI")
        elif not self.llm_explainer.enabled:
            print("⚠️ LLM disabled - skipping AI explanations")
        
        return products
    
    def _calculate_risk(self, product: Dict, all_products: List[Dict]) -> tuple:
        """Calculate risk score and identify risk factors"""
        risk_score = 0.0
        risk_factors = []
        
        price = product.get('price', 0)
        rating = product.get('rating', 0)
        reviews = product.get('reviews', 0)
        seller = product.get('seller', {})
        seller_rating = seller.get('rating', 0)
        
        # Price analysis (compare to other products)
        if len(all_products) > 3:
            prices = [p.get('price', 0) for p in all_products if p.get('price', 0) > 0]
            if prices:
                median_price = statistics.median(prices)
                
                if price < median_price * 0.3:
                    risk_score += 0.4
                    percent_below = int(((median_price - price) / median_price) * 100)
                    risk_factors.append(f"Extremely cheap: {percent_below}% below median")
                elif price < median_price * 0.5:
                    risk_score += 0.25
                    percent_below = int(((median_price - price) / median_price) * 100)
                    risk_factors.append(f"Suspiciously low price: {percent_below}% below median")
        
        # Rating analysis
        if rating == 0:
            risk_score += 0.15
            risk_factors.append("No rating available")
        elif rating < 3.0:
            risk_score += 0.25
            risk_factors.append(f"Low rating: {rating}/5")
        
        # Reviews analysis
        if reviews == 0:
            risk_score += 0.15
            risk_factors.append("Very few reviews (0)")
        elif reviews < 5:
            risk_score += 0.1
            risk_factors.append(f"Few reviews ({reviews})")
        
        # Seller analysis
        if seller_rating > 0 and seller_rating < 3.0:
            risk_score += 0.2
            risk_factors.append(f"Low seller rating: {seller_rating}/5")
        
        return min(risk_score, 1.0), risk_factors
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to level"""
        if risk_score >= 0.6:
            return "HIGH"
        elif risk_score >= 0.3:
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