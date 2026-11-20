"""Audit log entries: one per state change, refund payment, finance decision or customer flag."""

from datetime import datetime

from returnright.domain.enums import Role
from returnright.dtos.base import ResponseDTO


class AuditLogResponse(ResponseDTO):
    audit_id: int
    entity: str
    entity_id: int
    action: str
    from_status: str | None
    to_status: str | None
    actor: str
    actor_role: Role | None
    reason: str | None = None
    created_at: datetime
