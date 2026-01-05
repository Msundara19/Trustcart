# TrustCart - AI-Powered E-Commerce Fraud Detection

Production-ready fraud detection system for online shopping across multiple platforms.

## Features

- 🔍 Multi-platform search (Google Shopping, eBay, Amazon)
- 🤖 AI-powered fraud analysis using Groq LLM
- 📊 Statistical anomaly detection
- 🎯 Universal product category support
- ⚡ 3-4 second response time

## Tech Stack

- **Backend**: FastAPI
- **AI**: Groq API (Llama 3.1-8b-instant)
- **Data**: SerpAPI (Google Shopping, eBay)
- **Architecture**: RESTful API, modular design

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Add your SERPAPI_KEY and GROQ_API_KEY

# Run the server
uvicorn main:app --reload
```

## API Endpoints

- `GET /api/search/{query}` - Search with fraud detection
- `GET /api/platforms` - Available platforms
- `GET /api/health` - Health check

## Project Structure
```
trustcart/
├── main.py                 # FastAPI entry point
├── app/
│   ├── api/               # API endpoints
│   ├── core/              # Core business logic
│   ├── models/            # ML models & fraud detection
│   ├── scraping/          # Multi-platform scrapers
│   └── utils/             # Utility functions
└── requirements.txt
```

## License

MIT
