"""The operations manager's team: list staff accounts, add one with a temporary password, and
switch an account off or on. Staff never register themselves, so nobody can make themselves a
finance reviewer. Every change writes an audit row.
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from returnright.core.exceptions import (
    CannotDeactivateSelfError,
    StaffLoginTakenError,
    StaffNotFoundError,
)
from returnright.core.security import hash_password
from returnright.dtos.internal.audit import Actor
from returnright.dtos.internal.auth import CurrentUser
from returnright.dtos.requests.staff import CreateStaffRequest, UpdateStaffRequest
from returnright.dtos.responses.staff import StaffMemberResponse
from returnright.models.user import StaffUser
from returnright.repositories.audit_repository import AuditRepository
from returnright.repositories.user_repository import StaffUserRepository
from returnright.services.audit_service import AuditTrail

STAFF = "STAFF"


class StaffService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._users = StaffUserRepository(session)
        self._audit = AuditTrail(AuditRepository(session))

    def team(self) -> list[StaffMemberResponse]:
        return [_to_response(user) for user in self._users.all()]

    def create(self, payload: CreateStaffRequest, manager: CurrentUser) -> StaffMemberResponse:
        if self._users.login_taken(payload.email):
            raise StaffLoginTakenError()
        user = StaffUser(
            full_name=payload.full_name,
            email=payload.email,
            role=payload.role,
            password_hash=hash_password(payload.password),
            is_active=True,
        )
        self._users.add(user)
        try:
            self._session.flush()
        except IntegrityError as error:
            # Two managers adding the same email at once: the unique index decides.
            self._session.rollback()
            raise StaffLoginTakenError() from error
        self._audit.record(
            entity_type=STAFF,
            entity_id=user.staff_id,
            action="CREATED",
            actor=Actor.staff(manager),
            details={"email": user.email, "staff_role": user.role.value},
        )
        self._session.commit()
        return _to_response(user)

    def update(
        self, staff_id: int, payload: UpdateStaffRequest, manager: CurrentUser
    ) -> StaffMemberResponse:
        if staff_id == manager.user_id and not payload.is_active:
            raise CannotDeactivateSelfError()
        user = self._users.get(staff_id, for_update=True)
        if user is None:
            raise StaffNotFoundError()
        if user.is_active != payload.is_active:
            user.is_active = payload.is_active
            self._audit.record(
                entity_type=STAFF,
                entity_id=user.staff_id,
                action="ACTIVATED" if payload.is_active else "DEACTIVATED",
                actor=Actor.staff(manager),
                details={"email": user.email},
            )
        self._session.commit()
        return _to_response(user)


def _to_response(user: StaffUser) -> StaffMemberResponse:
    return StaffMemberResponse(
        user_id=user.staff_id,
        full_name=user.full_name,
        email=user.email,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
    )
