"""StockTwits data collection via public API (no authentication required)."""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
REQUEST_DELAY = 1  # seconds between calls


def fetch_messages(ticker: str, limit: int = 30) -> List[Dict[str, Any]]:
    """
    Fetch recent StockTwits messages for a ticker symbol.

    Args:
        ticker: Stock ticker (e.g. 'TSLA').
        limit: Max messages to return (free tier caps at 30 per call).

    Returns:
        List of message dicts with body, created_at, sentiment_label, likes.
    """
    url = BASE_URL.format(ticker=ticker.upper())

    try:
        time.sleep(REQUEST_DELAY)
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.HTTPError as exc:
        logger.warning("HTTP error fetching StockTwits for %s: %s", ticker, exc)
        return []
    except requests.exceptions.RequestException as exc:
        logger.warning("Request error fetching StockTwits for %s: %s", ticker, exc)
        return []
    except ValueError as exc:
        logger.warning("Failed to parse StockTwits JSON for %s: %s", ticker, exc)
        return []

    messages = data.get("messages", [])[:limit]
    results = []

    for msg in messages:
        created_raw = msg.get("created_at", "")
        date_str = _parse_date_str(created_raw)

        sentiment_info = msg.get("entities", {}).get("sentiment")
        sentiment_label = sentiment_info.get("basic") if sentiment_info else None

        likes = msg.get("likes", {}).get("total", 0) or 0

        results.append({
            "body": msg.get("body", ""),
            "created_at": created_raw,
            "date_str": date_str,
            "sentiment_label": sentiment_label,  # "Bullish", "Bearish", or None
            "likes": likes,
        })

    logger.info("Fetched %d StockTwits messages for %s", len(results), ticker)
    return results


def bull_bear_counts(messages: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Count explicit Bull/Bear labels from StockTwits messages.

    Args:
        messages: Raw or scored StockTwits message dicts.

    Returns:
        Dict with 'bull' and 'bear' counts.
    """
    bull = sum(1 for m in messages if m.get("sentiment_label") == "Bullish")
    bear = sum(1 for m in messages if m.get("sentiment_label") == "Bearish")
    return {"bull": bull, "bear": bear}


def _parse_date_str(created_at: str) -> str:
    """Parse a StockTwits ISO timestamp to a YYYY-MM-DD date string."""
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return dt.date().isoformat()
    except (ValueError, AttributeError):
        return datetime.now(tz=timezone.utc).date().isoformat()
