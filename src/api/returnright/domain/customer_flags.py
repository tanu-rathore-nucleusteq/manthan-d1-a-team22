"""Flags a customer with more than 3 returns in the last 30 days for review.

BR 1.2: the 4th return within 30 days flags the customer. A flag only asks the operations
manager to review the customer; flagged customers can still return items.

The window is counted in UTC calendar days and is inclusive, like the return window: a return
requested 30 days ago still counts, one requested 31 days ago does not. The count includes the
return being created now.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

FLAG_RETURN_LIMIT = 3
"""BR 1.2: more returns than this within the window flags the customer."""

FLAG_WINDOW_DAYS = 30
"""BR 1.2: the rolling window, in days, for counting a customer's returns."""


@dataclass(frozen=True, slots=True)
class FlagCheck:
    flagged: bool
    returns_in_window: int
    window_starts_on: date
    reason: str


def window_starts_on(today: date) -> date:
    """The first day that still counts: returns requested on or after it are in the window."""
    return today - timedelta(days=FLAG_WINDOW_DAYS)


def returns_in_window(requested_on: Iterable[date], today: date) -> int:
    """How many of the customer's returns fall between window_starts_on(today) and today."""
    start = window_starts_on(today)
    return sum(1 for day in requested_on if start <= day <= today)


def check_frequent_returner(requested_on: Iterable[date], today: date) -> FlagCheck:
    """Decide whether the customer is flagged, given the dates of their returns (UTC, including
    the one being created today), and explain why for the operations manager.
    """
    count = returns_in_window(requested_on, today)
    flagged = count > FLAG_RETURN_LIMIT
    returns = "1 return" if count == 1 else f"{count} returns"
    if flagged:
        reason = (
            f"{returns} in the last {FLAG_WINDOW_DAYS} days, which is more than "
            f"{FLAG_RETURN_LIMIT}, so this customer is flagged for review. They can still "
            "return items."
        )
    else:
        reason = (
            f"{returns} in the last {FLAG_WINDOW_DAYS} days, which is not more than "
            f"{FLAG_RETURN_LIMIT}, so this customer is not flagged."
        )
    return FlagCheck(
        flagged=flagged,
        returns_in_window=count,
        window_starts_on=window_starts_on(today),
        reason=reason,
    )
