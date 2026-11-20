"""SQLAlchemy ORM models. Import every model here so Alembic sees it."""

from returnright.models.audit_log import AuditLog
from returnright.models.base import Base, TimestampMixin
from returnright.models.catalog import Category, Product
from returnright.models.customer import Customer, CustomerFlag
from returnright.models.ledger import LedgerEntry
from returnright.models.order import Order, OrderItem
from returnright.models.refund import FinanceApproval, Refund
from returnright.models.return_request import (
    Inspection,
    ReasonCode,
    ReturnItem,
    ReturnPhoto,
    ReturnRequest,
)
from returnright.models.user import StaffUser

__all__ = [
    "AuditLog",
    "Base",
    "Category",
    "Customer",
    "CustomerFlag",
    "FinanceApproval",
    "Inspection",
    "LedgerEntry",
    "Order",
    "OrderItem",
    "Product",
    "ReasonCode",
    "Refund",
    "ReturnItem",
    "ReturnPhoto",
    "ReturnRequest",
    "StaffUser",
    "TimestampMixin",
]
