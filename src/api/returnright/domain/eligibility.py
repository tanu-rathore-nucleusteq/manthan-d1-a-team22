"""Eligibility engine: decides per item whether it can be returned (30-day window, 10 days for
electronics, never innerwear or perishables) and explains why in plain English.

Implemented: BR 1.2 in full. decide_eligibility() is the entry point and applies, in order:
1. not returnable: categories.is_returnable is FALSE (Innerwear, Perishables), whatever the date;
2. return window: categories.return_window_days (10 for Electronics, otherwise the standard 30).
The rules live in data (the categories table); the constants below document and test them.
"""

from dataclasses import dataclass
from datetime import date, timedelta

STANDARD_RETURN_WINDOW_DAYS = 30
"""BR 1.2: an item can be returned up to and including day 30 after delivery."""

ELECTRONICS_RETURN_WINDOW_DAYS = 10
"""BR 1.2: electronics can be returned up to and including day 10 after delivery. Stored as
categories.return_window_days for the Electronics row; this constant documents and tests it."""


NON_RETURNABLE_CATEGORIES = frozenset({"Innerwear", "Perishables"})
"""BR 1.2: these categories are never returnable. Stored as categories.is_returnable = FALSE;
this constant documents and tests it."""


def window_days_for(category_window_days: int | None) -> int:
    """The category's own window, or the standard 30 days when the category sets none."""
    return category_window_days or STANDARD_RETURN_WINDOW_DAYS


@dataclass(frozen=True, slots=True)
class EligibilityDecision:
    eligible: bool
    reason: str
    days_since_delivery: int | None
    window_ends_on: date | None


def decide_eligibility(
    delivered_on: date | None,
    today: date,
    *,
    category: str,
    is_returnable: bool,
    window_days: int | None,
) -> EligibilityDecision:
    """Decide one item: a non-returnable category is refused first, then the return window
    applies (the category's window, or the standard 30 days when it sets none).
    """
    if not is_returnable:
        return EligibilityDecision(
            eligible=False,
            reason=f"{category} items can't be returned under our returns policy.",
            days_since_delivery=None,
            window_ends_on=None,
        )
    return check_return_window(
        delivered_on, today, window_days=window_days_for(window_days), category=category
    )


def check_return_window(
    delivered_on: date | None,
    today: date,
    window_days: int = STANDARD_RETURN_WINDOW_DAYS,
    category: str | None = None,
) -> EligibilityDecision:
    """Apply the return window to one item.

    Day 0 is the delivery date. The last allowed day is delivered_on + window_days, so with the
    standard window day 30 is returnable and day 31 is not; for electronics, day 10 versus day 11.
    When the window differs from the standard one, the reason names the category's rule.
    """
    if window_days <= 0:
        raise ValueError("window_days must be positive")

    if delivered_on is None or delivered_on > today:
        return EligibilityDecision(
            eligible=False,
            reason="This order has not been delivered yet, so it can't be returned.",
            days_since_delivery=None,
            window_ends_on=None,
        )

    days = (today - delivered_on).days
    window_ends_on = delivered_on + timedelta(days=window_days)
    ends, ago = _format(window_ends_on), _days_ago(days)
    category_rule = category is not None and window_days != STANDARD_RETURN_WINDOW_DAYS

    if days <= window_days:
        rule = (
            f"{category} items have a {window_days}-day return window"
            if category_rule
            else f"the return window is {window_days} days"
        )
        return EligibilityDecision(
            eligible=True,
            reason=f"You can return this item until {ends}. It was delivered {ago} and {rule}.",
            days_since_delivery=days,
            window_ends_on=window_ends_on,
        )

    ended = (
        f"{category} items have a {window_days}-day return window, which ended on {ends}."
        if category_rule
        else f"The {window_days}-day return window ended on {ends}."
    )
    return EligibilityDecision(
        eligible=False,
        reason=f"{ended} This item was delivered {ago}.",
        days_since_delivery=days,
        window_ends_on=window_ends_on,
    )


def _format(day: date) -> str:
    return f"{day.day} {day:%b %Y}"  # 19 Dec 2026, same on every OS


def _days_ago(days: int) -> str:
    if days == 0:
        return "today"
    return f"{days} day ago" if days == 1 else f"{days} days ago"
