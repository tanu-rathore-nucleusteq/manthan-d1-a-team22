"""Mock gateway POST /payments: a repeated Idempotency-Key replays the first answer and never
pays twice. Uses the in-memory store, so no database is needed.
"""

from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from mock_gateway.main import app
from mock_gateway.store import InMemoryPaymentStore, get_store

PAYMENT = {"refund_id": 1, "amount": "1499.00", "currency": "INR"}


@pytest.fixture
def store():
    store = InMemoryPaymentStore()
    app.dependency_overrides[get_store] = lambda: store
    yield store
    app.dependency_overrides.clear()


@pytest.fixture
def client(store):
    return TestClient(app)


def pay(client: TestClient, key: str = "refund-1", payment: dict = PAYMENT):
    return client.post("/payments", json=payment, headers={"Idempotency-Key": key})


def test_first_payment_succeeds_and_is_not_a_replay(client, store):
    response = pay(client)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["amount"] == "1499.00"
    assert body["replayed"] is False
    assert body["transaction_id"].startswith("txn_")
    assert store.payment_count == 1


def test_same_key_twice_pays_once_and_replays_the_first_answer(client, store):
    first = pay(client).json()
    second = pay(client).json()

    assert second["transaction_id"] == first["transaction_id"]
    assert second["replayed"] is True
    assert store.payment_count == 1


def test_different_keys_pay_separately(client, store):
    first = pay(client, "refund-1").json()
    second = pay(client, "refund-2", {**PAYMENT, "refund_id": 2}).json()

    assert first["transaction_id"] != second["transaction_id"]
    assert store.payment_count == 2


def test_ten_simultaneous_requests_with_one_key_pay_once(client, store):
    with ThreadPoolExecutor(max_workers=10) as pool:
        replies = list(pool.map(lambda _: pay(client).json(), range(10)))

    assert len({reply["transaction_id"] for reply in replies}) == 1
    assert [reply["replayed"] for reply in replies].count(False) == 1
    assert store.payment_count == 1


@pytest.mark.parametrize("change", [{"amount": "1500.00"}, {"refund_id": 99}])
def test_same_key_for_a_different_payment_is_409(client, change):
    pay(client)

    response = pay(client, payment={**PAYMENT, **change})

    assert response.status_code == 409
    assert "already used for a different payment" in response.json()["detail"]


def test_missing_idempotency_key_is_rejected(client, store):
    response = client.post("/payments", json=PAYMENT)

    assert response.status_code == 422
    assert store.payment_count == 0


@pytest.mark.parametrize("key", ["short", "k" * 65])
def test_key_shorter_than_8_or_longer_than_64_is_rejected(client, key):
    assert pay(client, key).status_code == 422


@pytest.mark.parametrize("amount", ["0", "-5.00"])
def test_amount_must_be_positive(client, amount):
    assert pay(client, payment={**PAYMENT, "amount": amount}).status_code == 422


def test_health_is_ok(client):
    assert client.get("/health").json() == {"status": "ok"}
