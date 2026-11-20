"""Return requests (status, refund method, return code, awaiting finance, version) and return
items (reason and note, eligibility answer, grade, decision, refund amount), with photos stored
per item and one warehouse inspection per item.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from returnright.domain.enums import Grade, ItemDecision, RefundMethod, ReturnStatus
from returnright.models.base import Base, code_enum
from returnright.models.customer import Customer
from returnright.models.order import Order, OrderItem

if TYPE_CHECKING:
    from returnright.models.refund import FinanceApproval, Refund


class ReasonCode(Base):
    """The fixed list of return reasons; code equals a ReturnReason member name."""

    __tablename__ = "return_reasons"

    reason_id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    label: Mapped[str] = mapped_column(String(100))


class ReturnRequest(Base):
    __tablename__ = "returns"

    return_id: Mapped[int] = mapped_column(primary_key=True)
    # The customer-facing code is also the QR value, so both columns hold the same string.
    return_code: Mapped[str] = mapped_column("return_number", String(20), unique=True)
    label_code: Mapped[str | None] = mapped_column(String(40), unique=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.customer_id"))
    status: Mapped[ReturnStatus] = mapped_column(code_enum(ReturnStatus))
    refund_method: Mapped[RefundMethod] = mapped_column(code_enum(RefundMethod))
    awaiting_finance: Mapped[bool] = mapped_column(default=False)
    version: Mapped[int] = mapped_column()
    requested_at: Mapped[datetime]
    closed_at: Mapped[datetime | None]

    order: Mapped[Order] = relationship(lazy="raise")
    customer: Mapped[Customer] = relationship(lazy="raise")
    items: Mapped[list["ReturnItem"]] = relationship(
        back_populates="return_request", lazy="raise", order_by="ReturnItem.return_item_id"
    )
    approval: Mapped["FinanceApproval | None"] = relationship(lazy="raise", viewonly=True)

    # Optimistic lock: every UPDATE checks and bumps the version, so two agents can't both win.
    __mapper_args__ = {"version_id_col": version}


class ReturnItem(Base):
    __tablename__ = "return_items"

    return_item_id: Mapped[int] = mapped_column(primary_key=True)
    return_id: Mapped[int] = mapped_column(ForeignKey("returns.return_id", ondelete="CASCADE"))
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.order_item_id"))
    quantity: Mapped[int] = mapped_column(SmallInteger)
    reason_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("return_reasons.reason_id"))
    reason_note: Mapped[str | None] = mapped_column(String(500))
    days_since_delivery: Mapped[int] = mapped_column(SmallInteger)
    is_eligible: Mapped[bool]
    eligibility_reason: Mapped[str] = mapped_column(String(300))

    return_request: Mapped[ReturnRequest] = relationship(back_populates="items", lazy="raise")
    order_item: Mapped[OrderItem] = relationship(lazy="raise")
    reason: Mapped[ReasonCode] = relationship(lazy="raise")
    photos: Mapped[list["ReturnPhoto"]] = relationship(
        lazy="raise", order_by="ReturnPhoto.photo_id"
    )
    inspection: Mapped["Inspection | None"] = relationship(lazy="raise")
    refund: Mapped["Refund | None"] = relationship(back_populates="return_item", lazy="raise")


class ReturnPhoto(Base):
    __tablename__ = "return_photos"

    photo_id: Mapped[int] = mapped_column(primary_key=True)
    return_item_id: Mapped[int] = mapped_column(
        ForeignKey("return_items.return_item_id", ondelete="CASCADE")
    )
    file_path: Mapped[str] = mapped_column(String(300))
    uploaded_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Inspection(Base):
    """The warehouse check of one item; the database allows exactly one per item."""

    __tablename__ = "inspections"

    inspection_id: Mapped[int] = mapped_column(primary_key=True)
    return_item_id: Mapped[int] = mapped_column(
        ForeignKey("return_items.return_item_id"), unique=True
    )
    agent_id: Mapped[int] = mapped_column(ForeignKey("staff_users.staff_id"))
    grade: Mapped[Grade] = mapped_column(code_enum(Grade, length=1))
    decision: Mapped[ItemDecision] = mapped_column(code_enum(ItemDecision, length=10))
    refund_percent: Mapped[int] = mapped_column(SmallInteger)
    notes: Mapped[str | None] = mapped_column(String(500))
    inspected_at: Mapped[datetime] = mapped_column(server_default=func.now())
