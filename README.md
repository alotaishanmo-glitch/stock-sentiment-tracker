# 📈 Stock Sentiment Tracker

A real-time NLP pipeline that aggregates retail investor sentiment for any 
stock ticker from Reddit, StockTwits, and financial news headlines — then 
scores it using FinBERT, a sentiment model trained specifically on financial text.

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![FinBERT](https://img.shields.io/badge/NLP-FinBERT-green)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## 🔍 What It Does

- Scrapes **Reddit** (r/wallstreetbets, r/stocks, r/investing, r/options)
- Pulls **StockTwits** messages with self-reported Bull/Bear labels
- Fetches **Yahoo Finance** news headlines via RSS
- Runs all text through **FinBERT** for financial-domain sentiment scoring
- Weights scores by post engagement (upvotes, likes, retweets)
- Outputs a **0–100 sentiment score** with trend analysis and hot topics

---

## 📊 Example Output

```
================================================
Sentiment Report: $TSLA  |  May 2 2026
================================================
SCORE:      72.4 / 100   🟢 Bullish
CONFIDENCE: High (low variance across sources)
TREND:      📈 Improving (+8.2 over 7 days)
------------------------------------------------
SOURCES
Reddit:      68.1  (143 posts across 4 subreddits)
StockTwits:  75.3  (30 messages | 🐂 18 Bull / 🐻 7 Bear)
News:        74.0  (20 headlines)
------------------------------------------------
BULL/BEAR RATIO:  71% Bull  |  29% Bear
MENTION VOLUME:   193 total posts (7 days)
------------------------------------------------
DAILY TREND
Apr 26: 64.1  ▁
Apr 27: 66.3  ▂
Apr 28: 71.2  ▄
Apr 29: 74.1  ▅
May 02: 78.2  ███
------------------------------------------------
HOT TOPICS: earnings, guidance, deliveries, musk,
            autopilot, china, shorts, calls
================================================
```

---

## 🛠 Tech Stack

| Layer | Tool |
|---|---|
| Reddit scraping | Public JSON API (no auth) |
| StockTwits | Public REST API |
| News | Yahoo Finance RSS + `feedparser` |
| Sentiment model | `FinBERT` via HuggingFace Transformers |
| Data processing | `requests`, `nltk`, `collections` |
| Config | `python-dotenv` |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- ~2GB disk space for FinBERT model (downloaded automatically on first run)

### Installation

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/stock-sentiment-tracker.git
cd stock-sentiment-tracker

# Install dependencies
pip install -r requirements.txt

# Copy the env example (no API keys needed!)
cp .env.example .env
```

### Usage

```bash
# Basic usage
python main.py AAPL

# Custom date range and result limit
python main.py TSLA --days 14 --limit 100
```

---

## 📁 Project Structure

```
stock-sentiment-tracker/
├── main.py                  # Entry point
├── config.py                # Environment config
├── scrapers/
│   ├── reddit_scraper.py    # Reddit public JSON scraper
│   ├── x_scraper.py         # StockTwits scraper
│   └── news_scraper.py      # Yahoo Finance RSS
├── analysis/
│   └── sentiment.py         # FinBERT scoring + weighting
├── utils/
│   └── rate_limiter.py      # Rate limit handling
├── output/                  # JSON results saved here
├── requirements.txt
└── .env.example
```

---

## ⚙️ How the Scoring Works

1. Each post/message is scored by FinBERT → returns `positive`, `negative`, `neutral` probabilities
2. Compound score = `positive - negative` (range: -1 to +1)
3. Each score is **weighted by engagement** using `log(engagement + 1)` to reduce the impact of outliers
4. Weighted average is scaled to **0–100**
5. Daily buckets are calculated to show trend direction over time

| Score | Signal |
|---|---|
| 0 – 35 | 🔴 Bearish |
| 36 – 50 | 🟠 Slightly Bearish |
| 51 – 65 | 🟡 Slightly Bullish |
| 66 – 100 | 🟢 Bullish |

---

## 🗺 Roadmap

- [ ] Streamlit web dashboard
- [ ] Email/Slack alerts when sentiment shifts significantly
- [ ] Multi-ticker comparison
- [ ] Historical score database

---

## 📄 License

MIT — free to use and build on.
