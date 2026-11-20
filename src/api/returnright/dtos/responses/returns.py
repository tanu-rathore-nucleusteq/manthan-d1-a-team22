"""Return detail, status timeline and label."""

from datetime import datetime

from returnright.domain.enums import Grade, ItemDecision, RefundMethod, ReturnReason, ReturnStatus
from returnright.dtos.base import Money, ResponseDTO


class StatusEventResponse(ResponseDTO):
    status: ReturnStatus
    at: datetime
    note: str | None = None


class ReturnItemResponse(ResponseDTO):
    return_item_id: int
    order_item_id: int
    product_name: str
    quantity: int
    reason: ReturnReason
    reason_details: str | None = None
    photo_urls: list[str] = []
    grade: Grade | None = None
    decision: ItemDecision | None = None
    refund_amount: Money | None = None


class ReturnDetailResponse(ResponseDTO):
    return_code: str
    status: ReturnStatus
    refund_method: RefundMethod
    items: list[ReturnItemResponse]
    timeline: list[StatusEventResponse]
    refund_total: Money | None = None
    created_at: datetime


class ReturnLabelResponse(ResponseDTO):
    return_code: str
    qr_svg: str
    ship_to: str


class ReturnSummaryResponse(ResponseDTO):
    """One row in a staff work queue."""

    return_code: str
    status: ReturnStatus
    order_number: str
    item_count: int
    refund_total: Money | None = None
    customer_flagged: bool = False
    created_at: datetime
    updated_at: datetime


class PhotoUploadResponse(ResponseDTO):
    return_code: str
    return_item_id: int
    photo_url: str
    content_type: str
    size_bytes: int
