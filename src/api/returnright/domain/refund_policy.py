"""Refund amount per item by grade (grade C pays 50%) and whether a refund total needs finance
approval (above 10,000 INR, applied to the return total).
"""

from collections.abc import Iterable
from decimal import Decimal

from returnright.domain.enums import Grade, ItemDecision
from returnright.utils.money import to_money

PERCENT_BY_GRADE = {Grade.A: 100, Grade.B: 100, Grade.C: 50}


def refund_percent(grade: Grade, decision: ItemDecision) -> int:
    """A rejected item pays nothing; an accepted item pays by its grade."""
    return 0 if decision == ItemDecision.REJECT else PERCENT_BY_GRADE[grade]


def refund_amount(unit_price: Decimal, quantity: int, percent: int) -> Decimal:
    """Unit price at purchase × quantity × percent, rounded half up to paise."""
    return to_money(unit_price * quantity * percent / 100)


def refund_total(amounts: Iterable[Decimal]) -> Decimal:
    return to_money(sum(amounts, Decimal("0")))


def needs_finance_approval(total: Decimal, threshold: Decimal) -> bool:
    """Strictly above the threshold: 10,000.00 pays automatically, 10,000.01 waits."""
    return total > threshold
