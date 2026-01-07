# app/models/llm_reasoner.py

from groq import Groq
import os
from typing import Dict, List, Optional
import json
import hashlib

class LLMFraudExplainer:
    """
    Uses Groq (ultra-fast LPU) for fraud explanations
    
    Free tier: 14,400 requests/day
    Models: llama-3.1-8b-instant (use 70b for complex cases)
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        
        if not self.api_key:
            print("Warning: Groq API key not found. LLM explanations disabled.")
            self.enabled = False
            self.client = None
        else:
            self.enabled = True
            self.client = Groq(api_key=self.api_key)
        
        # Model selection
        self.fast_model = "llama-3.1-8b-instant"
        self.smart_model = "llama-3.1-70b-versatile"
        
        # Cache for identical products
        self._cache = {}
    
    def explain_risk(
        self, 
        product: Dict, 
        risk_level: str, 
        risk_score: float, 
        risk_factors: List[str],
        price_stats: Dict = None,
        use_smart_model: bool = False
    ) -> Optional[Dict]:
        """
        Generate structured fraud analysis with reasoning
        
        Returns:
            {
                "scam_probability": float (0.0-1.0),
                "red_flags": List[str],
                "reasoning": str,
                "recommendation": str
            }
        """
        if not self.enabled:
            return None
        
        try:
            # Check cache first
            cache_key = self._get_cache_key(product, risk_level)
            if cache_key in self._cache:
                return self._cache[cache_key]
            
            # Build optimized prompt
            prompt = self._build_structured_prompt(
                product=product,
                risk_level=risk_level,
                risk_score=risk_score,
                risk_factors=risk_factors,
                price_stats=price_stats
            )
            
            # Select model
            model = self.smart_model if use_smart_model else self.fast_model
            
            # Call Groq with structured output
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            
            # Cache result
            self._cache[cache_key] = result
            
            return result
                
        except Exception as e:
            print(f"Groq LLM error: {e}")
            return None
    
    def batch_explain(
        self, 
        products: List[Dict], 
        price_stats: Dict = None,
        max_concurrent: int = 5
    ) -> List[Dict]:
        """
        Efficiently process multiple products
        """
        if not self.enabled:
            return products
        
        risky_products = [
            p for p in products 
            if p.get('risk_level') in ['HIGH', 'MEDIUM']
        ]
        
        for product in risky_products:
            risk_level = product.get('risk_level')
            risk_score = product.get('risk_score', 0)
            risk_factors = product.get('risk_factors', [])
            
            analysis = self.explain_risk(
                product=product,
                risk_level=risk_level,
                risk_score=risk_score,
                risk_factors=risk_factors,
                price_stats=price_stats,
                use_smart_model=False
            )
            
            if analysis:
                product['fraud_analysis'] = analysis
                product['risk_explanation'] = analysis.get('reasoning', '')
        
        return products
    
    def _get_system_prompt(self) -> str:
        """Improved system prompt with clear risk thresholds"""
        return """You are an expert fraud detection system for online shopping.

RISK CALIBRATION GUIDELINES:
- HIGH RISK (0.7-1.0): Multiple major red flags present
  * Price 50%+ below market AND no reviews
  * Obvious scam language ("AMAZING DEAL!!!")
  * New seller + unrealistic pricing
  * Parts/broken items listed as working
  
- MEDIUM RISK (0.4-0.69): Some concerning factors
  * Price 30-50% below market OR few reviews
  * Minor seller concerns
  * Slightly suspicious but could be legitimate
  
- LOW RISK (0.0-0.39): Minimal concerns
  * Price reasonable (within 30% of market)
  * Good seller rating OR established platform
  * Normal product description

IMPORTANT: Be strict about HIGH risk. Only assign 0.7+ when multiple serious red flags exist.

Return JSON with exact fields:
{
  "scam_probability": <float 0.0-1.0>,
  "red_flags": [<specific red flags found>],
  "reasoning": "<2-3 sentences explaining the probability>",
  "recommendation": "AVOID" | "PROCEED WITH CAUTION" | "SAFE TO BUY"
}"""
    
    def _build_structured_prompt(
        self,
        product: Dict,
        risk_level: str,
        risk_score: float,
        risk_factors: List[str],
        price_stats: Dict = None
    ) -> str:
        """Build focused prompt with key fraud signals"""
        
        title = product.get('title', 'Unknown')
        price = product.get('price', 0)
        platform = product.get('platform', 'unknown')
        rating = product.get('rating', 0)
        reviews = product.get('reviews', 0)
        condition = product.get('condition', 'unknown')
        
        # Calculate price deviation
        price_context = ""
        if price_stats and price_stats.get('average'):
            avg = price_stats['average']
            if price > 0 and avg > 0:
                deviation = int(((avg - price) / avg) * 100)
                if deviation > 0:
                    price_context = f"Price is {deviation}% below market average (${avg:.2f})"
                else:
                    price_context = f"Price is {abs(deviation)}% above market average (${avg:.2f})"
        
        prompt = f"""Analyze this listing for fraud:

PRODUCT: {title}
PRICE: ${price}
CONDITION: {condition}
PLATFORM: {platform}
RATING: {rating}/5 ({reviews} reviews)
PRELIMINARY RISK: {risk_level} (score: {risk_score:.2f})
{price_context}

DETECTED RISK FACTORS:
{chr(10).join(f"- {factor}" for factor in risk_factors)}

Based on these factors, assign a calibrated scam_probability (0.0-1.0), list specific red_flags, provide reasoning, and give a recommendation."""
        
        return prompt
    
    def _get_cache_key(self, product: Dict, risk_level: str) -> str:
        """Generate cache key for identical products"""
        unique_str = f"{product.get('title', '')}{product.get('price', 0)}{risk_level}"
        return hashlib.md5(unique_str.encode()).hexdigest()
    
    def clear_cache(self):
        """Clear cached analyses"""
        self._cache.clear()