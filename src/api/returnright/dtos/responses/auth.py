"""Token issued after a successful login."""

from typing import Literal

from pydantic import Field

from returnright.domain.enums import Role
from returnright.dtos.base import ResponseDTO


class TokenResponse(ResponseDTO):
    access_token: str
    token_type: Literal["bearer"] = Field(default="bearer")
    expires_in: int
    role: Role


class UserResponse(ResponseDTO):
    """The signed-in internal user."""

    user_id: int
    username: str
    role: Role
