"""The authenticated caller, resolved from the JWT by api/deps.py."""

from dataclasses import dataclass

from returnright.domain.enums import Role


@dataclass(frozen=True, slots=True)
class CurrentUser:
    user_id: int
    username: str
    role: Role
