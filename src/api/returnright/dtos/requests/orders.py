"""Order lookup: the order number and email together prove the customer owns the order."""

from pydantic import Field

from returnright.dtos.base import EMAIL_PATTERN, ORDER_NUMBER_PATTERN, RequestDTO


class OrderLookupRequest(RequestDTO):
    order_number: str = Field(pattern=ORDER_NUMBER_PATTERN)
    email: str = Field(max_length=254, pattern=EMAIL_PATTERN)
