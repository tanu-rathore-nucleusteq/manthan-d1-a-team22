"""BR 1.2: standard 30-day return window. Day 30 is returnable, day 31 is not."""

from datetime import date, timedelta

import pytest

from returnright.domain.eligibility import STANDARD_RETURN_WINDOW_DAYS, check_return_window

TODAY = date(2026, 11, 20)


def delivered(days_ago: int) -> date:
    return TODAY - timedelta(days=days_ago)


def test_standard_window_is_30_days():
    assert STANDARD_RETURN_WINDOW_DAYS == 30


@pytest.mark.parametrize("days_ago", [0, 1, 15, 29, 30])
def test_items_within_30_days_are_returnable(days_ago):
    decision = check_return_window(delivered(days_ago), TODAY)

    assert decision.eligible is True
    assert decision.days_since_delivery == days_ago


@pytest.mark.parametrize("days_ago", [31, 32, 45, 365])
def test_items_after_30_days_are_not_returnable(days_ago):
    decision = check_return_window(delivered(days_ago), TODAY)

    assert decision.eligible is False
    assert decision.days_since_delivery == days_ago


def test_window_ends_30_days_after_delivery():
    decision = check_return_window(date(2026, 11, 1), TODAY)

    assert decision.window_ends_on == date(2026, 12, 1)


def test_day_30_reason_names_the_last_day():
    decision = check_return_window(delivered(30), TODAY)

    assert decision.reason == (
        "You can return this item until 20 Nov 2026. It was delivered 30 days ago and the "
        "return window is 30 days."
    )


def test_day_31_reason_explains_the_window_has_ended():
    decision = check_return_window(delivered(31), TODAY)

    assert decision.reason == (
        "The 30-day return window ended on 19 Nov 2026. This item was delivered 31 days ago."
    )


@pytest.mark.parametrize(("days_ago", "phrase"), [(0, "delivered today"), (1, "1 day ago")])
def test_reason_reads_naturally_for_recent_deliveries(days_ago, phrase):
    assert phrase in check_return_window(delivered(days_ago), TODAY).reason


def test_undelivered_order_is_not_returnable():
    decision = check_return_window(None, TODAY)

    assert decision.eligible is False
    assert decision.window_ends_on is None
    assert decision.reason == "This order has not been delivered yet, so it can't be returned."


def test_delivery_date_in_the_future_is_treated_as_not_delivered():
    decision = check_return_window(TODAY + timedelta(days=1), TODAY)

    assert decision.eligible is False
    assert decision.days_since_delivery is None


def test_window_must_be_positive():
    with pytest.raises(ValueError, match="positive"):
        check_return_window(TODAY, TODAY, window_days=0)
