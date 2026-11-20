"""Inserts audit rows and reads them back: a return's status history (the customer timeline),
everything recorded for one return, and the filtered audit log for the operations manager.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from returnright.models.audit_log import STATUS_CHANGE, AuditLog


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entry: AuditLog) -> None:
        self._session.add(entry)

    def status_history(self, return_id: int) -> list[AuditLog]:
        statement = (
            select(AuditLog)
            .where(AuditLog.return_id == return_id, AuditLog.action == STATUS_CHANGE)
            .order_by(AuditLog.created_at, AuditLog.audit_id)
        )
        return list(self._session.scalars(statement))

    def for_return(self, return_id: int) -> list[AuditLog]:
        """Every row linked to the return (status changes, refunds, decisions), oldest first."""
        statement = (
            select(AuditLog)
            .where(AuditLog.return_id == return_id)
            .order_by(AuditLog.created_at, AuditLog.audit_id)
        )
        return list(self._session.scalars(statement))

    def page(
        self, entity_type: str | None, entity_id: int | None, offset: int, limit: int
    ) -> tuple[list[AuditLog], int]:
        """Newest first."""
        conditions = []
        if entity_type is not None:
            conditions.append(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            conditions.append(AuditLog.entity_id == entity_id)
        total = self._session.scalar(select(func.count()).select_from(AuditLog).where(*conditions))
        statement = (
            select(AuditLog)
            .where(*conditions)
            .order_by(AuditLog.created_at.desc(), AuditLog.audit_id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self._session.scalars(statement)), total or 0
