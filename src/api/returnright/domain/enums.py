"""Enumerations shared by the domain rules, the DTOs and the database models."""

from enum import StrEnum


class ReturnStatus(StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    IN_TRANSIT = "in_transit"
    RECEIVED = "received"
    INSPECTED = "inspected"
    REFUNDED = "refunded"
    REJECTED = "rejected"


class Grade(StrEnum):
    A = "A"
    B = "B"
    C = "C"


class ItemDecision(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"


class RefundMethod(StrEnum):
    ORIGINAL_PAYMENT = "original_payment"
    STORE_CREDIT = "store_credit"


class RefundStatus(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    PAID = "paid"
    FAILED = "failed"
    REJECTED = "rejected"


class ReturnReason(StrEnum):
    DAMAGED = "damaged"
    WRONG_ITEM = "wrong_item"
    NOT_AS_DESCRIBED = "not_as_described"
    SIZE_OR_FIT = "size_or_fit"
    NO_LONGER_NEEDED = "no_longer_needed"
    OTHER = "other"


class Role(StrEnum):
    WAREHOUSE_AGENT = "warehouse_agent"
    FINANCE_REVIEWER = "finance_reviewer"
    OPERATIONS_MANAGER = "operations_manager"


class LedgerEntryType(StrEnum):
    GATEWAY_REFUND = "gateway_refund"
    STORE_CREDIT = "store_credit"
