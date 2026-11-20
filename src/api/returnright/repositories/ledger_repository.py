"""Queries for ledger entries. The ledger is insert-only, so there is no update or delete."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from returnright.models.ledger import LedgerEntry


class LedgerRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entry: LedgerEntry) -> None:
        self._session.add(entry)

    def page(self, refund_id: int | None, offset: int, limit: int) -> tuple[list[LedgerEntry], int]:
        conditions = [LedgerEntry.refund_id == refund_id] if refund_id is not None else []
        total = self._session.scalar(
            select(func.count()).select_from(LedgerEntry).where(*conditions)
        )
        statement = (
            select(LedgerEntry)
            .where(*conditions)
            .order_by(LedgerEntry.entry_id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self._session.scalars(statement)), total or 0
