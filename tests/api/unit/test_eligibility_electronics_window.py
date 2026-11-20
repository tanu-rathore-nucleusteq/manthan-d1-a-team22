"""BR 1.2: electronics have a 10-day return window. Day 10 is returnable, day 11 is not."""

from datetime import date, timedelta

import pytest

from returnright.domain.eligibility import (
    ELECTRONICS_RETURN_WINDOW_DAYS,
    STANDARD_RETURN_WINDOW_DAYS,
    check_return_window,
    window_days_for,
)

TODAY = date(2026, 11, 20)


def electronics(days_ago: int):
    return check_return_window(
        TODAY - timedelta(days=days_ago),
        TODAY,
        window_days=ELECTRONICS_RETURN_WINDOW_DAYS,
        category="Electronics",
    )


def test_electronics_window_is_10_days():
    assert ELECTRONICS_RETURN_WINDOW_DAYS == 10


@pytest.mark.parametrize("days_ago", [0, 1, 5, 9, 10])
def test_electronics_within_10_days_are_returnable(days_ago):
    decision = electronics(days_ago)

    assert decision.eligible is True
    assert decision.days_since_delivery == days_ago


@pytest.mark.parametrize("days_ago", [11, 12, 14, 30])
def test_electronics_after_10_days_are_not_returnable(days_ago):
    assert electronics(days_ago).eligible is False


def test_electronics_window_ends_10_days_after_delivery():
    assert electronics(3).window_ends_on == date(2026, 11, 27)


def test_day_10_reason_names_the_electronics_rule():
    assert electronics(10).reason == (
        "You can return this item until 20 Nov 2026. It was delivered 10 days ago and "
        "Electronics items have a 10-day return window."
    )


def test_day_11_reason_explains_the_electronics_window_has_ended():
    assert electronics(11).reason == (
        "Electronics items have a 10-day return window, which ended on 19 Nov 2026. "
        "This item was delivered 11 days ago."
    )


def test_day_14_electronics_refused_while_other_items_still_returnable():
    delivered_on = TODAY - timedelta(days=14)

    phone = check_return_window(delivered_on, TODAY, 10, category="Electronics")
    shirt = check_return_window(delivered_on, TODAY, 30, category="Apparel")

    assert (phone.eligible, shirt.eligible) == (False, True)


def test_standard_window_keeps_the_standard_reason_even_with_a_category():
    reason = check_return_window(TODAY - timedelta(days=5), TODAY, 30, category="Apparel").reason

    assert reason.endswith("and the return window is 30 days.")
    assert "Apparel" not in reason


@pytest.mark.parametrize(
    ("configured", "expected"),
    [(10, 10), (30, 30), (None, STANDARD_RETURN_WINDOW_DAYS)],
)
def test_window_comes_from_the_category_or_falls_back_to_30_days(configured, expected):
    assert window_days_for(configured) == expected
