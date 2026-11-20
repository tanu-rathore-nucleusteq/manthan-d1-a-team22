"""Decimal helpers for INR: round half up to two places."""

from decimal import ROUND_HALF_UP, Decimal

PAISE = Decimal("0.01")


def to_money(value: Decimal) -> Decimal:
    return value.quantize(PAISE, rounding=ROUND_HALF_UP)
