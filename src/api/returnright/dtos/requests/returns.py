"""Customer return payloads. Each item carries its own reason; photos are uploaded per item
afterwards as multipart form data.
"""

from pydantic import Field

from returnright.domain.enums import RefundMethod, ReturnReason
from returnright.dtos.base import EMAIL_PATTERN, ORDER_NUMBER_PATTERN, RequestDTO


class ReturnItemRequest(RequestDTO):
    order_item_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1, le=10)
    reason: ReturnReason
    reason_details: str | None = Field(default=None, max_length=500)


class CreateReturnRequest(RequestDTO):
    order_number: str = Field(pattern=ORDER_NUMBER_PATTERN)
    email: str = Field(max_length=254, pattern=EMAIL_PATTERN)
    items: list[ReturnItemRequest] = Field(min_length=1, max_length=20)
    refund_method: RefundMethod


class CustomerProofRequest(RequestDTO):
    """Sent with customer actions on an existing return, such as marking it shipped."""

    email: str = Field(max_length=254, pattern=EMAIL_PATTERN)
