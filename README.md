# TrustCart — AI-Powered E-Commerce Fraud Detection

[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen?style=flat-square)](https://web-production-e61ac.up.railway.app/)
[![Python](https://img.shields.io/badge/python-3.11+-blue?style=flat-square)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.128-009688?style=flat-square)](https://fastapi.tiangolo.com/)
[![XGBoost](https://img.shields.io/badge/XGBoost-91.6%25_F1-orange?style=flat-square)](https://xgboost.readthedocs.io/)
[![Groq LLM](https://img.shields.io/badge/Groq-LLaMA_3.1_8B-purple?style=flat-square)](https://groq.com/)
[![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)

> TrustCart is a real-time fraud detection system for e-commerce listings. It combines a trained XGBoost classifier, statistical anomaly scoring, Groq LLM reasoning, and semantic duplicate detection to surface risky listings from Google Shopping and eBay — before you buy.


**[Live Demo](https://web-production-e61ac.up.railway.app/)** 

<img width="1066" height="789" alt="image" src="https://github.com/user-attachments/assets/6ed6fb54-38d5-4804-aad5-f903912a948d" />

---

## How It Works

A search query triggers a four-stage pipeline:

1. **Scraping** — Listings fetched live from Google Shopping and eBay via SerpAPI
2. **Statistical Scoring** — Percentile-based price analysis, seller trust signals, and a weighted 4-factor rule model
3. **XGBoost Classification** — 17-feature gradient-boosted classifier assigns a fraud probability to each listing
4. **Groq LLM Explanation** — Plain-English fraud reasoning, red flags, and a buy recommendation for the top risky items

Results are deduplicated using TF-IDF cosine similarity to surface cross-platform price comparisons.

---

## Model Performance

Benchmarked on **714 real scraped listings** (Google Shopping + eBay), labeled via Groq LLM and validated against rule-based scores.

### XGBoost vs. Rule-Based Baseline

| Metric | XGBoost | Rule-Based | Delta |
|--------|:-------:|:----------:|:-----:|
| F1 Score | **91.6%** | 84.5% | +7.1% |
| Recall | **98.0%** | 77.3% | +20.7% |
| Precision | 86.0% | **93.2%** | −7.2% |
| Accuracy | **88.8%** | 82.4% | +6.4% |
| AUC (ROC) | 92.4% | **93.6%** | −1.2% |

> High recall (98%) is the priority — catching fraudulent listings matters more than the occasional false positive.

### Per-Category F1 (XGBoost, real data)

| Category | F1 | Category | F1 |
|----------|----|----------|----|
| Used Cars | **100%** | Gaming Laptop | **95.2%** |
| Luxury Watch | **100%** | Headphones | **96.6%** |
| Luxury Handbag | **100%** | PS5 / Console | **96.6%** |
| iPhone | 91.6% | Books | 85.6% |
| Hair Dryer | 80.0% | Furniture | 69.6% |

### Top Predictive Features (XGBoost Importance)

| Rank | Feature | Importance |
|------|---------|:----------:|
| 1 | Seller Rating | 60.0% |
| 2 | Quantity Sold (log) | 14.8% |
| 3 | Product Rating | 10.9% |
| 4 | Price Percentile | 3.2% |
| 5 | Review Count (log) | 2.8% |
| 6 | Log Price | 2.4% |
| 7 | Condition (New) | 1.9% |
| 8 | Seller Feedback % | 1.8% |
| 9 | Platform (eBay) | 1.1% |

---

## Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────┐
│     FastAPI Backend             │
└──────────┬──────────────────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
SerpAPI       Fraud Detection Pipeline
Scraping      │
│             ├─ 1. Statistical Scoring
│ Google         Price: 50% | Seller: 25%
│ Shopping       Attributes: 15% | History: 10%
│ eBay        │
│             ├─ 2. XGBoost Classifier (17 features)
│                seller_rating, quantity_sold,
│                price_percentile, rating, reviews,
│                seller_feedback_pct, platform,
│                condition, dynamic_trust flags
│             │
│             ├─ 3. Groq LLM Explanation
│                llama-3.1-8b-instant
│                Structured JSON · Cached
│             │
│             └─ 4. Duplicate Detection
│                TF-IDF cosine similarity (0.82)
│                Cross-platform pair matching
│
└──────────────────────────
    Tailwind CSS / Vanilla JS
    Glass-morphism UI
    Real-time animated stages
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI 0.128 (Python 3.11+) |
| ML Model | XGBoost 1.7+, scikit-learn |
| LLM | Groq API — LLaMA 3.1-8B Instant |
| Duplicate Detection | TF-IDF cosine similarity |
| Data Collection | SerpAPI (Google Shopping + eBay) |
| Frontend | HTML5, Tailwind CSS, Vanilla JavaScript |
| Deployment | Railway (CI/CD from GitHub) |

---

## Fraud Detection — Deep Dive

### Stage 1 — Statistical Risk Scoring

| Component | Weight | Signals |
|-----------|:------:|---------|
| Price Analysis | **50%** | Percentile rank, outlier removal (>10× median), trusted seller discount |
| Seller Reputation | **25%** | Item rating, review count, seller rating, eBay feedback %, dynamic trust |
| Product Attributes | **15%** | Condition, title length and quality |
| Historical Patterns | **10%** | Platform risk, category-specific baselines |

**Dynamic trusted seller logic:** eBay sellers with ≥1,000 ratings and ≥98% positive feedback are automatically trusted — no hardcoding needed.

Risk thresholds: `LOW` (< 0.25) · `MEDIUM` (0.25–0.55) · `HIGH` (≥ 0.55)

### Stage 2 — XGBoost Classifier

Trained on **10,000 synthetic listings** (35% fraud / 45% legitimate / 20% edge cases) and validated on **714 real scraped listings** labeled via Groq LLM.

17 input features across price, seller trust, platform, condition, and sales volume. `quantity_sold` emerged as the #2 most important feature (14.8%) — high-volume listings are a strong legitimacy signal.

### Stage 3 — Groq LLM Explanation

Generates structured fraud analysis for the top 5 risky items per search: scam probability, specific red flags, plain-English reasoning, and a buy recommendation. Trust score is capped by the LLM output — an AVOID verdict limits the safety score to 20%, preventing contradictory results.

### Stage 4 — Semantic Duplicate Detection

TF-IDF vectorization with cosine similarity threshold of **0.82** and Union-Find clustering. Flags when the same item appears across multiple sellers or platforms so users can compare before buying.

---

## Local Development

### Prerequisites

- Python 3.11+
- `libomp` (macOS only): `brew install libomp`
- [SerpAPI key](https://serpapi.com) · [Groq API key](https://console.groq.com)

### Setup

```bash
git clone https://github.com/Msundara19/Trustcart.git
cd Trustcart

brew install libomp          # macOS only

python -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env         # Add SERPAPI_KEY and GROQ_API_KEY

uvicorn main:app --reload    # → http://localhost:8000
```

---

## Roadmap

- [x] Multi-platform scraping — Google Shopping + eBay
- [x] Statistical fraud scoring — weighted 4-factor model
- [x] XGBoost classifier — 17 features, 91.6% F1 / 98.0% recall
- [x] Groq LLM explanations with calibrated risk thresholds
- [x] Semantic duplicate detection — cross-platform pairing
- [x] Prediction logging for continuous dataset growth
- [x] Production deployment on Railway (CI/CD from GitHub)
- [ ] Browser extension (Chrome / Firefox)
- [ ] Historical price tracking
- [ ] Amazon + AliExpress integration
- [ ] Image-based counterfeit detection

---

## Security & Privacy

- No user data collected — stateless API, no tracking or storage
- API keys stored in environment variables, never committed
- HTTPS enforced in production (Railway)

---

## Author

**Meenakshi Sridharan**

[![GitHub](https://img.shields.io/badge/GitHub-@Msundara19-181717?style=flat-square&logo=github)](https://github.com/Msundara19)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Meenakshi_Sridharan-0A66C2?style=flat-square&logo=linkedin)](https://linkedin.com/in/meenakshi-sridharan)
[![Portfolio](https://img.shields.io/badge/Portfolio-Visit-4F46E5?style=flat-square)](https://portfolio-git-main-msundaras-projects.vercel.app/)

📧 msridharansundaram@hawk.illinoistech.edu

---

## Acknowledgments

| Tool | Role |
|------|------|
| [Groq](https://groq.com) | Ultra-fast LLM inference (LPU hardware) |
| [SerpAPI](https://serpapi.com) | Google Shopping + eBay scraping |
| [XGBoost](https://xgboost.readthedocs.io/) | Gradient boosting classifier |
| [FastAPI](https://fastapi.tiangolo.com/) | Async Python web framework |
| [Railway](https://railway.app/) | Zero-config cloud deployment |
