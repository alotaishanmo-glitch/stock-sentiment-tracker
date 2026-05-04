"""
Sentiment scoring with FinBERT, daily trend analysis, and keyword extraction.
"""

import logging
import math
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_finbert_pipeline = None

BLOCK_CHARS = "▁▂▃▄▅▆▇█"


# ---------------------------------------------------------------------------
# FinBERT model
# ---------------------------------------------------------------------------

def _get_pipeline() -> Any:
    """Load FinBERT once and cache it for the process lifetime."""
    global _finbert_pipeline
    if _finbert_pipeline is None:
        print("\nLoading FinBERT model — first run downloads ~400 MB, please wait...", flush=True)
        from transformers import pipeline as hf_pipeline
        _finbert_pipeline = hf_pipeline(
            "text-classification",
            model="ProsusAI/finbert",
            top_k=None,
            device=-1,  # CPU; change to 0 for CUDA or "mps" for Apple Silicon
        )
        print("FinBERT ready.\n", flush=True)
    return _finbert_pipeline


def _batch_score(texts: List[str]) -> List[float]:
    """
    Run FinBERT on a batch of texts and return compound scores (positive - negative).

    Args:
        texts: Raw text strings. Each is truncated to 512 characters before scoring.

    Returns:
        List of floats in [-1, 1], one per input text.
    """
    if not texts:
        return []

    pipe = _get_pipeline()
    # FinBERT max is 512 tokens; 512 chars is a safe proxy that avoids slow truncation
    truncated = [t[:512] for t in texts]

    try:
        batch_results = pipe(truncated, batch_size=8, truncation=True, max_length=512)
    except Exception as exc:
        logger.warning("FinBERT batch scoring failed: %s — defaulting to 0.0", exc)
        return [0.0] * len(texts)

    compounds = []
    for result in batch_results:
        scores = {r["label"]: r["score"] for r in result}
        compound = scores.get("positive", 0.0) - scores.get("negative", 0.0)
        compounds.append(round(compound, 4))

    return compounds


# ---------------------------------------------------------------------------
# Per-source scoring
# ---------------------------------------------------------------------------

def score_reddit_posts(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Score Reddit posts with FinBERT and attach engagement weight.

    Args:
        posts: List of post dicts (title, selftext, score, created_utc, ...).

    Returns:
        List of scored dicts with compound, weight, date_str, source fields added.
    """
    items = []
    for post in posts:
        text = f"{post.get('title', '')} {post.get('selftext', '')}".strip()
        if not text:
            continue
        ts = post.get("created_utc", 0)
        try:
            day = datetime.fromtimestamp(float(ts), tz=timezone.utc).date().isoformat()
        except (ValueError, OSError):
            day = date.today().isoformat()
        items.append({**post, "text_combined": text, "date_str": day})

    if not items:
        return []

    compounds = _batch_score([i["text_combined"] for i in items])

    scored = []
    for item, compound in zip(items, compounds):
        upvotes = max(item.get("score", 0), 0)
        scored.append({
            **item,
            "compound": compound,
            "weight": math.log(upvotes + 1),
            "source": "reddit",
        })
    return scored


def score_stocktwits(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Score StockTwits messages with FinBERT and attach engagement weight.

    Args:
        messages: List of message dicts (body, likes, sentiment_label, ...).

    Returns:
        List of scored dicts with compound, weight, date_str, source fields added.
    """
    items = [m for m in messages if m.get("body", "").strip()]
    if not items:
        return []

    compounds = _batch_score([i["body"] for i in items])

    scored = []
    for item, compound in zip(items, compounds):
        likes = max(item.get("likes", 0), 0)
        scored.append({
            **item,
            "compound": compound,
            "weight": math.log(likes + 1),
            "source": "stocktwits",
        })
    return scored


def score_news(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Score news headlines with FinBERT.

    Args:
        articles: List of article dicts (title, summary, date_str, ...).

    Returns:
        List of scored dicts. All articles get equal weight (no engagement signal).
    """
    items = []
    for article in articles:
        text = f"{article.get('title', '')} {article.get('summary', '')}".strip()
        if not text:
            continue
        items.append({**article, "text_combined": text})

    if not items:
        return []

    compounds = _batch_score([i["text_combined"] for i in items])

    return [
        {**item, "compound": compound, "weight": 1.0, "source": "news"}
        for item, compound in zip(items, compounds)
    ]


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def compute_overall_score(scored_items: List[Dict[str, Any]]) -> float:
    """
    Weighted-average compound score scaled to 0–100.

    Args:
        scored_items: Any mix of scored dicts that each have 'compound' and 'weight'.

    Returns:
        Float in [0, 100]. Returns 50.0 when the list is empty.
    """
    if not scored_items:
        return 50.0

    total_weight = sum(item["weight"] for item in scored_items)
    if total_weight == 0:
        avg = sum(item["compound"] for item in scored_items) / len(scored_items)
    else:
        avg = sum(item["compound"] * item["weight"] for item in scored_items) / total_weight

    return round((avg + 1) / 2 * 100, 2)


def label_score(score: float) -> str:
    """Map a 0–100 score to a human-readable sentiment label with emoji."""
    if score <= 35:
        return "Bearish 🔴"
    if score <= 50:
        return "Slightly Bearish 🟡"
    if score <= 65:
        return "Slightly Bullish 🟡"
    return "Bullish 🟢"


def compute_confidence(source_scores: Dict[str, Optional[float]]) -> str:
    """
    Estimate confidence from variance across source scores.

    Args:
        source_scores: Dict mapping source name → score (None if unavailable).

    Returns:
        Human-readable confidence string.
    """
    valid = [s for s in source_scores.values() if s is not None]
    if len(valid) < 2:
        return "Low (single source)"

    mean = sum(valid) / len(valid)
    variance = sum((s - mean) ** 2 for s in valid) / len(valid)

    if variance < 25:
        return "High (low variance across sources)"
    if variance < 100:
        return "Medium (moderate variance)"
    return "Low (high variance across sources)"


def compute_confidence_score(source_scores: Dict[str, Optional[float]]) -> int:
    """
    Numeric confidence in [0, 100] derived from inverse variance + source coverage.

    More sources agreeing → higher score. Single source caps at ~45.
    """
    valid = [s for s in source_scores.values() if s is not None]
    if not valid:
        return 0
    if len(valid) == 1:
        return 45  # single source — cannot triangulate

    mean = sum(valid) / len(valid)
    variance = sum((s - mean) ** 2 for s in valid) / len(valid)

    # Map variance ∈ [0, 400+] → score ∈ [100, ~30]
    # variance 0 → 100, variance 25 → ~88, variance 100 → ~67, variance 400 → ~33
    raw = 100 * math.exp(-variance / 200)

    # Boost when all 3 sources are present
    coverage_bonus = 5 if len(valid) >= 3 else 0
    return min(100, max(0, round(raw + coverage_bonus)))


def bull_bear_ratio(all_scored: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Count bullish (compound > 0) vs bearish (compound < 0) items across all sources.

    Args:
        all_scored: Combined scored items list.

    Returns:
        Tuple of (bull_count, bear_count).
    """
    bull = sum(1 for i in all_scored if i.get("compound", 0) > 0)
    bear = sum(1 for i in all_scored if i.get("compound", 0) < 0)
    return bull, bear


def top_item(scored_items: List[Dict[str, Any]], source: str) -> Tuple[str, float]:
    """
    Find the highest-compound item from the given source.

    Args:
        scored_items: Combined scored items list.
        source: One of 'reddit', 'stocktwits', 'news'.

    Returns:
        Tuple of (text_snippet, compound). Returns ('N/A', 0.0) if none found.
    """
    candidates = [i for i in scored_items if i.get("source") == source]
    if not candidates:
        return "N/A", 0.0

    best = max(candidates, key=lambda i: i["compound"])

    if source == "reddit":
        text = best.get("title") or best.get("text_combined", "")
    elif source == "stocktwits":
        text = best.get("body", "")
    else:
        text = best.get("title") or best.get("text_combined", "")

    snippet = text[:72] + "..." if len(text) > 72 else text
    return snippet, best["compound"]


# ---------------------------------------------------------------------------
# Daily trend
# ---------------------------------------------------------------------------

def compute_daily_trend(scored_items: List[Dict[str, Any]], days: int = 7) -> List[Dict[str, Any]]:
    """
    Break scored items into daily buckets and compute a score per day.

    Args:
        scored_items: All scored items (must have 'date_str' field).
        days: Number of days to include in the trend window.

    Returns:
        List of dicts [{date, score, volume}] ordered oldest-first.
        score is None for days with no data.
    """
    today = date.today()
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for offset in range(days - 1, -1, -1):
        day = (today - timedelta(days=offset)).isoformat()
        buckets[day] = []

    for item in scored_items:
        day = item.get("date_str")
        if day in buckets:
            buckets[day].append(item)

    trend = []
    for day in sorted(buckets):
        items_that_day = buckets[day]
        score = compute_overall_score(items_that_day) if items_that_day else None
        trend.append({"date": day, "score": score, "volume": len(items_that_day)})

    return trend


def detect_trend_direction(daily_trend: List[Dict[str, Any]]) -> Tuple[str, float]:
    """
    Detect whether sentiment is improving, declining, or stable.

    Compares the average of the first two data-bearing days against the last two.

    Args:
        daily_trend: Output of compute_daily_trend.

    Returns:
        Tuple of (direction_label, delta). direction_label is one of
        'Improving', 'Declining', or 'Stable'.
    """
    valid = [d for d in daily_trend if d["score"] is not None]
    if len(valid) < 4:
        return "Stable", 0.0

    first_avg = (valid[0]["score"] + valid[1]["score"]) / 2
    last_avg = (valid[-2]["score"] + valid[-1]["score"]) / 2
    delta = round(last_avg - first_avg, 2)

    if delta > 3:
        return "Improving", delta
    if delta < -3:
        return "Declining", delta
    return "Stable", delta


def score_to_bar(score: float, min_s: float, max_s: float) -> str:
    """Map a score to a single block character proportional to its range position."""
    if max_s == min_s:
        return "▄"
    normalized = (score - min_s) / (max_s - min_s)
    idx = min(int(normalized * 8), 7)
    return BLOCK_CHARS[idx]


# ---------------------------------------------------------------------------
# Keyword extraction
# ---------------------------------------------------------------------------

def extract_hot_topics(
    scored_items: List[Dict[str, Any]], ticker: str, top_n: int = 10
) -> List[str]:
    """
    Extract the most-mentioned meaningful words across all scored items.

    Args:
        scored_items: All scored items from any source.
        ticker: Ticker symbol to exclude from results (e.g. 'TSLA').
        top_n: Number of top words to return.

    Returns:
        List of top words ordered by frequency.
    """
    import nltk

    try:
        nltk.data.find("corpora/stopwords")
    except LookupError:
        nltk.download("stopwords", quiet=True)

    from nltk.corpus import stopwords

    stop = set(stopwords.words("english"))
    # Add finance/Reddit boilerplate and ticker variants
    stop.update({
        ticker.lower(),
        f"${ticker.lower()}",
        "stock", "stocks", "share", "shares", "market", "trading",
        "price", "buy", "sell", "hold", "like", "think", "know",
        "amp", "https", "com", "www", "http",
    })

    word_counts: Counter = Counter()
    for item in scored_items:
        text = (
            item.get("text_combined")
            or item.get("body")
            or item.get("title")
            or item.get("text", "")
        )
        tokens = re.findall(r"\b[a-z]{3,}\b", text.lower())
        word_counts.update(t for t in tokens if t not in stop)

    return [word for word, _ in word_counts.most_common(top_n)]
