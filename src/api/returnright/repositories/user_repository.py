"""Queries for staff users."""

from sqlalchemy import func, select
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
