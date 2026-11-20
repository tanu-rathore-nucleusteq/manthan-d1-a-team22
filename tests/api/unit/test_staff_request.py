"""Rules for a new staff account, checked before anything reaches the database."""

import pytest
from pydantic import ValidationError

from returnright.domain.enums import Role
from returnright.dtos.requests.staff import CreateStaffRequest

VALID = {
    "full_name": "Meera Iyer",
    "email": "Meera.Iyer@Example.com",
    "role": "finance_reviewer",
    "password": "temporary-pass-42",
}


def test_valid_request_lowers_the_email_and_reads_the_role():
    request = CreateStaffRequest(**VALID)

    assert request.email == "meera.iyer@example.com"
    assert request.role is Role.FINANCE_REVIEWER


@pytest.mark.parametrize(
    "password",
    ["short-1", "no-digits-at-all", "1234567890123", "a1" * 37],
    ids=["under 10 characters", "no number", "no letter", "over 72 bytes for bcrypt"],
)
def test_weak_or_too_long_password_is_refused(password):
    with pytest.raises(ValidationError):
        CreateStaffRequest(**VALID | {"password": password})


@pytest.mark.parametrize(
    ("field", "value"),
    [("role", "admin"), ("email", "not-an-email"), ("full_name", "M")],
    ids=["unknown role", "bad email", "name too short"],
)
def test_invalid_field_is_refused(field, value):
    with pytest.raises(ValidationError):
        CreateStaffRequest(**VALID | {field: value})


def test_extra_fields_such_as_is_admin_are_refused():
    with pytest.raises(ValidationError):
        CreateStaffRequest(**VALID | {"is_admin": True})
