"""Handles API rate limiting with wait-and-retry logic."""

import time
import logging

logger = logging.getLogger(__name__)


def wait_and_retry(func, *args, wait_seconds=900, max_retries=1, **kwargs):
    """
    Call func with args/kwargs; if a rate-limit error occurs, wait and retry.

    Args:
        func: Callable to invoke.
        *args: Positional args forwarded to func.
        wait_seconds: Seconds to sleep on rate-limit hit (default 15 min).
        max_retries: Maximum number of retry attempts.
        **kwargs: Keyword args forwarded to func.

    Returns:
        Return value of func, or None if all retries are exhausted.
    """
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            if attempt < max_retries and _is_rate_limit_error(exc):
                logger.warning(
                    "Rate limit hit. Waiting %d seconds before retry %d/%d...",
                    wait_seconds,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(wait_seconds)
            else:
                raise
    return None


def _is_rate_limit_error(exc: Exception) -> bool:
    """Return True if the exception looks like a rate-limit (HTTP 429) error."""
    msg = str(exc).lower()
    return "429" in msg or "rate limit" in msg or "too many requests" in msg


def polite_delay(seconds: float) -> None:
    """Sleep for the given number of seconds to be polite to public APIs."""
    time.sleep(seconds)
