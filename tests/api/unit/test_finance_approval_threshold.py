"""BR 1.2: a return's refund total strictly above 10,000 INR needs finance approval."""

from decimal import Decimal

import pytest

from returnright.core.config import Settings
from returnright.domain.refund_policy import (
    FINANCE_APPROVAL_THRESHOLD_INR,
    check_finance_approval,
    refund_total,
    requires_finance_approval,
)


def test_threshold_is_10000_inr():
    assert Decimal("10000") == FINANCE_APPROVAL_THRESHOLD_INR


def test_settings_default_matches_the_rule():
    assert Settings().finance_approval_threshold_inr == FINANCE_APPROVAL_THRESHOLD_INR


@pytest.mark.parametrize("total", ["0.00", "1.00", "9999.99", "10000.00"])
def test_total_up_to_10000_is_paid_without_approval(total):
    assert requires_finance_approval(Decimal(total)) is False


@pytest.mark.parametrize("total", ["10000.01", "10001.00", "12000.00", "250000.00"])
def test_total_above_10000_needs_approval(total):
    assert requires_finance_approval(Decimal(total)) is True


def test_check_uses_the_return_total_not_each_item():
    """Two items of 6,000 each: neither is above 10,000, but the return total is."""
    check = check_finance_approval([Decimal("6000.00"), Decimal("6000.00")])

    assert check.requires_approval is True
    assert check.refund_total == Decimal("12000.00")


def test_items_adding_up_to_exactly_10000_are_paid_without_approval():
    check = check_finance_approval([Decimal("4000.00"), Decimal("3500.50"), Decimal("2499.50")])

    assert check.requires_approval is False
    assert check.refund_total == Decimal("10000.00")


def test_grade_c_half_refund_can_bring_a_return_under_the_threshold():
    """A 16,000 INR item graded C refunds 8,000, so no approval is needed."""
    assert check_finance_approval([Decimal("8000.00")]).requires_approval is False


def test_reason_when_approval_is_needed():
    check = check_finance_approval([Decimal("12000")])

    assert check.reason == (
        "The refund total of 12,000.00 INR is above 10,000.00 INR, so a finance reviewer must "
        "approve it before it is paid."
    )


def test_reason_when_no_approval_is_needed():
    check = check_finance_approval([Decimal("10000")])

    assert check.reason == (
        "The refund total of 10,000.00 INR is not above 10,000.00 INR, so it is paid without "
        "finance approval."
    )


def test_a_different_threshold_from_settings_is_respected():
    assert requires_finance_approval(Decimal("6000"), threshold=Decimal("5000")) is True
    assert check_finance_approval([Decimal("6000")], threshold=Decimal("7500")).threshold == (
        Decimal("7500")
    )


def test_return_with_no_refunds_has_a_zero_total():
    assert refund_total([]) == Decimal("0.00")


def test_total_is_rounded_to_the_paisa():
    assert refund_total([Decimal("0.005"), Decimal("10000")]) == Decimal("10000.00")


def test_negative_item_refund_is_rejected():
    with pytest.raises(ValueError, match="negative"):
        refund_total([Decimal("100"), Decimal("-1")])


def test_negative_threshold_is_rejected():
    with pytest.raises(ValueError, match="negative"):
        requires_finance_approval(Decimal("1"), threshold=Decimal("-1"))
