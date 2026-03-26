# TrustCart — AI-Powered E-Commerce Fraud Detection

[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen?style=flat-square)](https://web-production-e61ac.up.railway.app/)
[![Python](https://img.shields.io/badge/python-3.11+-blue?style=flat-square)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.128-009688?style=flat-square)](https://fastapi.tiangolo.com/)
[![XGBoost](https://img.shields.io/badge/XGBoost-91.6%25_F1-orange?style=flat-square)](https://xgboost.readthedocs.io/)
[![Groq LLM](https://img.shields.io/badge/Groq-LLaMA_3.1-8B-purple?style=flat-square)](https://groq.com/)
[![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)

> TrustCart is a real-time fraud detection system for e-commerce listings. It combines a trained XGBoost classifier, statistical anomaly scoring, Groq LLM reasoning, and semantic duplicate detection to surface risky listings from Google Shopping and eBay — before you buy.

**[Live Demo](https://web-production-e61ac.up.railway.app/)** · **[API Docs](https://web-production-e61ac.up.railway.app/docs)**
<img width="1066" height="789" alt="image" src="https://github.com/user-attachments/assets/6ed6fb54-38d5-4804-aad5-f903912a948d" />


---

## How It Works

A search query triggers a four-stage pipeline:

1. **Scraping** — Listings fetched from Google Shopping and eBay via SerpAPI
2. **Statistical Scoring** — Percentile-based price analysis, seller trust signals, and weighted rule scoring
3. **XGBoost Classification** — 17-feature gradient-boosted classifier assigns a fraud probability per listing
4. **Groq LLM Explanation** — Plain-English fraud reasoning generated for the top risky items, with structured red flags and a buy recommendation

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
│  /api/search  /api/evaluate     │
└──────────┬──────────────────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
SerpAPI       Fraud Detection Pipeline
Scraping      │
│             ├─ 1. Statistical Scoring
│ Google         Weighted 4-factor model
│ Shopping       Price: 50% | Seller: 25%
│ eBay           Attributes: 15% | History: 10%
│             │
│             ├─ 2. XGBoost Classifier (17 features)
│                log_price, rating, log_reviews,
│                seller_rating, quantity_sold,
│                seller_feedback_pct,
│                dynamic_trusted_seller,
│                price_percentile, platform,
│                condition (one-hot), title_length,
│                rating/review presence flags
│             │
│             ├─ 3. Groq LLM Explanation
│                llama-3.1-8b-instant
│                Structured JSON · In-memory cache
│                Top 5 risky items only
│             │
│             └─ 4. Duplicate Detection
│                TF-IDF cosine similarity (threshold 0.82)
│                Union-Find clustering
│                Cross-platform pair matching
│
└───────────────────────────────────────
    HTML5 / Tailwind CSS / Vanilla JS
         Glass-morphism UI
         Real-time animated pipeline stages
         Sort by risk, price · Filter by platform
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI 0.128 (Python 3.11+) |
| ML Model | XGBoost 1.7+, scikit-learn |
| LLM | Groq API — LLaMA 3.1-8B Instant |
| Duplicate Detection | TF-IDF cosine similarity (scikit-learn) |
| Data Collection | SerpAPI (Google Shopping + eBay) |
| Frontend | HTML5, Tailwind CSS, Vanilla JavaScript |
| Deployment | Railway (CI/CD from GitHub) |

---

## Fraud Detection Pipeline — Deep Dive

### Stage 1 — Statistical Risk Scoring

Each listing is scored using four independently weighted components:

| Component | Weight | Signals Used |
|-----------|:------:|-------------|
| Price Analysis | **50%** | Percentile rank within search results; outlier removal (>10× median); trusted seller discount |
| Seller Reputation | **25%** | Item rating, review count, seller rating, eBay feedback %, dynamic trust logic |
| Product Attributes | **15%** | Condition (new / used / refurbished / unknown), title length and quality |
| Historical Patterns | **10%** | Platform risk (eBay vs Google Shopping), category-specific baselines |

**Dynamic trusted seller logic:** eBay sellers with ≥1,000 ratings and ≥98% positive feedback are automatically recognized as trusted, regardless of whether they appear in the hardcoded retailer list.

Risk thresholds: `LOW` (< 0.25) · `MEDIUM` (0.25–0.55) · `HIGH` (≥ 0.55)

---

### Stage 2 — XGBoost Classifier

A gradient-boosted tree classifier trained on a **10,000-product synthetic dataset** and validated on **714 real scraped listings**.

**Training data distribution:**
- 35% fraud / 45% legitimate / 20% edge cases across 8 product categories
- Realistic price distributions, seller profiles, and condition labels per category

**Validation approach:**
- Real listings scraped via SerpAPI, labeled by Groq LLM consensus
- 5-fold stratified cross-validation on synthetic data: F1 ≈ 99.9%
- Generalization to real data: **F1 = 91.6%, Recall = 98.0%**

**17 input features (v2):**

| Feature | Description |
|---------|-------------|
| `log_price` | Log-transformed listing price |
| `rating` | Item star rating (0–5) |
| `log_reviews` | Log-transformed review count |
| `seller_rating` | Seller's own star rating |
| `is_trusted` | Hardcoded or dynamically trusted seller |
| `is_dynamic_trusted` | eBay sellers ≥1k ratings + ≥98% positive |
| `platform_ebay` | Binary: eBay vs Google Shopping |
| `condition_*` | One-hot: new / used / refurbished / unknown |
| `title_length` | Character count of listing title |
| `has_rating`, `has_reviews` | Presence flags |
| `price_percentile` | Rank within search result price distribution |
| `log_quantity_sold` | Log-transformed units sold (#2 most important feature) |
| `seller_feedback_pct` | eBay positive feedback % (0–1 normalized) |

---

### Stage 3 — Groq LLM Explanation

Natural language fraud analysis generated for the **top 3 HIGH-risk + top 2 MEDIUM-risk** products per search. Uses `llama-3.1-8b-instant` with:
- Structured JSON output (scam probability, red flags, reasoning, recommendation)
- Calibrated prompt with risk thresholds and market context
- In-memory caching keyed on title + price + risk level
- Trust score capped by recommendation: AVOID → max 20% safe, CAUTION → max 55% safe

---

### Stage 4 — Semantic Duplicate Detection

TF-IDF vectorization over preprocessed listing titles (unit normalization, color standardization) with cosine similarity threshold of **0.82**. Union-Find clustering groups near-identical listings, flagging cross-platform pairs so users can compare prices before buying.

---

## API Reference

### `GET /api/search/{query}`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `platform` | string | `all` | `google`, `ebay`, or `all` |
| `num_results` | int | `10` | 1–50 |
| `max_price` | int | — | Maximum price filter |

**Example:**
```bash
curl "https://web-production-e61ac.up.railway.app/api/search/iphone%2013?platform=ebay&num_results=10&max_price=500"
```

**Per-product response fields:**

| Field | Description |
|-------|-------------|
| `risk_score` | Rule-based score (0–1) |
| `risk_level` | `LOW` / `MEDIUM` / `HIGH` |
| `xgb_score` | XGBoost fraud probability (0–1) |
| `xgb_risk_level` | XGBoost risk classification |
| `price_tier` / `price_percentile` | Category-relative pricing context |
| `fraud_analysis` | LLM reasoning, red flags, recommendation |
| `duplicate_group` / `is_cross_platform` | Semantic duplicate flags |
| `similar_to` | Near-duplicate listings with similarity scores |

**Top-level response also includes:** `risk_summary`, `price_statistics`, `duplicate_summary`

---

### `GET /api/evaluate`

Side-by-side model comparison on 714 real listings. Returns precision, recall, F1, AUC, confusion matrix, per-category breakdown, threshold sensitivity, and XGBoost feature importances.

```bash
curl "https://web-production-e61ac.up.railway.app/api/evaluate"
```

### Other Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | System status, model availability |
| `GET /api/platforms` | Supported platforms and capabilities |
| `GET /api/test-llm` | Validate Groq LLM connectivity |
| `GET /api/logs/stats?days=7` | Prediction log stats (fraud rate, volume) |

---

## Local Development

### Prerequisites

- Python 3.11+
- `libomp` (macOS only, required by XGBoost): `brew install libomp`
- [SerpAPI key](https://serpapi.com) — for live scraping
- [Groq API key](https://console.groq.com) — for LLM explanations

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/Msundara19/Trustcart.git
cd Trustcart

# 2. Install OpenMP (macOS only)
brew install libomp

# 3. Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure environment variables
cp .env.example .env
# Edit .env and add:
#   SERPAPI_KEY=your_serpapi_key
#   GROQ_API_KEY=your_groq_key

# 6. Start the server
uvicorn main:app --reload
# → http://localhost:8000
```

### Rebuild the Model (optional)

```bash
# Generate 10k synthetic labeled products
python data/synthetic_generator.py

# Collect ~700 real listings via SerpAPI (~50 searches)
python data/collect_real_data.py

# Label real listings with Groq LLM
python data/llm_labeler.py

# Train XGBoost and save model
python data/train_model.py

# Verify performance
curl "http://localhost:8000/api/evaluate"
```

---

## Quick Test Cases

```bash
# Standard search — both platforms
curl "http://localhost:8000/api/search/iphone%2013?num_results=20"

# High-risk category
curl "http://localhost:8000/api/search/used%20cars%20under%205000?platform=ebay"

# Trusted sellers — expect LOW risk
curl "http://localhost:8000/api/search/dyson%20hair%20dryer?platform=google"

# Low-value items — verify outlier handling
curl "http://localhost:8000/api/search/marvel%20comic%20books"

# Model benchmark
curl "http://localhost:8000/api/evaluate"
```

---

## Roadmap

### Completed
- [x] Multi-platform scraping — Google Shopping + eBay via SerpAPI
- [x] Statistical fraud scoring — weighted 4-factor model (50/25/15/10%)
- [x] Percentile-based price analysis with outlier removal
- [x] Dynamic trusted seller recognition (eBay ≥1k ratings + ≥98% positive)
- [x] Groq LLM explanations — structured JSON, calibrated risk thresholds
- [x] XGBoost classifier — 17 features, 91.6% F1 / 98.0% recall on real data
- [x] Semantic duplicate detection — TF-IDF cosine similarity, cross-platform pairing
- [x] Prediction logging — rotating JSONL files for dataset growth pipeline
- [x] `/api/evaluate` — live side-by-side model benchmark endpoint
- [x] Production deployment on Railway (CI/CD from GitHub)
- [x] Blue gradient glass-morphism UI with real-time animated pipeline stages

### Planned
- [ ] Browser extension (Chrome / Firefox)
- [ ] Historical price tracking
- [ ] Amazon + AliExpress integration
- [ ] Image-based counterfeit detection

---

## Security & Privacy

- **No user data collected** — stateless API, no session tracking or personal data storage
- API keys stored in environment variables, never committed to version control
- Input validation on all endpoints via Pydantic
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
| [SerpAPI](https://serpapi.com) | Reliable Google Shopping + eBay scraping |
| [XGBoost](https://xgboost.readthedocs.io/) | Gradient boosting classifier |
| [FastAPI](https://fastapi.tiangolo.com/) | Async Python web framework |
| [Railway](https://railway.app/) | Zero-config cloud deployment |
