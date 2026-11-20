"""A staff account as the operations manager sees it. Never includes the password hash."""

from returnright.domain.enums import Role
from returnright.dtos.base import ResponseDTO


class StaffMemberResponse(ResponseDTO):
    user_id: int
    full_name: str
    email: str
    username: str
    role: Role
    is_active: bool
