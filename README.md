# TrustCart — AI-Powered E-Commerce Fraud Detection

[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen)](https://web-production-e61ac.up.railway.app/)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.128-green)](https://fastapi.tiangolo.com/)
[![XGBoost](https://img.shields.io/badge/xgboost-1.7+-orange)](https://xgboost.readthedocs.io/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

> Real-time fraud detection system that analyzes e-commerce product listings across Google Shopping and eBay using a hybrid ML pipeline: statistical anomaly detection, XGBoost classification, and Groq LLM reasoning.

**[Live Demo](https://web-production-e61ac.up.railway.app/)** | **[API Docs](https://web-production-e61ac.up.railway.app/docs)**

<img width="575" height="436" alt="TrustCart UI" src="https://github.com/user-attachments/assets/58ecea66-6cf0-4ec0-bda2-bd94fd808cea" />

---

## Model Performance

Benchmarked on **714 real scraped listings** (Google Shopping + eBay) labeled via Groq LLM, and **10,000 synthetic listings** across 8 product categories.

### XGBoost Classifier (primary model)

| Metric | Value |
|--------|-------|
| F1 Score | **94.5%** |
| Recall | **97.5%** |
| Precision | **91.6%** |
| Accuracy | **92.9%** |
| AUC (ROC) | **92.2%** |
| CV F1 (5-fold) | **99.9% ± 0.03%** |

### vs Rule-Based Statistical Baseline

| Metric | XGBoost | Rule-Based | Delta |
|--------|---------|------------|-------|
| F1 | **94.5%** | 84.5% | +10.0% |
| Recall | **97.5%** | 77.3% | +20.2% |
| Precision | 91.6% | **93.2%** | -1.7% |
| Accuracy | **92.9%** | 82.4% | +10.5% |

### Per-Category F1 (XGBoost)

| Category | F1 | Category | F1 |
|----------|----|----------|----|
| Headphones | 99.1% | Books | 89.2% |
| PS5 / Gaming Console | 96.6% | iPhone | 90.2% |
| Gaming Laptop | 95.2% | Furniture | 78.1% |
| Hair Dryer | 92.6% | Used Cars | 100.0% |

### Top Predictive Features (XGBoost Importance)

| Feature | Importance |
|---------|------------|
| Seller Rating | 56.0% |
| Product Rating | 16.3% |
| Review Count (log) | 7.8% |
| Platform (eBay) | 6.5% |
| Condition | 5.3% |
| Price Percentile | 4.2% |

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Frontend                         │
│              HTML5 / Tailwind CSS / JS              │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│                  FastAPI Backend                    │
│         /api/search  /api/evaluate  /api/health     │
└──────┬───────────────┬──────────────────────────────┘
       │               │
       ▼               ▼
┌────────────┐  ┌──────────────────────────────────────┐
│  SerpAPI   │  │         Fraud Detection Pipeline      │
│  Scraping  │  │                                      │
│            │  │  1. ProductClassifier                │
│ • Google   │  │     Toy filtering, spec extraction   │
│   Shopping │  │                                      │
│ • eBay     │  │  2. Statistical Scoring (rule-based) │
└────────────┘  │     Weighted factors: 50/25/15/10%   │
                │     Percentile-based price analysis  │
                │     Outlier removal (>10x median)    │
                │                                      │
                │  3. XGBoost Classifier               │
                │     14 features, trained on 10k      │
                │     synthetic + validated on 714     │
                │     real LLM-labeled listings        │
                │                                      │
                │  4. Groq LLM Explainer               │
                │     llama-3.1-8b-instant             │
                │     Top 5 risky items only           │
                └──────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI 0.128 (Python 3.11+) |
| ML Model | XGBoost 1.7+, scikit-learn 1.3+ |
| LLM | Groq API — Llama 3.1-8B Instant |
| Statistical Analysis | NumPy, percentile-based scoring |
| Data Collection | SerpAPI (Google Shopping + eBay) |
| Frontend | HTML5, Tailwind CSS, Vanilla JavaScript |
| Deployment | Railway (CI/CD from GitHub) |

---

## Fraud Detection Pipeline

### 1. Statistical Risk Scoring (Rule-Based Baseline)

Each product is scored using four independently weighted components:

| Component | Weight | Signals |
|-----------|--------|---------|
| Price Analysis | 50% | Percentile rank within category, outlier detection (>10x median removed), trusted seller adjustment |
| Seller Reputation | 25% | Product rating, review count, seller rating |
| Product Attributes | 15% | Condition (new/used/refurbished/unknown), title length/quality |
| Historical Patterns | 10% | Platform risk (eBay vs Google Shopping), category-specific rules |

Risk levels: `LOW` (< 0.25) · `MEDIUM` (0.25–0.55) · `HIGH` (≥ 0.55)

### 2. XGBoost Classification

A gradient-boosted classifier trained on a 10,000-product synthetic dataset and validated on 714 real scraped listings labeled via Groq LLM consensus.

**Training approach:**
- Synthetic data generator produces realistic price distributions across 8 categories with deterministic fraud labels (35% fraud / 45% legitimate / 20% edge cases)
- Real validation set: 714 Google Shopping + eBay listings scraped via SerpAPI, labeled by Groq LLM, validated against rule-based scores (41.2% label agreement used as a quality signal)
- 5-fold stratified cross-validation on synthetic set: F1 = 99.9% ± 0.03%
- Generalization to real data: F1 = 94.5%, Recall = 97.5%

**14 input features:** log price, rating, log review count, seller rating, trusted seller flag, platform, condition (one-hot), title length, rating/review presence flags, price percentile.

### 3. Groq LLM Explanation

Natural language fraud reasoning generated for the top 3 HIGH-risk + top 2 MEDIUM-risk products per search. Uses `llama-3.1-8b-instant` with structured JSON output and in-memory caching.

---

## API Reference

### Search Products
```
GET /api/search/{query}
```
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `platform` | string | `all` | `google`, `ebay`, or `all` |
| `num_results` | int | 10 | 1–50 |
| `max_price` | int | — | Maximum price filter |
| `condition` | string | — | `new`, `used`, `refurbished` |

**Example:**
```bash
curl "https://web-production-e61ac.up.railway.app/api/search/iphone%2013?platform=ebay&num_results=10&max_price=500"
```

**Response includes per-product:**
- `risk_score` — rule-based score (0–1)
- `risk_level` — LOW / MEDIUM / HIGH
- `xgb_score` — XGBoost fraud probability (0–1)
- `xgb_risk_level` — XGBoost risk classification
- `price_tier` / `price_percentile` — category-relative pricing
- `fraud_analysis` — LLM reasoning, red flags, recommendation

### Evaluate Model Performance
```
GET /api/evaluate?threshold=0.25&sample_size=1000
```
Returns side-by-side rule-based vs XGBoost metrics: precision, recall, F1, AUC, confusion matrix, per-category breakdown, threshold sensitivity analysis, and XGBoost feature importances.

### Other Endpoints
```
GET /api/health        # System status + model availability
GET /api/platforms     # Supported platforms and capabilities
GET /api/test-llm      # Validate Groq LLM connectivity
```

---

## Local Development

### Prerequisites
- Python 3.11+
- Homebrew (macOS) — for `libomp` required by XGBoost
- SerpAPI key — [serpapi.com](https://serpapi.com)
- Groq API key — [console.groq.com](https://console.groq.com)

### Setup

```bash
# 1. Clone
git clone https://github.com/Msundara19/Trustcart.git
cd Trustcart

# 2. Install OpenMP (macOS only, required for XGBoost)
brew install libomp

# 3. Create virtual environment
python -m venv venv
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure environment
cp .env.example .env
# Add your keys to .env:
#   SERPAPI_KEY=your_key
#   GROQ_API_KEY=your_key

# 6. Start server
uvicorn main:app --reload
# → http://localhost:8000
```

### Build the Evaluation Dataset (one-time)

```bash
# Generate 10k synthetic labeled products (no API cost)
python data/synthetic_generator.py

# Collect ~1,000 real listings (~50 SerpAPI searches)
python data/collect_real_data.py

# Label real listings via Groq LLM
python data/llm_labeler.py

# Train XGBoost model
python data/train_model.py

# View benchmark results
curl "http://localhost:8000/api/evaluate"
```

---

## Quick Test Cases

```bash
# Search and analyze (both platforms, default)
curl "http://localhost:8000/api/search/iphone%2013?num_results=10"

# High-risk category — expect many HIGH risk flags
curl "http://localhost:8000/api/search/used%20cars%20under%205000?platform=ebay"

# Trusted seller — expect LOW risk from major retailers
curl "http://localhost:8000/api/search/hair%20dryer?platform=google"

# Outlier handling — $10-20 books should NOT be 99% below average
curl "http://localhost:8000/api/search/marvel%20comic%20books"

# Model benchmark
curl "http://localhost:8000/api/evaluate"

# Health check
curl "http://localhost:8000/api/health"
```

---

## Roadmap

### Completed
- [x] Multi-platform search (Google Shopping + eBay via SerpAPI)
- [x] Statistical fraud scoring — weighted 4-factor model (50/25/15/10%)
- [x] Percentile-based price analysis with outlier removal
- [x] Trusted seller recognition (15 major retailers)
- [x] Groq LLM fraud explanations (Llama 3.1-8B, structured JSON)
- [x] XGBoost classifier — 94.5% F1, 97.5% recall on real data
- [x] Evaluation benchmark pipeline — synthetic + real labeled datasets
- [x] `/api/evaluate` — live model comparison endpoint
- [x] Production deployment (Railway, CI/CD from GitHub)

### In Progress
- [ ] Semantic duplicate detection using sentence embeddings
- [ ] Prediction logging + dataset growth pipeline

### Planned
- [ ] Browser extension (Chrome/Firefox)
- [ ] Historical price tracking
- [ ] Amazon + AliExpress integration
- [ ] Image analysis for counterfeit detection
- [ ] User authentication and saved searches

---

## Security & Privacy

- No user data collected — stateless API, no tracking or storage
- API keys stored in environment variables, never committed
- Input validation on all endpoints
- HTTPS enforced on production (Railway)

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Author

**Meenakshi Sridharan**
- GitHub: [@Msundara19](https://github.com/Msundara19)
- LinkedIn: [Meenakshi Sridharan](https://linkedin.com/in/meenakshi-sridharan)
- Email: msridharansundaram@hawk.illinoistech.edu
- Portfolio: [meenakshi-sridharan.vercel.app](https://portfolio-git-main-msundaras-projects.vercel.app/)

---

## Acknowledgments

- **Groq** — Ultra-fast LLM inference (14,400 req/day free tier)
- **SerpAPI** — Reliable e-commerce data (Google Shopping + eBay)
- **XGBoost** — Gradient boosting framework
- **FastAPI** — Modern async Python web framework
- **Railway** — Zero-config deployment platform
