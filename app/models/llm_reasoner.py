# app/models/llm_explainer.py

from groq import Groq
import os
from typing import Dict, List, Optional
import json
import hashlib
from functools import lru_cache

class LLMFraudExplainer:
    """
    Uses Groq (ultra-fast LPU) for fraud explanations
    
    Free tier: 14,400 requests/day
    Models: llama-3.1-8b-instant (use 70b for complex cases)
    
    Optimization strategies:
    - Structured JSON outputs
    - Caching for identical products
    - Smart model selection (8B vs 70B)
    - Batch processing support
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
        self.fast_model = "llama-3.1-8b-instant"  # 300+ tokens/sec
        self.smart_model = "llama-3.1-70b-versatile"  # Use for complex cases
        
        # Cache for identical products (avoid redundant API calls)
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
            
            # Select model based on complexity
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
                temperature=0.3,  # Lower = more consistent
                max_tokens=200,
                response_format={"type": "json_object"}  # Force JSON output
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
        
        Strategy:
        - Only analyze HIGH/MEDIUM risk products
        - Use 8B model for most cases
        - Escalate to 70B only if 8B shows uncertainty
        - Process in batches to respect rate limits
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
            
            # First pass: Use fast 8B model
            analysis = self.explain_risk(
                product=product,
                risk_level=risk_level,
                risk_score=risk_score,
                risk_factors=risk_factors,
                price_stats=price_stats,
                use_smart_model=False
            )
            
            if analysis:
                # Add to product
                product['fraud_analysis'] = analysis
                product['risk_explanation'] = analysis.get('reasoning', '')
                
                # If 8B is uncertain (scam_probability near 0.5), escalate to 70B
                scam_prob = analysis.get('scam_probability', 0)
                if 0.4 <= scam_prob <= 0.6 and risk_level == 'HIGH':
                    # Re-analyze with smarter model
                    smart_analysis = self.explain_risk(
                        product=product,
                        risk_level=risk_level,
                        risk_score=risk_score,
                        risk_factors=risk_factors,
                        price_stats=price_stats,
                        use_smart_model=True
                    )
                    if smart_analysis:
                        product['fraud_analysis'] = smart_analysis
                        product['risk_explanation'] = smart_analysis.get('reasoning', '')
        
        return products
    
    def _get_system_prompt(self) -> str:
        """Optimized system prompt focusing on specific scam indicators"""
        return """You are an expert fraud detection system analyzing online shopping listings.

Focus on these scam indicators:
- Unrealistic pricing (too cheap)
- Fake/missing reviews
- Poor grammar or exaggerated claims ("AMAZING DEAL!!!")
- Suspicious seller patterns (no rating, new account)
- Stock photos vs real product photos
- Vague product descriptions
- Suspicious payment methods mentions

Return analysis as JSON with these exact fields:
{
  "scam_probability": <float 0.0-1.0>,
  "red_flags": [<list of specific red flags found>],
  "reasoning": "<2-3 sentence explanation>",
  "recommendation": "<AVOID/CAUTION/SAFE>"
}

Be specific, concise, and actionable."""
    
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
        
        prompt = f"""Analyze this product listing for fraud:

PRODUCT: {title}
PRICE: ${price}
PLATFORM: {platform}
RATING: {rating}/5 ({reviews} reviews)
RISK LEVEL: {risk_level}
{price_context}

DETECTED RISK FACTORS:
{chr(10).join(f"- {factor}" for factor in risk_factors)}

Analyze and return JSON with scam_probability, red_flags, reasoning, and recommendation."""
        
        return prompt
    
    def _get_cache_key(self, product: Dict, risk_level: str) -> str:
        """Generate cache key for identical products"""
        # Use title + price + platform as unique identifier
        unique_str = f"{product.get('title', '')}{product.get('price', 0)}{risk_level}"
        return hashlib.md5(unique_str.encode()).hexdigest()
    
    def clear_cache(self):
        """Clear cached analyses"""
        self._cache.clear()