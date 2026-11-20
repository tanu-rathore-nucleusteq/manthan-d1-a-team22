"""Inserts audit rows and reads a return's status history (the customer timeline)."""

from sqlalchemy import select
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
