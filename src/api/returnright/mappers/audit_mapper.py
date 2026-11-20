"""Audit rows to AuditLogResponse. Stored codes (RETURN, IN_TRANSIT, PAYMENT_FAILED) become the
lowercase API values the rest of the API uses.
"""

from enum import Enum

from returnright.domain.enums import RefundStatus, ReturnStatus, Role
from returnright.dtos.responses.audit import AuditLogResponse
from returnright.models.audit_log import AuditLog

STATUSES_BY_ENTITY: dict[str, type[Enum]] = {"RETURN": ReturnStatus, "REFUND": RefundStatus}
ROLE_VALUES = {role.value for role in Role}


def _status(entity_type: str, code: str | None) -> str | None:
    if code is None:
        return None
    statuses = STATUSES_BY_ENTITY.get(entity_type)
    if statuses is not None and code in statuses.__members__:
        return statuses[code].value
    return code.lower()


def to_audit_response(entry: AuditLog) -> AuditLogResponse:
    details = entry.details or {}
    role = details.get("role")
    return AuditLogResponse(
        audit_id=entry.audit_id,
        entity=entry.entity_type.lower(),
        entity_id=entry.entity_id,
        action=entry.action.lower(),
        from_status=_status(entry.entity_type, entry.old_status),
        to_status=_status(entry.entity_type, entry.new_status),
        actor=details.get("actor") or entry.actor_type.lower(),
        actor_role=Role(role) if role in ROLE_VALUES else None,
        reason=details.get("note") or details.get("reason"),
        created_at=entry.created_at,
    )
