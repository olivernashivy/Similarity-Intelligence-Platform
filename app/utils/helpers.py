"""Helper utilities."""
from datetime import datetime, timedelta
from typing import Tuple


def get_current_billing_period() -> Tuple[datetime, datetime]:
    """
    Get current billing period (monthly).

    Returns:
        Tuple of (period_start, period_end)
    """
    now = datetime.utcnow()

    # Start of current month
    period_start = datetime(now.year, now.month, 1)

    # Start of next month
    if now.month == 12:
        period_end = datetime(now.year + 1, 1, 1)
    else:
        period_end = datetime(now.year, now.month + 1, 1)

    return period_start, period_end


def calculate_ttl_expiry(days: int) -> datetime:
    """
    Calculate expiry datetime for TTL.

    Args:
        days: Number of days until expiry

    Returns:
        Expiry datetime
    """
    return datetime.utcnow() + timedelta(days=days)


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.

    Args:
        text: Input text
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix
