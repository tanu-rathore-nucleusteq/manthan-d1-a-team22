"""Category rules: electronics have a 10-day window, innerwear and perishables are never
returnable, everything else has 30 days. Every answer carries a plain-English reason.
"""

from datetime import date, timedelta

from returnright.domain.eligibility import CategoryRule, check_item

TODAY = date(2026, 11, 20)
APPAREL = CategoryRule("Apparel", is_returnable=True, window_days=30)
ELECTRONICS = CategoryRule("Electronics", is_returnable=True, window_days=10)
INNERWEAR = CategoryRule("Innerwear", is_returnable=False, window_days=None)
PERISHABLES = CategoryRule("Perishables", is_returnable=False, window_days=None)


def delivered(days_ago: int) -> date:
    return TODAY - timedelta(days=days_ago)


def test_electronics_day_10_is_allowed():
    assert check_item(ELECTRONICS, delivered(10), TODAY).eligible is True


def test_electronics_day_11_is_refused_with_the_10_day_window_in_the_reason():
    decision = check_item(ELECTRONICS, delivered(11), TODAY)

    assert decision.eligible is False
    assert decision.reason.startswith("Electronics can only be returned within 10 days")
    assert "11 days ago" in decision.reason


def test_apparel_day_30_is_allowed_and_day_31_is_refused():
    assert check_item(APPAREL, delivered(30), TODAY).eligible is True
    assert check_item(APPAREL, delivered(31), TODAY).eligible is False


def test_innerwear_is_never_returnable_even_on_the_day_of_delivery():
    decision = check_item(INNERWEAR, delivered(0), TODAY)

    assert decision.eligible is False
    assert decision.reason.startswith("Innerwear can't be returned")
    assert decision.window_ends_on is None


def test_perishables_are_never_returnable():
    assert check_item(PERISHABLES, delivered(1), TODAY).eligible is False


def test_mixed_basket_on_day_14_allows_the_shirt_and_refuses_the_phone():
    shirt = check_item(APPAREL, delivered(14), TODAY)
    phone = check_item(ELECTRONICS, delivered(14), TODAY)

    assert (shirt.eligible, phone.eligible) == (True, False)
    assert "10 days" in phone.reason


def test_undelivered_electronics_are_refused_without_a_window_prefix():
    decision = check_item(ELECTRONICS, None, TODAY)

    assert decision.eligible is False
    assert decision.reason.startswith("This order has not been delivered yet")
