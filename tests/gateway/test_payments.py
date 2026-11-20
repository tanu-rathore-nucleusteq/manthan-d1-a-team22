"""The mock gateway pays once per idempotency key and its fault switches behave as documented."""

import time
import uuid

import pytest
from fastapi.testclient import TestClient

from mock_gateway.config import GatewaySettings
from mock_gateway.main import create_app
from mock_gateway.store import MemoryStore


def gateway(**settings) -> TestClient:
    return TestClient(create_app(GatewaySettings(**settings), MemoryStore()))


def pay(client: TestClient, key: str, amount: str = "1500.00", refund_id: int = 1):
    return client.post(
        "/payments",
        json={"refund_id": refund_id, "amount": amount},
        headers={"Idempotency-Key": key},
    )


def test_same_key_pays_once_and_replays_the_first_answer():
    client = gateway()

    first = pay(client, "refund-101")
    second = pay(client, "refund-101")

    assert first.status_code == second.status_code == 200
    assert first.json()["replayed"] is False
    assert second.json()["replayed"] is True
    assert second.json()["transaction_id"] == first.json()["transaction_id"]


def test_different_keys_are_different_payments():
    client = gateway()

    assert (
        pay(client, "refund-101").json()["transaction_id"]
        != pay(client, "refund-102", refund_id=2).json()["transaction_id"]
    )


def test_same_key_with_a_different_amount_is_refused_with_409():
    client = gateway()
    pay(client, "refund-101", amount="1500.00")

    assert pay(client, "refund-101", amount="9999.00").status_code == 409


def test_missing_idempotency_key_is_rejected_with_422():
    response = gateway().post("/payments", json={"refund_id": 1, "amount": "10.00"})

    assert response.status_code == 422


def test_outage_switch_answers_503_and_nothing_is_paid():
    client = gateway(down=True)

    assert pay(client, "refund-101").status_code == 503
    client.post("/admin/faults", json={"down": False})
    assert pay(client, "refund-101").json()["replayed"] is False


def test_error_rate_of_one_answers_502_and_a_retry_after_recovery_pays():
    client = gateway(error_rate=1.0)

    assert pay(client, "refund-101").status_code == 502
    client.post("/admin/faults", json={"error_rate": 0.0})
    retry = pay(client, "refund-101")

    assert retry.status_code == 200
    assert retry.json()["replayed"] is False


def test_latency_switch_slows_the_answer():
    client = gateway(latency_ms=150)

    started = time.perf_counter()
    pay(client, "refund-101")

    assert time.perf_counter() - started >= 0.15


def test_fault_switches_can_be_read_and_changed_at_runtime():
    client = gateway()

    changed = client.post("/admin/faults", json={"latency_ms": 200, "error_rate": 0.25})

    assert changed.json() == {"latency_ms": 200, "error_rate": 0.25, "down": False}
    assert client.get("/admin/faults").json() == changed.json()


def test_admin_token_protects_the_fault_switches_when_set():
    client = gateway(admin_token="drill-token-123")

    assert client.post("/admin/faults", json={"down": True}).status_code == 401
    allowed = client.post(
        "/admin/faults", json={"down": True}, headers={"X-Admin-Token": "drill-token-123"}
    )
    assert allowed.status_code == 200


def test_health_answers_ok():
    assert gateway().get("/health").json() == {"status": "ok"}


@pytest.fixture
def postgres_store():
    import psycopg

    from mock_gateway.store import PostgresStore

    url = "postgresql://returnright:change-me@localhost:5434/returnright"
    try:
        store = PostgresStore(url)
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL is not reachable on localhost:5434")
    key = f"test-{uuid.uuid4().hex[:12]}"
    yield store, key
    with psycopg.connect(url, autocommit=True) as connection:
        connection.execute("DELETE FROM gateway.payments WHERE idempotency_key = %s", (key,))


def test_postgres_store_pays_once_per_key(postgres_store):
    from decimal import Decimal

    store, key = postgres_store

    first, first_replayed = store.pay_once(key, 1, Decimal("250.00"), "INR")
    second, second_replayed = store.pay_once(key, 1, Decimal("250.00"), "INR")

    assert (first_replayed, second_replayed) == (False, True)
    assert second.transaction_id == first.transaction_id
