"""Login payload for internal roles."""

from pydantic import Field

from returnright.dtos.base import RequestDTO


class LoginRequest(RequestDTO):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)
