"""Audit log entries: one per state change."""

from datetime import datetime

from returnright.domain.enums import Role
from returnright.dtos.base import ResponseDTO


class AuditLogResponse(ResponseDTO):
    audit_id: int
    entity: str
    entity_id: int
    from_status: str | None
    to_status: str
    actor: str
    actor_role: Role | None
    reason: str | None = None
    created_at: datetime
