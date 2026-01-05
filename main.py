# main.py

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.scraping.google_shopping import GoogleShoppingScraper
from app.scraping.ebay import EbayScraper
from app.models.fraud_detector import UniversalFraudDetector
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional

load_dotenv()

app = FastAPI(
    title="TrustCart - Universal Shopping Fraud Detector",
    description="AI-powered fraud detection for ANY product category across multiple platforms",
    version="2.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize scrapers
google_scraper = GoogleShoppingScraper(api_key=os.getenv("SERPAPI_KEY"))
ebay_scraper = EbayScraper(api_key=os.getenv("SERPAPI_KEY"))
fraud_detector = UniversalFraudDetector()

def _generate_category_warning(query: str, valid_products: List[Dict], invalid_products: List[Dict]) -> Optional[str]:
    """Generate warnings about filtered products and search limitations"""
    warnings = []
    
    # Check if many products were filtered as toys
    if invalid_products:
        toy_products = [p for p in invalid_products if 'toy' in p.get('invalid_reason', '').lower()]
        if len(toy_products) > 0:
            warnings.append(
                f"ℹ️ Filtered out {len(toy_products)} toy product(s). "
                f"To search for toys specifically, include 'toy' or 'kids' in your query."
            )
    
    # Category-specific warnings
    query_lower = query.lower()
    
    # Cars warning
    if any(word in query_lower for word in ['car', 'cars', 'vehicle', 'auto']):
        if invalid_products and len([p for p in invalid_products if 'toy' in p.get('invalid_reason', '').lower()]) > 0:
            warnings.append(
                "⚠️ Many toy cars were filtered. For real vehicles, try adding '?platform=ebay&condition=used' to search eBay."
            )
    
    return " ".join(warnings) if warnings else None

def _summarize_filtered_reasons(invalid_products: List[Dict]) -> Dict:
    """Summarize why products were filtered"""
    reasons = {}
    for product in invalid_products:
        reason = product.get('invalid_reason', 'Unknown')
        reasons[reason] = reasons.get(reason, 0) + 1
    return reasons

@app.get("/api/search/{query}")
async def search_products(
    query: str,
    num_results: int = Query(default=10, ge=1, le=50),
    platform: str = Query(default="google", enum=["google", "ebay", "all"]),
    max_price: Optional[int] = None,
    condition: Optional[str] = Query(default=None, enum=["new", "used", "refurbished"]),
    analyze_fraud: bool = True,
    filter_invalid: bool = True
):
    """
    Universal product search with AI-powered fraud detection
    
    Parameters:
    - query: Search query
    - num_results: Number of results per platform (1-50)
    - platform: "google" (default), "ebay", or "all"
    - max_price: Maximum price filter (eBay only)
    - condition: "new", "used", or "refurbished" (eBay only)
    - analyze_fraud: Enable fraud detection
    - filter_invalid: Remove invalid products
    """
    
    try:
        all_products = []
        platforms_searched = []
        
        # Search Google Shopping
        if platform in ["google", "all"]:
            try:
                google_products = google_scraper.search(query=query, num_results=num_results)
                all_products.extend(google_products)
                platforms_searched.append("google_shopping")
            except Exception as e:
                print(f"Google Shopping error: {e}")
        
        # Search eBay
        if platform in ["ebay", "all"]:
            try:
                ebay_kwargs = {}
                if max_price:
                    ebay_kwargs['max_price'] = max_price
                if condition:
                    ebay_kwargs['condition'] = condition
                
                ebay_products = ebay_scraper.search(
                    query=query,
                    num_results=num_results,
                    **ebay_kwargs
                )
                all_products.extend(ebay_products)
                platforms_searched.append("ebay")
            except Exception as e:
                print(f"eBay error: {e}")
        
        if not all_products:
            return {
                "query": query,
                "platforms_searched": platforms_searched,
                "total_results": 0,
                "message": "No products found"
            }
        
        # Analyze for fraud (includes LLM explanations)
        if analyze_fraud:
            all_products = fraud_detector.analyze_products(all_products, query)
        
        # Filter invalid products
        if filter_invalid:
            valid_products = [p for p in all_products if p.get('is_valid_product', True)]
            invalid_products = [p for p in all_products if not p.get('is_valid_product', True)]
        else:
            valid_products = all_products
            invalid_products = []
        
        # Generate category warning
        category_warning = _generate_category_warning(query, valid_products, invalid_products)
        
        # Calculate statistics
        if valid_products:
            price_stats = fraud_detector.get_price_statistics(valid_products)
            
            high_risk = [p for p in valid_products if p.get('risk_level') == 'HIGH']
            medium_risk = [p for p in valid_products if p.get('risk_level') == 'MEDIUM']
            low_risk = [p for p in valid_products if p.get('risk_level') == 'LOW']
            
            recommendations = fraud_detector.get_smart_recommendations(valid_products)
        else:
            price_stats = {}
            high_risk, medium_risk, low_risk = [], [], []
            recommendations = {}
        
        # Return results
        return {
            "query": query,
            "platforms_searched": platforms_searched,
            "category_warning": category_warning,
            "total_results": len(all_products),
            "valid_products": len(valid_products),
            "filtered_out": len(invalid_products),
            "filtered_reasons": _summarize_filtered_reasons(invalid_products) if invalid_products else {},
            "price_statistics": price_stats,
            "risk_summary": {
                "high_risk_count": len(high_risk),
                "medium_risk_count": len(medium_risk),
                "low_risk_count": len(low_risk)
            },
            "products": valid_products,
            "invalid_products": invalid_products if not filter_invalid else [],
            "recommendations": recommendations
        }
    
    except Exception as e:
        import traceback
        print(f"Error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/platforms")
async def get_supported_platforms():
    """Get list of supported platforms and their features"""
    return {
        "platforms": {
            "google_shopping": {
                "name": "Google Shopping",
                "description": "Retail products from major stores",
                "best_for": ["New products", "Electronics", "General retail"],
                "supports_used": False,
                "supports_condition_filter": False
            },
            "ebay": {
                "name": "eBay",
                "description": "New and used products, auctions and Buy It Now",
                "best_for": ["Used items", "Cars", "Electronics", "Collectibles"],
                "supports_used": True,
                "supports_condition_filter": True,
                "conditions": ["new", "used", "refurbished"]
            }
        }
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0",
        "google_scraper": "online" if google_scraper else "offline",
        "ebay_scraper": "online" if ebay_scraper else "offline",
        "fraud_detector": "online" if fraud_detector else "offline",
        "llm_enabled": fraud_detector.llm_explainer.enabled if hasattr(fraud_detector, 'llm_explainer') else False
    }

@app.get("/api/test-llm")
async def test_llm():
    """Test if Groq LLM is working"""
    
    # Check if LLM explainer exists
    if not hasattr(fraud_detector, 'llm_explainer'):
        return {
            "status": "error",
            "error": "llm_explainer not found in fraud_detector",
            "hint": "Check if fraud_detector.py initializes self.llm_explainer"
        }
    
    # Check if LLM is enabled
    if not fraud_detector.llm_explainer.enabled:
        return {
            "status": "disabled",
            "error": "LLM is disabled",
            "groq_key_set": bool(os.getenv("GROQ_API_KEY")),
            "hint": "Add GROQ_API_KEY to your .env file"
        }
    
    # Try a simple test
    try:
        test_product = {
            "title": "iPhone 13 Pro - AMAZING DEAL!!!",
            "price": 50,
            "platform": "ebay",
            "rating": 0,
            "reviews": 0,
            "seller": {"name": "test-seller"}
        }
        
        analysis = fraud_detector.llm_explainer.explain_risk(
            product=test_product,
            risk_level="HIGH",
            risk_score=0.9,
            risk_factors=["Extremely cheap: 90% below median", "No reviews"],
            price_stats={"average": 500}
        )
        
        if analysis:
            return {
                "status": "success",
                "llm_enabled": True,
                "test_analysis": analysis,
                "message": "✅ Groq LLM is working perfectly!"
            }
        else:
            return {
                "status": "error",
                "error": "LLM returned None",
                "hint": "Check Groq API key or rate limits"
            }
    
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "hint": "Check the error details above"
        }

# Mount static files and serve frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root():
    """Serve the frontend HTML"""
    return FileResponse('static/index.html')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)