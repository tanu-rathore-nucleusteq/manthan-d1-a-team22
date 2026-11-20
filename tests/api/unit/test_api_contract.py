"""The planned API surface (docs/api-plan.md) exists, validates input and guards roles."""

import pytest
from fastapi.testclient import TestClient

from returnright.api.deps import (
    get_current_user,
    get_order_service,
    get_refund_service,
    get_return_service,
)
from returnright.api.v1.endpoints import health
from returnright.core.exceptions import OrderNotFoundError, RefundNotFoundError
from returnright.db.session import get_db
from returnright.domain.enums import Role
from returnright.dtos.internal.auth import CurrentUser
from returnright.main import app
from returnright.services.order_service import OrderService
from returnright.utils.clock import SystemClock

client = TestClient(app)

PLANNED_ROUTES = {
    ("GET", "/api/v1/health"),
    ("GET", "/api/v1/health/ready"),
    ("POST", "/api/v1/auth/login"),
    ("GET", "/api/v1/auth/me"),
    ("POST", "/api/v1/orders/lookup"),
    ("POST", "/api/v1/returns"),
    ("POST", "/api/v1/returns/{return_code}/photo"),
    ("GET", "/api/v1/returns/{return_code}"),
    ("GET", "/api/v1/returns/{return_code}/timeline"),
    ("GET", "/api/v1/returns/{return_code}/label"),
    ("POST", "/api/v1/returns/{return_code}/ship"),
    ("GET", "/api/v1/warehouse/returns"),
    ("GET", "/api/v1/warehouse/returns/{return_code}"),
    ("POST", "/api/v1/warehouse/returns/{return_code}/receive"),
    ("POST", "/api/v1/warehouse/returns/{return_code}/inspection"),
    ("GET", "/api/v1/finance/approvals"),
    ("POST", "/api/v1/finance/approvals/{return_code}/decision"),
    ("GET", "/api/v1/finance/refunds"),
    ("GET", "/api/v1/finance/refunds/{refund_id}"),
    ("POST", "/api/v1/finance/refunds/{refund_id}/pay"),
    ("GET", "/api/v1/finance/ledger"),
    ("GET", "/api/v1/dashboard"),
    ("GET", "/api/v1/dashboard/return-rates"),
    ("GET", "/api/v1/dashboard/top-reasons"),
    ("GET", "/api/v1/dashboard/flagged-customers"),
    ("GET", "/api/v1/audit"),
    ("GET", "/api/v1/audit/returns/{return_code}"),
    ("GET", "/api/v1/staff"),
    ("POST", "/api/v1/staff"),
    ("PATCH", "/api/v1/staff/{staff_id}"),
}


def test_every_planned_route_is_in_the_openapi_schema():
    published = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
    }
    assert published == PLANNED_ROUTES
    assert len(published) == 30


def test_order_lookup_is_implemented():
    class NoOrders:
        def find_by_number_and_email(self, *_args):
            return None

    app.dependency_overrides[get_order_service] = lambda: OrderService(NoOrders(), SystemClock())
    try:
        response = client.post(
            "/api/v1/orders/lookup", json={"order_number": "ORD-1001", "email": "asha@example.com"}
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 404


def test_order_lookup_with_bad_email_is_rejected():
    response = client.post(
        "/api/v1/orders/lookup", json={"order_number": "ORD-1001", "email": "not-an-email"}
    )
    assert response.status_code == 422


VALID_RETURN = {
    "order_number": "ORD-1001",
    "email": "asha@example.com",
    "items": [{"order_item_id": 1, "reason": "damaged", "reason_details": "Seam torn"}],
    "refund_method": "store_credit",
}


class NoOrderReturns:
    def create(self, _payload):
        raise OrderNotFoundError()


def test_create_return_with_a_reason_per_item_reaches_the_service():
    app.dependency_overrides[get_return_service] = NoOrderReturns
    try:
        response = client.post("/api/v1/returns", json=VALID_RETURN)
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 404
    assert response.json()["code"] == "order_not_found"


def test_create_return_with_unknown_field_is_rejected():
    response = client.post("/api/v1/returns", json={**VALID_RETURN, "discount": 100})
    assert response.status_code == 422


def test_create_return_with_an_item_without_a_reason_is_rejected():
    payload = {**VALID_RETURN, "items": [{"order_item_id": 1}]}
    assert client.post("/api/v1/returns", json=payload).status_code == 422


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/warehouse/returns",
        "/api/v1/finance/approvals",
        "/api/v1/dashboard",
        "/api/v1/audit",
        "/api/v1/staff",
    ],
)
def test_staff_routes_without_a_token_return_401(path):
    assert client.get(path).status_code == 401


@pytest.fixture
def as_finance_reviewer():
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=1, username="finance1", role=Role.FINANCE_REVIEWER
    )
    yield
    app.dependency_overrides.clear()


def test_pay_refund_without_idempotency_key_is_rejected(as_finance_reviewer):
    response = client.post("/api/v1/finance/refunds/1/pay")
    assert response.status_code == 422


class NoRefunds:
    def pay_and_describe(self, *_args):
        raise RefundNotFoundError()


def test_pay_refund_with_idempotency_key_reaches_the_service(as_finance_reviewer):
    app.dependency_overrides[get_refund_service] = NoRefunds
    response = client.post(
        "/api/v1/finance/refunds/1/pay", headers={"Idempotency-Key": "refund-1-attempt"}
    )
    assert response.status_code == 404
    assert response.json()["code"] == "refund_not_found"


def test_wrong_role_is_forbidden(as_finance_reviewer):
    assert client.get("/api/v1/dashboard").status_code == 403


def test_liveness_returns_ok():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_is_503_when_database_is_down(monkeypatch):
    class DeadSession:
        def execute(self, *_args, **_kwargs):
            from sqlalchemy.exc import OperationalError

            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    monkeypatch.setattr(health, "check_gateway", lambda *_: "ok")
    app.dependency_overrides[get_db] = lambda: DeadSession()
    try:
        response = client.get("/api/v1/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"status": "down", "database": "down", "gateway": "ok"}


def test_readiness_is_degraded_when_gateway_is_down(monkeypatch):
    class LiveSession:
        def execute(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(health, "check_gateway", lambda *_: "down")
    app.dependency_overrides[get_db] = lambda: LiveSession()
    try:
        response = client.get("/api/v1/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
