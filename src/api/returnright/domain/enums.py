"""Enumerations shared by the domain rules, the DTOs and the database models.

Member names are the exact codes stored in PostgreSQL (db/schema_v2.sql). Values are the
lowercase strings the API and the frontend use. SQLAlchemy's Enum type stores member names, so
map columns with Enum(<EnumClass>, native_enum=False) and both sides line up.
"""

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
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"
    REJECTED = "rejected"


class ReturnReason(StrEnum):
    """Names match return_reasons.code; the service looks up reason_id by name."""

    DAMAGED = "damaged"
    WRONG_ITEM = "wrong_item"
    SIZE = "size"
    NOT_AS_DESCRIBED = "not_as_described"
    CHANGED_MIND = "changed_mind"
    QUALITY = "quality"
    OTHER = "other"


class Role(StrEnum):
    WAREHOUSE_AGENT = "warehouse_agent"
    FINANCE_REVIEWER = "finance_reviewer"
    OPS_MANAGER = "operations_manager"


class LedgerEntryType(StrEnum):
    """A refund adds a positive row; a correction adds a negative reversal row."""

    REFUND = "refund"
    REVERSAL = "reversal"
