"""Every error leaves the API in one shape (code, message, request_id, field errors), and every
response carries a request id. No database is needed.
"""

import pytest
from fastapi.testclient import TestClient

from returnright.api.deps import get_order_service
from returnright.main import app


@pytest.fixture
def client():
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def test_invalid_body_is_422_with_one_error_per_field(client):
    response = client.post("/api/v1/orders/lookup", json={"order_number": "ORD-1"})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert [error["field"] for error in body["errors"]] == ["email"]


def test_missing_token_is_401_in_the_same_shape(client):
    response = client.get("/api/v1/dashboard")

    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_unknown_route_is_404_in_the_same_shape(client):
    response = client.get("/api/v1/no-such-thing")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_unexpected_failure_is_500_without_internal_details(client):
    def broken_service():
        raise RuntimeError("connection string with secrets")

    app.dependency_overrides[get_order_service] = broken_service

    response = client.post(
        "/api/v1/orders/lookup",
        json={"order_number": "ORD-1", "email": "asha@example.com"},
        headers={"X-Request-ID": "req-500"},
    )

    assert response.status_code == 500
    assert response.json() == {
        "code": "internal_error",
        "message": "Something went wrong on our side. Please try again in a moment.",
        "request_id": "req-500",
    }


def test_request_id_is_generated_when_the_caller_sends_none(client):
    response = client.get("/api/v1/health")

    assert len(response.headers["X-Request-ID"]) == 32


def test_unsafe_request_id_is_replaced(client):
    response = client.get("/api/v1/health", headers={"X-Request-ID": "<script> id"})

    assert len(response.headers["X-Request-ID"]) == 32
