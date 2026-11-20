"""BR 1.2: innerwear and perishables are never returnable, whatever the date."""

from datetime import date, timedelta

import pytest

from returnright.domain.eligibility import NON_RETURNABLE_CATEGORIES, decide_eligibility

TODAY = date(2026, 11, 20)


def decide(category: str, *, is_returnable: bool, window_days: int | None, days_ago: int | None):
    delivered_on = None if days_ago is None else TODAY - timedelta(days=days_ago)
    return decide_eligibility(
        delivered_on,
        TODAY,
        category=category,
        is_returnable=is_returnable,
        window_days=window_days,
    )


def test_innerwear_and_perishables_are_the_non_returnable_categories():
    assert frozenset({"Innerwear", "Perishables"}) == NON_RETURNABLE_CATEGORIES


@pytest.mark.parametrize("category", sorted(NON_RETURNABLE_CATEGORIES))
@pytest.mark.parametrize("days_ago", [0, 1, 5, 30, None])
def test_non_returnable_categories_are_refused_whatever_the_date(category, days_ago):
    decision = decide(category, is_returnable=False, window_days=None, days_ago=days_ago)

    assert decision.eligible is False
    assert decision.window_ends_on is None
    assert decision.days_since_delivery is None


@pytest.mark.parametrize("category", sorted(NON_RETURNABLE_CATEGORIES))
def test_reason_names_the_category(category):
    decision = decide(category, is_returnable=False, window_days=None, days_ago=2)

    assert decision.reason == f"{category} items can't be returned under our returns policy."


def test_not_returnable_wins_over_not_delivered():
    """The permanent reason is more useful to the customer than 'not delivered yet'."""
    decision = decide("Innerwear", is_returnable=False, window_days=None, days_ago=None)

    assert decision.reason == "Innerwear items can't be returned under our returns policy."


def test_not_returnable_wins_even_if_a_window_is_set():
    decision = decide("Perishables", is_returnable=False, window_days=30, days_ago=1)

    assert decision.eligible is False


@pytest.mark.parametrize(
    ("category", "window_days", "days_ago", "eligible"),
    [
        ("Apparel", 30, 30, True),
        ("Apparel", 30, 31, False),
        ("Electronics", 10, 10, True),
        ("Electronics", 10, 11, False),
        ("Footwear", None, 30, True),  # no window set: standard 30 days
    ],
)
def test_returnable_categories_still_follow_their_window(category, window_days, days_ago, eligible):
    decision = decide(category, is_returnable=True, window_days=window_days, days_ago=days_ago)

    assert decision.eligible is eligible
