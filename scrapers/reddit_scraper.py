"""Reddit data collection via public JSON endpoints (no API key required)."""

import logging
import time
from typing import List, Dict, Any

import requests

from config import REDDIT_SUBREDDITS, REDDIT_USER_AGENT, REDDIT_DELAY_SECONDS

logger = logging.getLogger(__name__)

BASE_URL = "https://www.reddit.com/r/{subreddit}/search.json"


def fetch_subreddit(subreddit: str, ticker: str, limit: int, days: int) -> List[Dict[str, Any]]:
    """
    Fetch posts from a single subreddit matching the ticker.

    Args:
        subreddit: Subreddit name (e.g. 'wallstreetbets').
        ticker: Stock ticker to search for (e.g. 'TSLA').
        limit: Maximum number of posts to fetch.
        days: Time window in days; maps to Reddit's 't' param (capped at 'week').

    Returns:
        List of post dicts with title, selftext, score, created_utc,
        subreddit, and num_comments.
    """
    time_filter = _days_to_time_filter(days)
    url = BASE_URL.format(subreddit=subreddit)
    params = {
        "q": ticker,
        "sort": "new",
        "limit": min(limit, 100),
        "t": time_filter,
        "restrict_sr": "true",
    }
    headers = {"User-Agent": REDDIT_USER_AGENT}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.HTTPError as exc:
        logger.warning("HTTP error fetching r/%s: %s", subreddit, exc)
        return []
    except requests.exceptions.RequestException as exc:
        logger.warning("Request error fetching r/%s: %s", subreddit, exc)
        return []
    except ValueError as exc:
        logger.warning("Failed to parse JSON from r/%s: %s", subreddit, exc)
        return []

    posts = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        posts.append({
            "title": post.get("title", ""),
            "selftext": post.get("selftext", ""),
            "score": post.get("score", 0),
            "created_utc": post.get("created_utc", 0),
            "subreddit": post.get("subreddit", subreddit),
            "num_comments": post.get("num_comments", 0),
            "permalink": post.get("permalink", ""),
        })

    logger.info("Fetched %d posts from r/%s", len(posts), subreddit)
    return posts


def fetch_all(ticker: str, limit: int = 25, days: int = 7) -> List[Dict[str, Any]]:
    """
    Fetch posts from all configured subreddits for the given ticker.

    Args:
        ticker: Stock ticker (e.g. 'AAPL').
        limit: Posts per subreddit.
        days: Lookback window in days.

    Returns:
        Combined list of post dicts from all subreddits.
    """
    all_posts: List[Dict[str, Any]] = []

    for i, subreddit in enumerate(REDDIT_SUBREDDITS):
        if i > 0:
            time.sleep(REDDIT_DELAY_SECONDS)
        posts = fetch_subreddit(subreddit, ticker, limit, days)
        all_posts.extend(posts)

    logger.info("Total Reddit posts collected: %d", len(all_posts))
    return all_posts


def _days_to_time_filter(days: int) -> str:
    """Map a day count to Reddit's time filter parameter."""
    if days <= 1:
        return "day"
    if days <= 7:
        return "week"
    if days <= 30:
        return "month"
    if days <= 365:
        return "year"
    return "all"
