"""A state change to record in the audit log."""

from dataclasses import dataclass

from returnright.domain.enums import Role


@dataclass(frozen=True, slots=True)
class AuditEvent:
    entity: str
    entity_id: int
    from_status: str | None
    to_status: str
    actor: str
    actor_role: Role | None
    reason: str | None = None
