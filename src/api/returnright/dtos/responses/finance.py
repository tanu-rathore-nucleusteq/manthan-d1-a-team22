"""Refunds, approvals and ledger entries."""

from datetime import datetime

from returnright.domain.enums import LedgerEntryType, RefundMethod, RefundStatus
from returnright.dtos.base import Money, ResponseDTO


class RefundResponse(ResponseDTO):
    refund_id: int
    return_code: str
    return_item_id: int
    amount: Money
    method: RefundMethod
    status: RefundStatus
    gateway_transaction_id: str | None = None
    approved_by: str | None = None
    created_at: datetime


class PendingApprovalResponse(ResponseDTO):
    return_code: str
    customer_flagged: bool
    refund_total: Money
    refunds: list[RefundResponse]


class LedgerEntryResponse(ResponseDTO):
    entry_id: int
    refund_id: int
    entry_type: LedgerEntryType
    method: RefundMethod
    amount: Money
    gateway_transaction_id: str | None = None
    created_at: datetime
