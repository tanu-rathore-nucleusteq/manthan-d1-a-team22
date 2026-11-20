"""Who performed an action, as recorded in the audit log: a customer, a staff user or the system."""

from dataclasses import dataclass

from returnright.domain.enums import Role
from returnright.dtos.internal.auth import CurrentUser


@dataclass(frozen=True, slots=True)
class Actor:
    kind: str  # CUSTOMER, STAFF or SYSTEM, as audit_log.actor_type expects
    actor_id: int | None
    name: str
    role: Role | None = None

    @classmethod
    def customer(cls, customer_id: int, email: str) -> "Actor":
        return cls("CUSTOMER", customer_id, email.lower())

    @classmethod
    def staff(cls, user: CurrentUser) -> "Actor":
        return cls("STAFF", user.user_id, user.username, user.role)

    @classmethod
    def system(cls) -> "Actor":
        return cls("SYSTEM", None, "system")
