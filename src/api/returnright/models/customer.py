"""Customers (synthetic), their review flag and the history of frequent-returner flags."""

from datetime import datetime

from sqlalchemy import ForeignKey, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from returnright.models.base import Base


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255))  # unique on lower(email) in the schema
    phone: Mapped[str | None] = mapped_column(String(20))
    is_flagged: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class CustomerFlag(Base):
    """One frequent-returner flag. Only one flag per customer can be open (resolved_at is null)."""

    __tablename__ = "customer_flags"

    flag_id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.customer_id"))
    trigger_return_id: Mapped[int] = mapped_column(ForeignKey("returns.return_id"))
    returns_in_30d: Mapped[int] = mapped_column(SmallInteger)
    flagged_at: Mapped[datetime] = mapped_column(server_default=func.now())
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("staff_users.staff_id"))
    review_note: Mapped[str | None] = mapped_column(String(500))
    resolved_at: Mapped[datetime | None]
