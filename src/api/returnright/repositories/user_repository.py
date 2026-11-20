"""Queries for staff users: sign-in lookup and the operations manager's team list."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from returnright.models.user import StaffUser


class StaffUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_active_by_login(self, login: str) -> StaffUser | None:
        """Staff sign in with their full email or the part before the @ (warehouse1)."""
        login = login.strip().lower()
        email = func.lower(StaffUser.email)
        matches = email == login if "@" in login else func.split_part(email, "@", 1) == login
        statement = (
            select(StaffUser).where(matches, StaffUser.is_active).order_by(StaffUser.staff_id)
        )
        return self._session.scalars(statement).first()

    def login_taken(self, email: str) -> bool:
        """True when the email, or the part before its @, is already someone's login."""
        email = email.lower()
        stored = func.lower(StaffUser.email)
        statement = select(StaffUser.staff_id).where(
            or_(stored == email, func.split_part(stored, "@", 1) == email.split("@", 1)[0])
        )
        return self._session.scalars(statement).first() is not None

    def get(self, staff_id: int, *, for_update: bool = False) -> StaffUser | None:
        return self._session.get(StaffUser, staff_id, with_for_update=for_update)

    def all(self) -> list[StaffUser]:
        statement = select(StaffUser).order_by(StaffUser.role, StaffUser.full_name)
        return list(self._session.scalars(statement))

    def add(self, user: StaffUser) -> None:
        self._session.add(user)
