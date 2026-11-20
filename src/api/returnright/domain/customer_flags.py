"""Flags a customer with more than 3 returns in the last 30 days for review."""

FLAG_WINDOW_DAYS = 30
MAX_RETURNS_BEFORE_FLAG = 3


def should_flag(returns_in_window: int) -> bool:
    """returns_in_window includes the return just created, so the 4th one flags."""
    return returns_in_window > MAX_RETURNS_BEFORE_FLAG
