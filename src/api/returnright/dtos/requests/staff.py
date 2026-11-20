"""The operations manager adds staff accounts and switches them on or off."""

from pydantic import Field, field_validator

from returnright.domain.enums import Role
from returnright.dtos.base import EMAIL_PATTERN, RequestDTO


class CreateStaffRequest(RequestDTO):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    role: Role
    password: str = Field(
        min_length=10, max_length=72, description="Temporary password the new user signs in with"
    )

    @field_validator("email")
    @classmethod
    def lower_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def letters_and_digits(cls, value: str) -> str:
        if not any(char.isalpha() for char in value) or not any(char.isdigit() for char in value):
            raise ValueError("Use at least one letter and one number")
        return value


class UpdateStaffRequest(RequestDTO):
    is_active: bool = Field(description="False stops the account from signing in")
