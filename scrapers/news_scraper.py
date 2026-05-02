"""Yahoo Finance RSS news scraper (no authentication required)."""

import logging
from datetime import date, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

RSS_URL = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"


def fetch_headlines(ticker: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Fetch recent Yahoo Finance news headlines for a ticker via RSS.

    Args:
        ticker: Stock ticker (e.g. 'AAPL').
        limit: Maximum number of headlines to return.

    Returns:
        List of article dicts with title, summary, published, link, date_str.
    """
    try:
        import feedparser
    except ImportError:
        logger.warning("feedparser not installed — skipping news collection.")
        return []

    url = RSS_URL.format(ticker=ticker.upper())

    try:
        feed = feedparser.parse(url)
    except Exception as exc:
        logger.warning("Failed to fetch Yahoo Finance RSS for %s: %s", ticker, exc)
        return []

    if feed.bozo and not feed.entries:
        logger.warning("Yahoo Finance RSS returned no entries for %s.", ticker)
        return []

    results = []
    for entry in feed.entries[:limit]:
        published_parsed = entry.get("published_parsed")
        if published_parsed:
            try:
                pub_date = date(*published_parsed[:3]).isoformat()
            except (TypeError, ValueError):
                pub_date = date.today().isoformat()
        else:
            pub_date = date.today().isoformat()

        results.append({
            "title": entry.get("title", ""),
            "summary": entry.get("summary", ""),
            "published": entry.get("published", ""),
            "date_str": pub_date,
            "link": entry.get("link", ""),
        })

    logger.info("Fetched %d news headlines for %s", len(results), ticker)
    return results
