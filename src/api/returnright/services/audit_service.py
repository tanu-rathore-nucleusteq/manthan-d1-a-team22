"""Writes audit_log rows in the caller's transaction (every return status change, finance
decisions, refund payments and customer flags) and reads them back for the operations manager.
"""

from typing import Any

from sqlalchemy.orm import Session

from returnright.core.exceptions import STAFF_NOT_FOUND, ReturnNotFoundError
from returnright.domain.enums import ReturnStatus
from returnright.domain.state_machine import FINAL_STATUSES, ensure_can_move
from returnright.dtos.internal.audit import Actor
from returnright.dtos.responses.audit import AuditLogResponse
from returnright.dtos.responses.common import PageResponse
from returnright.mappers.audit_mapper import to_audit_response
from returnright.models.audit_log import STATUS_CHANGE, AuditLog
from returnright.models.return_request import ReturnRequest
from returnright.repositories.audit_repository import AuditRepository
from returnright.repositories.return_repository import ReturnRepository
from returnright.utils.clock import Clock

RETURN = "RETURN"


class AuditLogService:
    def __init__(self, session: Session) -> None:
        self._audits = AuditRepository(session)
        self._returns = ReturnRepository(session)

    def page(
        self, entity: str | None, entity_id: int | None, page: int, size: int
    ) -> PageResponse[AuditLogResponse]:
        entity_type = entity.upper() if entity else None
        rows, total = self._audits.page(entity_type, entity_id, (page - 1) * size, size)
        return PageResponse[AuditLogResponse](
            items=[to_audit_response(row) for row in rows], total=total, page=page, size=size
        )

    def for_return(self, code: str) -> list[AuditLogResponse]:
        return_request = self._returns.get_by_code(code)
        if return_request is None:
            raise ReturnNotFoundError(STAFF_NOT_FOUND)
        return [to_audit_response(row) for row in self._audits.for_return(return_request.return_id)]


class AuditTrail:
    def __init__(self, audits: AuditRepository) -> None:
        self._audits = audits

    def record(
        self,
        *,
        entity_type: str,
        entity_id: int,
        action: str,
        actor: Actor,
        return_id: int | None = None,
        old_status: str | None = None,
        new_status: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {"actor": actor.name}
        if actor.role is not None:
            payload["role"] = actor.role.value
        payload.update(details or {})
        self._audits.add(
            AuditLog(
                return_id=return_id,
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                old_status=old_status,
                new_status=new_status,
                actor_type=actor.kind,
                actor_id=actor.actor_id,
                details=payload,
            )
        )


class ReturnTransitions:
    """Moves a return through the state machine. Each move writes one audit row; the caller
    commits both together."""

    def __init__(self, audit: AuditTrail, clock: Clock) -> None:
        self._audit = audit
        self._clock = clock

    def open(self, return_request: ReturnRequest, actor: Actor) -> None:
        """Record the creation of a flushed return (status Requested)."""
        self._audit.record(
            entity_type=RETURN,
            entity_id=return_request.return_id,
            return_id=return_request.return_id,
            action=STATUS_CHANGE,
            actor=actor,
            new_status=return_request.status.name,
        )

    def move(
        self,
        return_request: ReturnRequest,
        target: ReturnStatus,
        actor: Actor,
        note: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        ensure_can_move(return_request.status, target)
        previous = return_request.status
        return_request.status = target
        if target in FINAL_STATUSES:
            return_request.closed_at = self._clock.now()
            return_request.awaiting_finance = False
        extra = dict(details or {})
        if note:
            extra["note"] = note
        self._audit.record(
            entity_type=RETURN,
            entity_id=return_request.return_id,
            return_id=return_request.return_id,
            action=STATUS_CHANGE,
            actor=actor,
            old_status=previous.name,
            new_status=target.name,
            details=extra,
        )
