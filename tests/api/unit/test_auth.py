"""Staff login issues a JWT with the role; staff routes accept only valid, unexpired tokens."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from fastapi.testclient import TestClient

from returnright.api.deps import get_auth_service, get_inspection_service
from returnright.core.config import get_settings
from returnright.core.security import create_access_token, hash_password
from returnright.domain.enums import Role
from returnright.dtos.internal.auth import CurrentUser
from returnright.dtos.responses.returns import ReturnDetailResponse
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


def role_token(role: Role) -> str:
    user = CurrentUser(user_id=9, username=role.value, role=role)
    return create_access_token(user, get_settings(), datetime.now(UTC))


class FakeInspectionService:
    def detail(self, code: str) -> ReturnDetailResponse:
        return ReturnDetailResponse.model_validate(
            {
                "return_code": code,
                "status": "inspected",
                "refund_method": "original_payment",
                "items": [
                    {
                        "return_item_id": 1,
                        "order_item_id": 2,
                        "product_name": "Laptop 14 inch",
                        "quantity": 1,
                        "unit_price": "12000.00",
                        "reason": "damaged",
                        "photo_urls": ["/api/v1/uploads/returns/1.png"],
                        "grade": "A",
                        "decision": "accept",
                        "refund_amount": "12000.00",
                    }
                ],
                "timeline": [],
                "refund_total": "12000.00",
                "created_at": datetime.now(UTC),
                "order_number": "ORD-DEMO-08",
            }
        )


@pytest.fixture
def detail_client():
    app.dependency_overrides[get_inspection_service] = FakeInspectionService
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_finance_token_can_open_a_return_detail_with_names_grades_and_photos(detail_client):
    headers = {"Authorization": f"Bearer {role_token(Role.FINANCE_REVIEWER)}"}

    response = detail_client.get("/api/v1/warehouse/returns/RR-7K2P9QX4", headers=headers)

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["product_name"] == "Laptop 14 inch"
    assert item["grade"] == "A"
    assert item["photo_urls"] == ["/api/v1/uploads/returns/1.png"]


def test_finance_token_still_cannot_mark_a_parcel_received(detail_client):
    headers = {"Authorization": f"Bearer {role_token(Role.FINANCE_REVIEWER)}"}

    response = detail_client.post("/api/v1/warehouse/returns/RR-7K2P9QX4/receive", headers=headers)

    assert response.status_code == 403


def test_operations_manager_token_cannot_open_a_return_detail(detail_client):
    headers = {"Authorization": f"Bearer {role_token(Role.OPS_MANAGER)}"}

    response = detail_client.get("/api/v1/warehouse/returns/RR-7K2P9QX4", headers=headers)

    assert response.status_code == 403


def test_token_carries_the_role_value_the_frontend_expects():
    token = staff_token(FixedClock(datetime.now(UTC)).now())

    claims = jwt.decode(token, options={"verify_signature": False})

    assert claims["role"] == "finance_reviewer"
    assert claims["sub"] == "7"
