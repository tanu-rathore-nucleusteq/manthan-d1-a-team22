"""Grade C pays 50%, grades A and B pay 100%, a rejected item pays nothing, and finance approval
applies to the return total strictly above 10,000 INR.
"""

from decimal import Decimal

import pytest

from returnright.domain.customer_flags import should_flag
from returnright.domain.enums import Grade, ItemDecision
from returnright.domain.refund_policy import (
    needs_finance_approval,
    refund_amount,
    refund_percent,
    refund_total,
)

THRESHOLD = Decimal("10000")


@pytest.mark.parametrize(("grade", "percent"), [(Grade.A, 100), (Grade.B, 100), (Grade.C, 50)])
def test_accepted_item_pays_by_grade(grade, percent):
    assert refund_percent(grade, ItemDecision.ACCEPT) == percent


def test_rejected_item_pays_nothing_whatever_the_grade():
    assert refund_percent(Grade.A, ItemDecision.REJECT) == 0


def test_grade_c_item_of_2000_refunds_1000():
    assert refund_amount(Decimal("2000.00"), 1, 50) == Decimal("1000.00")


def test_half_of_an_odd_paise_amount_rounds_half_up():
    assert refund_amount(Decimal("799.55"), 1, 50) == Decimal("399.78")


def test_quantity_multiplies_the_unit_price():
    assert refund_amount(Decimal("799.50"), 2, 100) == Decimal("1599.00")


def test_exactly_10000_pays_without_finance_approval():
    assert needs_finance_approval(Decimal("10000.00"), THRESHOLD) is False


def test_10000_01_waits_for_finance_approval():
    assert needs_finance_approval(Decimal("10000.01"), THRESHOLD) is True


def test_two_items_of_6000_wait_for_finance_because_the_return_total_counts():
    total = refund_total([Decimal("6000.00"), Decimal("6000.00")])

    assert total == Decimal("12000.00")
    assert needs_finance_approval(total, THRESHOLD) is True


def test_third_return_in_30_days_does_not_flag_and_the_fourth_does():
    assert should_flag(3) is False
    assert should_flag(4) is True
