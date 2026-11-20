"""Refund amount per item by grade (grade C pays 50%) and whether a refund total needs finance
approval (above 10,000 INR).

BR 1.2 rules implemented here:
- Grade refund: an accepted item refunds 100% for grades A and B and 50% for grade C; a rejected
  item refunds 0, whatever its grade. This matches chk_grade_percent on inspections.
- Finance check: applies to the return's refund total (the sum of its item refunds), strictly
  above the threshold, so exactly 10,000.00 INR is paid without review. The service passes
  Settings.finance_approval_threshold_inr; the default here is the same value.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from types import MappingProxyType

from returnright.domain.enums import Grade, ItemDecision

FINANCE_APPROVAL_THRESHOLD_INR = Decimal("10000.00")
"""BR 1.2: a return whose refund total is above this needs a finance reviewer's approval."""

GRADE_C_REFUND_PERCENT = 50
"""BR 1.2: an accepted grade C item refunds half of what the customer paid for it."""

REFUND_PERCENT_BY_GRADE = MappingProxyType({Grade.A: 100, Grade.B: 100, Grade.C: 50})
"""Refund percent for an accepted item, by condition grade."""

_PAISE = Decimal("0.01")


def refund_percent(grade: Grade, decision: ItemDecision) -> int:
    """100 for an accepted grade A or B item, 50 for an accepted grade C item, 0 when rejected."""
    if decision is ItemDecision.REJECT:
        return 0
    return REFUND_PERCENT_BY_GRADE[grade]


def item_refund_amount(
    unit_price: Decimal, quantity: int, grade: Grade, decision: ItemDecision
) -> Decimal:
    """What one returned item line refunds, in INR to the paisa.

    unit_price is the price paid at purchase (order_items.unit_price). Half paise round up, so a
    grade C item bought for 799.99 refunds 400.00.
    """
    if unit_price < 0:
        raise ValueError("unit_price cannot be negative")
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    paid = unit_price * quantity
    refund = paid * refund_percent(grade, decision) / 100
    return refund.quantize(_PAISE, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class FinanceCheck:
    requires_approval: bool
    refund_total: Decimal
    threshold: Decimal
    reason: str


def refund_total(item_refunds: Iterable[Decimal]) -> Decimal:
    """The return's refund total in INR, to the paisa. Every item refund must be zero or more."""
    amounts = list(item_refunds)
    if any(amount < 0 for amount in amounts):
        raise ValueError("item refunds cannot be negative")
    return sum(amounts, Decimal("0")).quantize(_PAISE)


def requires_finance_approval(
    total: Decimal, threshold: Decimal = FINANCE_APPROVAL_THRESHOLD_INR
) -> bool:
    """True when the refund total is strictly above the threshold."""
    if threshold < 0:
        raise ValueError("threshold cannot be negative")
    return total > threshold


def check_finance_approval(
    item_refunds: Iterable[Decimal], threshold: Decimal = FINANCE_APPROVAL_THRESHOLD_INR
) -> FinanceCheck:
    """Apply the finance check to one return and explain the outcome in plain English."""
    total = refund_total(item_refunds)
    required = requires_finance_approval(total, threshold)
    if required:
        reason = (
            f"The refund total of {_inr(total)} is above {_inr(threshold)}, so a finance "
            "reviewer must approve it before it is paid."
        )
    else:
        reason = (
            f"The refund total of {_inr(total)} is not above {_inr(threshold)}, so it is paid "
            "without finance approval."
        )
    return FinanceCheck(
        requires_approval=required, refund_total=total, threshold=threshold, reason=reason
    )


def _inr(amount: Decimal) -> str:
    return f"{amount.quantize(_PAISE):,} INR"  # 12,000.00 INR
