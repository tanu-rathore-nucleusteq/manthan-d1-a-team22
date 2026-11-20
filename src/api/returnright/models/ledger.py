"""Insert-only ledger: one REFUND row per paid refund, REVERSAL rows for corrections. The database
blocks UPDATE and DELETE with a trigger.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from returnright.domain.enums import LedgerEntryType, RefundMethod
from returnright.models.base import Base, code_enum


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    entry_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    refund_id: Mapped[int] = mapped_column(ForeignKey("refunds.refund_id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.customer_id"))
    entry_type: Mapped[LedgerEntryType] = mapped_column(code_enum(LedgerEntryType, length=10))
    amount: Mapped[Decimal]
    method: Mapped[RefundMethod] = mapped_column(code_enum(RefundMethod))
    gateway_reference: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
