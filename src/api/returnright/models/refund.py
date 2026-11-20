"""Refunds (one per return item, with its gateway idempotency key) and finance decisions (one per
return).
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from returnright.domain.enums import RefundMethod, RefundStatus
from returnright.models.base import Base, code_enum
from returnright.models.return_request import ReturnItem
from returnright.models.user import StaffUser

APPROVED = "APPROVED"
REJECTED = "REJECTED"


class Refund(Base):
    __tablename__ = "refunds"

    refund_id: Mapped[int] = mapped_column(primary_key=True)
    return_item_id: Mapped[int] = mapped_column(
        ForeignKey("return_items.return_item_id"), unique=True
    )
    amount: Mapped[Decimal]
    method: Mapped[RefundMethod] = mapped_column(code_enum(RefundMethod))
    requires_approval: Mapped[bool]
    status: Mapped[RefundStatus] = mapped_column(code_enum(RefundStatus))
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True)
    gateway_reference: Mapped[str | None] = mapped_column(String(64))
    attempt_count: Mapped[int] = mapped_column(SmallInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    paid_at: Mapped[datetime | None]

    return_item: Mapped[ReturnItem] = relationship(back_populates="refund", lazy="raise")


class FinanceApproval(Base):
    __tablename__ = "finance_approvals"

    approval_id: Mapped[int] = mapped_column(primary_key=True)
    return_id: Mapped[int] = mapped_column(ForeignKey("returns.return_id"), unique=True)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("staff_users.staff_id"))
    decision: Mapped[str] = mapped_column(String(10))  # APPROVED or REJECTED
    comment: Mapped[str | None] = mapped_column(String(500))
    decided_at: Mapped[datetime] = mapped_column(server_default=func.now())

    reviewer: Mapped[StaffUser] = relationship(lazy="raise")
