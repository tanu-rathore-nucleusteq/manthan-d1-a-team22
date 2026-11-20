"""Refunds, pending approvals and ledger entries to response DTOs."""

from decimal import Decimal

from returnright.dtos.responses.finance import (
    LedgerEntryResponse,
    PendingApprovalResponse,
    RefundResponse,
)
from returnright.mappers.return_mapper import return_refund_total
from returnright.models.ledger import LedgerEntry
from returnright.models.refund import APPROVED, Refund
from returnright.models.return_request import ReturnRequest


def to_refund_response(refund: Refund, return_request: ReturnRequest) -> RefundResponse:
    approval = return_request.approval
    approved_by = (
        approval.reviewer.username
        if approval is not None and approval.decision == APPROVED
        else None
    )
    return RefundResponse(
        refund_id=refund.refund_id,
        return_code=return_request.return_code,
        return_item_id=refund.return_item_id,
        amount=refund.amount,
        method=refund.method,
        status=refund.status,
        gateway_transaction_id=refund.gateway_reference,
        approved_by=approved_by,
        created_at=refund.created_at,
    )


def to_pending_approval(return_request: ReturnRequest) -> PendingApprovalResponse:
    refunds = [item.refund for item in return_request.items if item.refund is not None]
    return PendingApprovalResponse(
        return_code=return_request.return_code,
        customer_flagged=return_request.customer.is_flagged,
        refund_total=return_refund_total(return_request) or Decimal("0.00"),
        refunds=[to_refund_response(refund, return_request) for refund in refunds],
    )


def to_ledger_response(entry: LedgerEntry) -> LedgerEntryResponse:
    return LedgerEntryResponse(
        entry_id=entry.entry_id,
        refund_id=entry.refund_id,
        entry_type=entry.entry_type,
        method=entry.method,
        amount=entry.amount,
        gateway_transaction_id=entry.gateway_reference,
        created_at=entry.created_at,
    )
