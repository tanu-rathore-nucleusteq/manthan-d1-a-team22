"""BR 1.2: more than 3 returns in 30 days flags the customer; the 4th return is the trigger."""

from datetime import date, timedelta

import pytest

from returnright.domain.customer_flags import (
    FLAG_RETURN_LIMIT,
    FLAG_WINDOW_DAYS,
    check_frequent_returner,
    returns_in_window,
    window_starts_on,
)

TODAY = date(2026, 11, 20)


def days_ago(*days: int) -> list[date]:
    return [TODAY - timedelta(days=d) for d in days]


def test_limit_is_3_returns_in_30_days():
    assert (FLAG_RETURN_LIMIT, FLAG_WINDOW_DAYS) == (3, 30)


@pytest.mark.parametrize("count", [0, 1, 2, 3])
def test_up_to_3_returns_in_30_days_is_not_flagged(count):
    assert check_frequent_returner(days_ago(*range(count)), TODAY).flagged is False


def test_4th_return_in_30_days_flags_the_customer():
    check = check_frequent_returner(days_ago(20, 12, 5, 0), TODAY)

    assert check.flagged is True
    assert check.returns_in_window == 4


def test_more_than_4_returns_stays_flagged():
    assert check_frequent_returner(days_ago(1, 2, 3, 4, 5, 6), TODAY).flagged is True


def test_return_requested_30_days_ago_still_counts():
    assert check_frequent_returner(days_ago(30, 10, 5, 0), TODAY).flagged is True


def test_return_requested_31_days_ago_no_longer_counts():
    check = check_frequent_returner(days_ago(31, 10, 5, 0), TODAY)

    assert check.flagged is False
    assert check.returns_in_window == 3


def test_old_returns_outside_the_window_are_ignored():
    assert check_frequent_returner(days_ago(90, 60, 45, 31, 0), TODAY).flagged is False


def test_dates_after_today_are_ignored():
    assert returns_in_window([TODAY + timedelta(days=1), TODAY], TODAY) == 1


def test_several_returns_on_the_same_day_each_count():
    assert check_frequent_returner([TODAY] * 4, TODAY).flagged is True


def test_window_starts_30_days_before_today():
    assert window_starts_on(TODAY) == date(2026, 10, 21)
    assert check_frequent_returner([], TODAY).window_starts_on == date(2026, 10, 21)


def test_reason_when_flagged_says_they_can_still_return():
    check = check_frequent_returner(days_ago(20, 12, 5, 0), TODAY)

    assert check.reason == (
        "4 returns in the last 30 days, which is more than 3, so this customer is flagged for "
        "review. They can still return items."
    )


def test_reason_when_not_flagged():
    assert check_frequent_returner(days_ago(12, 5, 0), TODAY).reason == (
        "3 returns in the last 30 days, which is not more than 3, so this customer is not flagged."
    )


def test_reason_uses_singular_for_one_return():
    assert check_frequent_returner(days_ago(0), TODAY).reason.startswith("1 return in the last")
