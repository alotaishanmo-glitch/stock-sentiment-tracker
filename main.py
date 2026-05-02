"""
Entry point for the Stock Sentiment Tracker.

Usage:
    python main.py TSLA
    python main.py AAPL --days 3 --limit 50
"""

import argparse
import json
import logging
import os
import sys
from datetime import date, datetime

from scrapers import reddit_scraper, stocktwits_scraper, news_scraper
from analysis import sentiment as sent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

WIDTH = 50
DIV = "=" * WIDTH
THIN = "-" * WIDTH


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Stock Sentiment Tracker")
    parser.add_argument("ticker", type=str, help="Stock ticker symbol (e.g. TSLA)")
    parser.add_argument("--days", type=int, default=7, help="Lookback window in days (default: 7)")
    parser.add_argument("--limit", type=int, default=50, help="Max items per source (default: 50)")
    return parser.parse_args()


def save_output(ticker: str, payload: dict) -> str:
    """
    Serialize payload to output/{TICKER}_{date}.json.

    Args:
        ticker: Ticker symbol used in the filename.
        payload: Data to write.

    Returns:
        Path of the written file.
    """
    os.makedirs("output", exist_ok=True)
    filename = f"output/{ticker.upper()}_{date.today().isoformat()}.json"
    with open(filename, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False, default=str)
    return filename


def _format_date_header() -> str:
    """Return today's date formatted as 'May 2 2026'."""
    return datetime.today().strftime("%b %-d %Y")


def _trend_arrow(direction: str) -> str:
    return {"Improving": "📈", "Declining": "📉", "Stable": "➡️"}.get(direction, "")


def print_report(
    ticker: str,
    overall_score: float,
    label: str,
    confidence: str,
    trend_direction: str,
    trend_delta: float,
    source_scores: dict,
    reddit_count: int,
    st_count: int,
    st_bull: int,
    st_bear: int,
    news_count: int,
    bull: int,
    bear: int,
    total_volume: int,
    daily_trend: list,
    hot_topics: list,
    top_reddit: tuple,
    top_st: tuple,
    top_news: tuple,
    days: int,
) -> None:
    """Print the full formatted sentiment report to stdout."""
    date_str = _format_date_header()
    arrow = _trend_arrow(trend_direction)
    delta_sign = "+" if trend_delta >= 0 else ""

    total_tagged = bull + bear
    bull_pct = round(bull / total_tagged * 100) if total_tagged else 0
    bear_pct = 100 - bull_pct if total_tagged else 0

    print(f"\n{DIV}")
    print(f"  Sentiment Report: ${ticker}  |  {date_str}")
    print(DIV)
    print(f"  SCORE:      {overall_score} / 100   {label}")
    print(f"  CONFIDENCE: {confidence}")
    print(f"  TREND:      {arrow} {trend_direction} ({delta_sign}{trend_delta} over {days} days)")
    print(THIN)
    print("  SOURCES")

    r_score = source_scores.get("reddit")
    st_score = source_scores.get("stocktwits")
    n_score = source_scores.get("news")

    r_str = f"{r_score:.1f}" if r_score is not None else "N/A"
    print(f"  Reddit:      {r_str}  ({reddit_count} posts across 4 subreddits)")

    st_str = f"{st_score:.1f}" if st_score is not None else "N/A"
    print(f"  StockTwits:  {st_str}  ({st_count} messages | 🐂 {st_bull} Bull / 🐻 {st_bear} Bear)")

    n_str = f"{n_score:.1f}" if n_score is not None else "N/A"
    print(f"  News:        {n_str}  ({news_count} headlines)")

    print(THIN)
    print(f"  BULL/BEAR RATIO:  {bull_pct}% Bull  |  {bear_pct}% Bear")
    print(f"  MENTION VOLUME:   {total_volume} total posts ({days} days)")
    print(THIN)

    # Daily trend bar chart
    valid_scores = [d["score"] for d in daily_trend if d["score"] is not None]
    min_s = min(valid_scores) if valid_scores else 50.0
    max_s = max(valid_scores) if valid_scores else 50.0

    print("  DAILY TREND")
    for day_data in daily_trend:
        day_label = datetime.strptime(day_data["date"], "%Y-%m-%d").strftime("%b %d")
        score = day_data["score"]
        if score is None:
            bar = "—"
            score_str = "  N/A"
        else:
            bar = sent.score_to_bar(score, min_s, max_s)
            score_str = f"{score:5.1f}"
        print(f"  {day_label}: {score_str}  {bar}")

    print(THIN)

    # Hot topics
    if hot_topics:
        topic_str = ", ".join(hot_topics[:5])
        overflow = ", ".join(hot_topics[5:]) if len(hot_topics) > 5 else ""
        print(f"  HOT TOPICS:  {topic_str},")
        if overflow:
            print(f"               {overflow}")
    else:
        print("  HOT TOPICS:  N/A")

    print(THIN)
    print("  TOP POSTS")

    def _top_line(label_str: str, item_tuple: tuple) -> None:
        text, score = item_tuple
        if text != "N/A":
            print(f'  {label_str:<13} "{text}"')
            print(f'  {"":13} ({score:+.2f})')
        else:
            print(f"  {label_str:<13} N/A")

    _top_line("Reddit:", top_reddit)
    _top_line("StockTwits:", top_st)
    _top_line("News:", top_news)

    print(f"{DIV}\n")


def main() -> None:
    """Orchestrate data collection, analysis, and output."""
    args = parse_args()
    ticker = args.ticker.upper()

    print(f"\nFetching sentiment data for ${ticker} (last {args.days} days)...")

    # --- Collect raw data ---
    reddit_posts = reddit_scraper.fetch_all(ticker, limit=args.limit, days=args.days)
    st_messages = stocktwits_scraper.fetch_messages(ticker, limit=30)
    news_articles = news_scraper.fetch_headlines(ticker, limit=20)

    if not reddit_posts and not st_messages and not news_articles:
        logger.error("No data collected from any source. Exiting.")
        sys.exit(1)

    # --- Score all sources (FinBERT loads here on first run) ---
    scored_reddit = sent.score_reddit_posts(reddit_posts)
    scored_st = sent.score_stocktwits(st_messages)
    scored_news = sent.score_news(news_articles)
    all_scored = scored_reddit + scored_st + scored_news

    # --- Per-source scores ---
    source_scores = {
        "reddit": sent.compute_overall_score(scored_reddit) if scored_reddit else None,
        "stocktwits": sent.compute_overall_score(scored_st) if scored_st else None,
        "news": sent.compute_overall_score(scored_news) if scored_news else None,
    }

    overall_score = sent.compute_overall_score(all_scored)
    label = sent.label_score(overall_score)
    confidence = sent.compute_confidence(source_scores)

    # --- Trend ---
    daily_trend = sent.compute_daily_trend(all_scored, days=args.days)
    trend_direction, trend_delta = sent.detect_trend_direction(daily_trend)

    # --- Bull/bear ---
    bull, bear = sent.bull_bear_ratio(all_scored)
    st_bb = stocktwits_scraper.bull_bear_counts(st_messages)

    # --- Top posts ---
    top_reddit = sent.top_item(all_scored, "reddit")
    top_st = sent.top_item(all_scored, "stocktwits")
    top_news = sent.top_item(all_scored, "news")

    # --- Hot topics ---
    hot_topics = sent.extract_hot_topics(all_scored, ticker)

    # --- Print report ---
    print_report(
        ticker=ticker,
        overall_score=overall_score,
        label=label,
        confidence=confidence,
        trend_direction=trend_direction,
        trend_delta=trend_delta,
        source_scores=source_scores,
        reddit_count=len(scored_reddit),
        st_count=len(scored_st),
        st_bull=st_bb["bull"],
        st_bear=st_bb["bear"],
        news_count=len(scored_news),
        bull=bull,
        bear=bear,
        total_volume=len(all_scored),
        daily_trend=daily_trend,
        hot_topics=hot_topics,
        top_reddit=top_reddit,
        top_st=top_st,
        top_news=top_news,
        days=args.days,
    )

    # --- Save JSON ---
    payload = {
        "ticker": ticker,
        "date": date.today().isoformat(),
        "days": args.days,
        "score": overall_score,
        "label": label,
        "confidence": confidence,
        "trend": {"direction": trend_direction, "delta": trend_delta},
        "source_scores": source_scores,
        "reddit_count": len(scored_reddit),
        "stocktwits_count": len(scored_st),
        "news_count": len(scored_news),
        "bull_count": bull,
        "bear_count": bear,
        "total_volume": len(all_scored),
        "daily_trend": daily_trend,
        "hot_topics": hot_topics,
        "top_reddit_post": {"text": top_reddit[0], "compound": top_reddit[1]},
        "top_stocktwits": {"text": top_st[0], "compound": top_st[1]},
        "top_news": {"text": top_news[0], "compound": top_news[1]},
        "reddit_posts": scored_reddit,
        "stocktwits_messages": scored_st,
        "news_articles": scored_news,
    }

    output_path = save_output(ticker, payload)
    print(f"Full results saved to: {output_path}\n")


if __name__ == "__main__":
    main()
