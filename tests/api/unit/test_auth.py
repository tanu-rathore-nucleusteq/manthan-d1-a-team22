"""Staff login issues a JWT with the role; staff routes accept only valid, unexpired tokens."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from fastapi.testclient import TestClient

from returnright.api.deps import get_auth_service
from returnright.core.config import get_settings
from returnright.core.security import create_access_token, hash_password
from returnright.domain.enums import Role
from returnright.dtos.internal.auth import CurrentUser
from returnright.main import app
from returnright.services.auth_service import AuthService
from returnright.utils.clock import FixedClock, SystemClock

PASSWORD = "correct-horse-battery"
PASSWORD_HASH = hash_password(PASSWORD)


class FakeUsers:
    def find_active_by_login(self, login: str):
        if login.lower() not in {"finance1", "finance1@example.com"}:
            return None
        return SimpleNamespace(
            staff_id=7, username="finance1", role=Role.FINANCE_REVIEWER, password_hash=PASSWORD_HASH
        )


@pytest.fixture
def client():
    service = AuthService(FakeUsers(), get_settings(), SystemClock())
    app.dependency_overrides[get_auth_service] = lambda: service
    yield TestClient(app)
    app.dependency_overrides.clear()


def login(client: TestClient, username: str, password: str):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def test_right_password_returns_a_token_with_the_role(client):
    response = login(client, "finance1", PASSWORD)

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "finance_reviewer"
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == get_settings().jwt_expire_minutes * 60


def test_login_by_full_email_also_works(client):
    assert login(client, "finance1@example.com", PASSWORD).status_code == 200


@pytest.mark.parametrize(
    ("username", "password"), [("finance1", "wrong-password"), ("nobody", PASSWORD)]
)
def test_wrong_password_or_unknown_user_gets_the_same_401(client, username, password):
    response = login(client, username, password)

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"
    assert response.json()["message"] == "Wrong username or password."


def test_token_from_login_opens_auth_me(client):
    token = login(client, "finance1", PASSWORD).json()["access_token"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.json() == {"user_id": 7, "username": "finance1", "role": "finance_reviewer"}


def staff_token(now: datetime, secret: str | None = None) -> str:
    settings = get_settings()
    if secret is not None:
        settings = settings.model_copy(update={"jwt_secret": secret})
    user = CurrentUser(user_id=7, username="finance1", role=Role.FINANCE_REVIEWER)
    return create_access_token(user, settings, now)


def test_expired_token_is_refused_with_401(client):
    expired = staff_token(datetime.now(UTC) - timedelta(days=1))

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})

    assert response.status_code == 401


def test_token_signed_with_another_secret_is_refused_with_401(client):
    forged = staff_token(datetime.now(UTC), secret="someone-elses-secret-key")

    assert (
        client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code
        == 401
    )


def test_finance_token_cannot_open_the_warehouse_queue(client):
    token = staff_token(datetime.now(UTC))

    response = client.get("/api/v1/warehouse/returns", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_token_carries_the_role_value_the_frontend_expects():
    token = staff_token(FixedClock(datetime.now(UTC)).now())

    claims = jwt.decode(token, options={"verify_signature": False})

    assert claims["role"] == "finance_reviewer"
    assert claims["sub"] == "7"
