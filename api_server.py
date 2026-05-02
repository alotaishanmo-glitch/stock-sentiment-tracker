"""
Flask API server that the SentimentIQ dashboard calls.
Started as a background thread by app.py.
"""

import concurrent.futures
import logging
import pathlib
from datetime import datetime

from flask import Flask, jsonify, request

logger = logging.getLogger(__name__)


def create_app(port: int = 0) -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def index():
        html_path = pathlib.Path(__file__).parent / "frontend" / "SentimentIQ.html"
        html = html_path.read_text(encoding="utf-8").replace("__API_PORT__", str(port))
        return html, 200, {"Content-Type": "text/html; charset=utf-8"}

    @app.after_request
    def _cors(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    @app.route("/api/analyse")
    def analyse():
        ticker = request.args.get("ticker", "TSLA").strip().upper()
        if not ticker.isalpha() or len(ticker) > 10:
            return jsonify({"error": "Invalid ticker symbol"}), 400
        days = min(int(request.args.get("days", 7)), 30)
        limit = min(int(request.args.get("limit", 50)), 100)
        try:
            result = _run_analysis(ticker, days, limit)
            return jsonify(result)
        except Exception as exc:
            logger.exception("Analysis failed for %s", ticker)
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok"})

    return app


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def _run_analysis(ticker: str, days: int = 7, limit: int = 50) -> dict:
    from scrapers import reddit_scraper, stocktwits_scraper, news_scraper
    from analysis import sentiment as sent

    errors: dict = {}
    reddit_posts, st_messages, news_articles = [], [], []

    # Fetch all three sources in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            "reddit": pool.submit(reddit_scraper.fetch_all, ticker, limit, days),
            "stocktwits": pool.submit(stocktwits_scraper.fetch_messages, ticker, 30),
            "news": pool.submit(news_scraper.fetch_headlines, ticker, 20),
        }
        for source, fut in futures.items():
            try:
                data = fut.result(timeout=45)
                if source == "reddit":
                    reddit_posts = data
                elif source == "stocktwits":
                    st_messages = data
                else:
                    news_articles = data
            except Exception as exc:
                errors[source] = str(exc)
                logger.warning("Scraper %s failed: %s", source, exc)

    # Score each source with FinBERT (sequential — model is not thread-safe for parallel loads)
    scored_reddit = sent.score_reddit_posts(reddit_posts) if reddit_posts else []
    scored_st = sent.score_stocktwits(st_messages) if st_messages else []
    scored_news = sent.score_news(news_articles) if news_articles else []
    all_scored = scored_reddit + scored_st + scored_news

    if not all_scored:
        return {
            "ticker": ticker,
            "error": "No data collected from any source.",
            "errors": errors,
        }

    # Per-source aggregated scores
    source_scores = {
        "reddit": sent.compute_overall_score(scored_reddit) if scored_reddit else None,
        "stocktwits": sent.compute_overall_score(scored_st) if scored_st else None,
        "news": sent.compute_overall_score(scored_news) if scored_news else None,
    }

    overall_score = sent.compute_overall_score(all_scored)
    confidence_full = sent.compute_confidence(source_scores)
    # "High (low variance ...)" → "High"
    confidence = confidence_full.split("(")[0].strip().split()[0]

    daily_trend = sent.compute_daily_trend(all_scored, days=days)
    trend_direction, trend_delta = sent.detect_trend_direction(daily_trend)

    bull, bear = sent.bull_bear_ratio(all_scored)
    st_bb = stocktwits_scraper.bull_bear_counts(st_messages)
    total_bb = bull + bear
    bull_pct = round(bull / total_bb * 100) if total_bb else 50

    hot_words = sent.extract_hot_topics(all_scored, ticker, top_n=8)
    n = max(len(hot_words), 1)
    hot_topics = [
        {"kw": w, "weight": round(1.0 - (i / n) * 0.6, 2)}
        for i, w in enumerate(hot_words)
    ]

    trend_formatted = _format_trend(daily_trend)
    price_info = _fetch_price(ticker)

    return {
        "ticker": ticker,
        "company": price_info["company"],
        "price": price_info["price"],
        "changePct": price_info["changePct"],
        "score": overall_score,
        "confidence": confidence,
        "mentions": len(all_scored),
        "bullPct": bull_pct,
        "trendDelta": round(trend_delta, 1),
        "trendDirection": trend_direction,
        "trend": trend_formatted,
        "hotTopics": hot_topics,
        "sources": {
            "reddit": {
                "score": source_scores["reddit"],
                "count": len(scored_reddit),
                "topPost": _best_reddit_post(scored_reddit),
                "error": errors.get("reddit"),
            },
            "stocktwits": {
                "score": source_scores["stocktwits"],
                "count": len(scored_st),
                "bull": st_bb["bull"],
                "bear": st_bb["bear"],
                "error": errors.get("stocktwits"),
            },
            "news": {
                "score": source_scores["news"],
                "count": len(scored_news),
                "topHeadline": _best_news_headline(scored_news),
                "error": errors.get("news"),
            },
        },
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DAY_NAMES = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def _format_trend(daily_trend: list) -> list:
    result = []
    for d in daily_trend:
        try:
            dt = datetime.strptime(d["date"], "%Y-%m-%d")
            day_label = _DAY_NAMES[dt.weekday()]
            date_label = dt.strftime("%b") + " " + str(dt.day)
        except ValueError:
            day_label = "—"
            date_label = d["date"]
        result.append({
            "day": day_label,
            "date": date_label,
            "score": d["score"] if d["score"] is not None else 50.0,
        })
    return result


def _best_reddit_post(scored: list) -> "dict | None":
    if not scored:
        return None
    best = max(scored, key=lambda i: i.get("compound", 0))
    title = (best.get("title") or "").strip()
    permalink = best.get("permalink", "")
    return {
        "text": title[:240] + ("..." if len(title) > 240 else ""),
        "upvotes": best.get("score", 0),
        "num_comments": best.get("num_comments", 0),
        "subreddit": best.get("subreddit", "reddit"),
        "url": ("https://reddit.com" + permalink) if permalink else "",
    }


def _best_news_headline(scored: list) -> "dict | None":
    if not scored:
        return None
    best = max(scored, key=lambda i: i.get("compound", 0))
    title = (best.get("title") or "").strip()
    return {
        "text": title[:240] + ("..." if len(title) > 240 else ""),
        "date_str": best.get("date_str", ""),
        "url": best.get("link", ""),
    }


def _fetch_price(ticker: str) -> dict:
    try:
        import yfinance as yf
        fi = yf.Ticker(ticker).fast_info
        price = float(fi.last_price or 0)
        prev = float(fi.previous_close or price or 1)
        change_pct = round((price - prev) / prev * 100, 2) if prev else 0.0
        return {
            "company": ticker,
            "price": round(price, 2),
            "changePct": change_pct,
        }
    except Exception:
        return {"company": ticker, "price": 0.0, "changePct": 0.0}
