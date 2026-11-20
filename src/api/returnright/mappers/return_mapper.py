"""Return requests, items and status history to response DTOs."""

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from returnright.core.constants import API_V1_PREFIX
from returnright.domain.enums import ReturnReason, ReturnStatus
from returnright.domain.refund_policy import refund_total
from returnright.dtos.responses.returns import (
    ReturnDetailResponse,
    ReturnItemResponse,
    ReturnSummaryResponse,
    StatusEventResponse,
)
from returnright.dtos.responses.warehouse import InspectionResultResponse
from returnright.models.audit_log import AuditLog
from returnright.models.return_request import ReturnItem, ReturnRequest

UPLOADS_PATH = f"{API_V1_PREFIX}/uploads"


def photo_url(relative_path: str) -> str:
    return f"{UPLOADS_PATH}/{relative_path}"


def to_item_response(item: ReturnItem) -> ReturnItemResponse:
    inspection = item.inspection
    if item.refund is not None:
        amount: Decimal | None = item.refund.amount
    else:
        amount = Decimal("0.00") if inspection is not None else None
    return ReturnItemResponse(
        return_item_id=item.return_item_id,
        order_item_id=item.order_item_id,
        product_name=item.order_item.product.name,
        quantity=item.quantity,
        reason=ReturnReason[item.reason.code],
        reason_details=item.reason_note,
        photo_urls=[photo_url(photo.file_path) for photo in item.photos],
        grade=inspection.grade if inspection else None,
        decision=inspection.decision if inspection else None,
        refund_amount=amount,
    )


def to_status_events(history: Sequence[AuditLog]) -> list[StatusEventResponse]:
    return [
        StatusEventResponse(
            status=ReturnStatus[row.new_status],
            at=row.created_at,
            note=(row.details or {}).get("note"),
        )
        for row in history
        if row.new_status
    ]


def return_refund_total(return_request: ReturnRequest) -> Decimal | None:
    amounts = [item.refund.amount for item in return_request.items if item.refund is not None]
    return refund_total(amounts) if amounts else None


def to_return_detail(
    return_request: ReturnRequest, history: Sequence[AuditLog]
) -> ReturnDetailResponse:
    return ReturnDetailResponse(
        return_code=return_request.return_code,
        status=return_request.status,
        refund_method=return_request.refund_method,
        items=[to_item_response(item) for item in return_request.items],
        timeline=to_status_events(history),
        refund_total=return_refund_total(return_request),
        created_at=return_request.requested_at,
    )


def to_summary(return_request: ReturnRequest, updated_at: datetime | None) -> ReturnSummaryResponse:
    return ReturnSummaryResponse(
        return_code=return_request.return_code,
        status=return_request.status,
        order_number=return_request.order.order_number,
        item_count=len(return_request.items),
        refund_total=return_refund_total(return_request),
        customer_flagged=return_request.customer.is_flagged,
        created_at=return_request.requested_at,
        updated_at=updated_at or return_request.requested_at,
    )


def to_inspection_result(return_request: ReturnRequest) -> InspectionResultResponse:
    return InspectionResultResponse(
        return_code=return_request.return_code,
        status=return_request.status,
        items=[to_item_response(item) for item in return_request.items],
        refund_total=return_refund_total(return_request) or Decimal("0.00"),
        needs_finance_approval=return_request.awaiting_finance,
    )
