"""Writes audit_log rows in the caller's transaction: every return status change, finance
decisions, refund payments and customer flags.
"""

from typing import Any

from returnright.domain.enums import ReturnStatus
from returnright.domain.state_machine import FINAL_STATUSES, ensure_can_move
from returnright.dtos.internal.audit import Actor
from returnright.models.audit_log import STATUS_CHANGE, AuditLog
from returnright.models.return_request import ReturnRequest
from returnright.repositories.audit_repository import AuditRepository
from returnright.utils.clock import Clock

RETURN = "RETURN"


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
