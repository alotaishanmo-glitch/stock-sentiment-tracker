# ⚡ SentimentIQ

A real-time stock sentiment dashboard that aggregates retail investor chatter from **Reddit**, **StockTwits**, and **financial news**, then scores it with **FinBERT** — the sentiment model trained specifically on financial text.

Type a ticker, get an instant 0–100 sentiment score with bull/bear breakdown, daily trend, top posts, and hot topics — all in a clean React-styled dashboard served through Streamlit.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FinBERT](https://img.shields.io/badge/NLP-FinBERT-green)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-red)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## 🌐 Live Demo

**[sentimentiq.streamlit.app](https://sentimentiq.streamlit.app)** ← deployed on Streamlit Community Cloud

---

## 🔍 What It Does

- Scrapes **Reddit** (r/wallstreetbets, r/stocks, r/investing, r/options)
- Pulls **StockTwits** messages with self-reported Bull/Bear labels
- Fetches **Yahoo Finance** news headlines via RSS
- Runs all text through **FinBERT** for financial-domain sentiment scoring
- Weights scores by post engagement (upvotes, likes, replies)
- Renders the result in a custom React dashboard with:
  - Sentiment gauge (0–100, color-coded by zone)
  - Bull/Bear ratio breakdown per source
  - 7-day trend line with smoothed Catmull-Rom curve
  - Hot topics extracted from the most-discussed terms
  - Clickable links to the top Reddit post and news headline

---

## 🚀 Getting Started

### Run locally

```bash
git clone https://github.com/alotaishanmo-glitch/stock-sentiment-tracker.git
cd stock-sentiment-tracker
pip install -r requirements.txt
streamlit run app.py
```

First run downloads the FinBERT model (~500 MB). Subsequent runs are cached.

### Run the CLI version (no UI)

```bash
python main.py TSLA --days 7 --limit 50
```

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────┐
│  Streamlit (app.py)                          │
│   ├─ Native search form (URL query params)   │
│   ├─ Server-side analysis (cached 5 min)     │
│   └─ Injects JSON result into HTML template  │
├──────────────────────────────────────────────┤
│  Custom React dashboard (frontend/)          │
│   ├─ Sentiment gauge, trend chart, sources   │
│   └─ Reads injected window.__INITIAL_DATA__  │
├──────────────────────────────────────────────┤
│  Analysis pipeline (api_server.py + scrapers)│
│   ├─ Parallel scraping (Reddit + ST + News)  │
│   ├─ FinBERT scoring (engagement-weighted)   │
│   └─ Aggregates score, trend, hot topics     │
└──────────────────────────────────────────────┘
```

This architecture works **identically** locally and on Streamlit Cloud — no browser-to-localhost fetches, no CORS issues, no port conflicts.

---

## 🛠 Tech Stack

| Layer | Tool |
|---|---|
| Web UI shell | Streamlit |
| Dashboard | React 18 + Babel standalone (no build step) |
| Reddit scraping | Public JSON API (no auth) |
| StockTwits | Public REST API |
| News | Yahoo Finance RSS + `feedparser` |
| Sentiment model | `FinBERT` via HuggingFace `transformers` |
| Price data | `yfinance` |
| Concurrency | `concurrent.futures.ThreadPoolExecutor` |

---

## ⚙️ How the Scoring Works

1. Each post/message is scored by FinBERT → returns `positive`, `negative`, `neutral` probabilities
2. Compound score = `positive − negative` (range −1 to +1)
3. Each score is **weighted by engagement** using `log(engagement + 1)` to dampen outliers
4. Weighted average is scaled to **0–100** and rounded
5. Daily buckets compute the trend direction over the past N days

| Score | Signal |
|---|---|
| 0 – 35 | 🔴 Bearish |
| 36 – 50 | 🟠 Slightly Bearish |
| 51 – 65 | 🟡 Slightly Bullish |
| 66 – 100 | 🟢 Bullish |

Confidence is derived from the variance across the three sources — agreement = high confidence, disagreement = low.

---

## 📁 Project Structure

```
stock-sentiment-tracker/
├── app.py                       # Streamlit entry point
├── api_server.py                # Analysis pipeline + (optional) Flask routes
├── main.py                      # CLI entry point
├── config.py                    # Reddit user agent, subreddit list
├── frontend/
│   └── SentimentIQ.html         # Self-contained React dashboard
├── scrapers/
│   ├── reddit_scraper.py
│   ├── stocktwits_scraper.py
│   └── news_scraper.py
├── analysis/
│   └── sentiment.py             # FinBERT scoring, trend, hot topics
└── requirements.txt
```

---

## 🚢 Deploying Your Own Copy

1. Fork this repo on GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → **Create app** → **Deploy public app from GitHub**
3. Select your fork, branch `main`, main file `app.py`
4. Under **Advanced settings**, set Python version to **3.11**
5. Click **Deploy** — first boot takes ~5 min for the FinBERT model download

---

## 🆕 Recent Updates

### v0.4.3 — Dashboard polish & bug fixes
- **Signal Quality card** now shows live data — Volume is derived from total mention count, Source Diversity reflects how many of the 3 sources returned data, and Model Certainty is a real numeric score (0–100) computed from variance across source scores
- **AI Summary** rewritten with 8 score-zone-based variations that incorporate the ticker, sentiment score, bull/bear ratio, mention volume, top source, and trend direction — no more static copy
- **Trend chart** fixed — null-score days are now interpolated, empty data shows a graceful fallback message, and x-axis labels adapt automatically for 7D / 30D / 90D / 1Y ranges
- **Range buttons (30D / 90D / 1Y)** now show a loading overlay immediately on click so the Streamlit rerun no longer feels like a page crash
- **Mention count** bumped: news scraper limit raised from 20 → 50 and StockTwits from 30 → 50, giving richer signal for the bull/bear ratio
- **iOS Safari scroll** fixed — iframe height increased to 3600px with `scrolling=True`; users can now scroll past the News Source Breakdown
- **Sentiment score** is now properly centered inside the gauge arc on all screen sizes

## 🗺 Roadmap

- [x] Streamlit web dashboard
- [x] Public deployment
- [x] Server-side analysis (no client-side fetches)
- [x] Live Signal Quality metrics (volume, source diversity, model certainty)
- [x] Dynamic AI summary with zone-based copy
- [x] Multi-range trend chart (7D / 30D / 90D / 1Y)
- [x] iOS Safari scroll fix
- [ ] Multi-ticker comparison view
- [ ] Email/Slack alerts when sentiment shifts > X points
- [ ] Historical score database (SQLite)
- [ ] Replace web scrapers with proper APIs where rate limits become a problem

---

## 📄 License

MIT — free to use, fork, and build on. Attribution appreciated but not required.
