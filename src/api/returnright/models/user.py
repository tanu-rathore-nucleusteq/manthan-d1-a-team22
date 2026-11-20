"""Internal staff who sign in: warehouse agents, finance reviewers and operations managers."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from returnright.domain.enums import Role
from returnright.models.base import Base, code_enum


class StaffUser(Base):
    __tablename__ = "staff_users"

    staff_id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    role: Mapped[Role] = mapped_column(code_enum(Role))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)

    @property
    def username(self) -> str:
        """Staff sign in with the part of their email before the @, such as warehouse1."""
        return self.email.split("@", 1)[0]
