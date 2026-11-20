"""Eligibility engine: decides per item whether it can be returned (30-day window, 10 days for
electronics, never innerwear or perishables) and explains why in plain English.

The windows come from the categories table, so check_item applies whatever the data says;
check_return_window is the window rule on its own (BR 1.2).
"""

from dataclasses import dataclass, replace
from datetime import date, timedelta

STANDARD_RETURN_WINDOW_DAYS = 30
"""BR 1.2: an item can be returned up to and including day 30 after delivery."""


@dataclass(frozen=True, slots=True)
class EligibilityDecision:
    eligible: bool
    reason: str
    days_since_delivery: int | None
    window_ends_on: date | None


def check_return_window(
    delivered_on: date | None,
    today: date,
    window_days: int = STANDARD_RETURN_WINDOW_DAYS,
) -> EligibilityDecision:
    """Apply the return window to one item.

    Day 0 is the delivery date. The last allowed day is delivered_on + window_days, so with the
    standard window day 30 is returnable and day 31 is not.
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

    if days <= window_days:
        return EligibilityDecision(
            eligible=True,
            reason=(
                f"You can return this item until {_format(window_ends_on)}. It was delivered "
                f"{_days_ago(days)} and the return window is {window_days} days."
            ),
            days_since_delivery=days,
            window_ends_on=window_ends_on,
        )

    return EligibilityDecision(
        eligible=False,
        reason=(
            f"The {window_days}-day return window ended on {_format(window_ends_on)}. "
            f"This item was delivered {_days_ago(days)}."
        ),
        days_since_delivery=days,
        window_ends_on=window_ends_on,
    )


@dataclass(frozen=True, slots=True)
class CategoryRule:
    """The return rule of a product category, as stored in the categories table."""

    name: str
    is_returnable: bool
    window_days: int | None


def check_item(
    category: CategoryRule, delivered_on: date | None, today: date
) -> EligibilityDecision:
    """Apply the category rule, then the category's return window, to one item."""
    days = (today - delivered_on).days if delivered_on and delivered_on <= today else None

    if not category.is_returnable or category.window_days is None:
        return EligibilityDecision(
            eligible=False,
            reason=(
                f"{category.name} can't be returned for hygiene and safety reasons. If the item "
                "arrived damaged or is not what you ordered, please contact customer support."
            ),
            days_since_delivery=days,
            window_ends_on=None,
        )

    decision = check_return_window(delivered_on, today, category.window_days)
    if decision.eligible or days is None or category.window_days == STANDARD_RETURN_WINDOW_DAYS:
        return decision
    return replace(
        decision,
        reason=(
            f"{category.name} can only be returned within {category.window_days} days of "
            f"delivery. {decision.reason}"
        ),
    )


def _format(day: date) -> str:
    return f"{day.day} {day:%b %Y}"  # 19 Dec 2026, same on every OS


def _days_ago(days: int) -> str:
    if days == 0:
        return "today"
    return f"{days} day ago" if days == 1 else f"{days} days ago"
