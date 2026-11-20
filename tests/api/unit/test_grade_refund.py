"""BR 1.2: grade C refunds 50%; grades A and B refund 100%; a rejected item refunds 0."""

from decimal import Decimal

import pytest

from returnright.domain.enums import Grade, ItemDecision
from returnright.domain.refund_policy import (
    GRADE_C_REFUND_PERCENT,
    check_finance_approval,
    item_refund_amount,
    refund_percent,
)

ACCEPT, REJECT = ItemDecision.ACCEPT, ItemDecision.REJECT


def test_grade_c_refund_is_50_percent():
    assert GRADE_C_REFUND_PERCENT == 50


@pytest.mark.parametrize(
    ("grade", "decision", "percent"),
    [
        (Grade.A, ACCEPT, 100),
        (Grade.B, ACCEPT, 100),
        (Grade.C, ACCEPT, 50),
        (Grade.A, REJECT, 0),
        (Grade.B, REJECT, 0),
        (Grade.C, REJECT, 0),
    ],
)
def test_refund_percent_matches_the_database_rule(grade, decision, percent):
    """Same table as chk_grade_percent on inspections in db/schema_v2.sql."""
    assert refund_percent(grade, decision) == percent


def test_grade_c_item_refunds_half_the_price_paid():
    assert item_refund_amount(Decimal("2000.00"), 1, Grade.C, ACCEPT) == Decimal("1000.00")


@pytest.mark.parametrize("grade", [Grade.A, Grade.B])
def test_grade_a_and_b_items_refund_the_full_price_paid(grade):
    assert item_refund_amount(Decimal("1499.00"), 1, grade, ACCEPT) == Decimal("1499.00")


@pytest.mark.parametrize("grade", list(Grade))
def test_rejected_item_refunds_nothing_whatever_its_grade(grade):
    assert item_refund_amount(Decimal("1499.00"), 1, grade, REJECT) == Decimal("0.00")


def test_quantity_multiplies_the_price_before_the_grade_percent():
    assert item_refund_amount(Decimal("799.50"), 2, Grade.C, ACCEPT) == Decimal("799.50")


def test_grade_c_half_paisa_rounds_up():
    assert item_refund_amount(Decimal("799.99"), 1, Grade.C, ACCEPT) == Decimal("400.00")


def test_grade_c_on_an_expensive_item_can_still_need_finance_approval():
    phone = item_refund_amount(Decimal("24000.00"), 1, Grade.C, ACCEPT)

    assert phone == Decimal("12000.00")
    assert check_finance_approval([phone]).requires_approval is True


def test_grade_c_can_bring_a_return_under_the_finance_threshold():
    laptop = item_refund_amount(Decimal("16000.00"), 1, Grade.C, ACCEPT)

    assert check_finance_approval([laptop]).requires_approval is False


def test_partial_accept_adds_up_only_the_accepted_items():
    refunds = [
        item_refund_amount(Decimal("1500.00"), 1, Grade.A, ACCEPT),
        item_refund_amount(Decimal("1000.00"), 1, Grade.C, ACCEPT),
        item_refund_amount(Decimal("3000.00"), 1, Grade.B, REJECT),
    ]

    assert check_finance_approval(refunds).refund_total == Decimal("2000.00")


def test_negative_price_is_rejected():
    with pytest.raises(ValueError, match="negative"):
        item_refund_amount(Decimal("-1"), 1, Grade.A, ACCEPT)


@pytest.mark.parametrize("quantity", [0, -1])
def test_quantity_must_be_positive(quantity):
    with pytest.raises(ValueError, match="positive"):
        item_refund_amount(Decimal("100"), quantity, Grade.A, ACCEPT)
