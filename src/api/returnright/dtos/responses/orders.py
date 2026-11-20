"""Order lookup result with an eligibility decision and reason for every item."""

from datetime import date

from returnright.dtos.base import Money, ResponseDTO


class ItemEligibilityResponse(ResponseDTO):
    order_item_id: int
    product_name: str
    category: str
    unit_price: Money
    quantity: int
    eligible: bool
    reason: str
    window_ends_on: date | None = None


class OrderLookupResponse(ResponseDTO):
    order_number: str
    delivered_on: date | None
    items: list[ItemEligibilityResponse]
