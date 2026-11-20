"""SqlPaymentStore against gateway.payments in the real PostgreSQL (GATEWAY_DATABASE_URL);
skipped when it is not running. Every test uses its own random keys and deletes its rows.
"""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import OperationalError

from mock_gateway.dtos import PaymentRequest
from mock_gateway.store import IdempotencyConflictError, SqlPaymentStore, get_engine, payments

REQUEST = PaymentRequest(refund_id=1, amount=Decimal("1499.00"))


@pytest.fixture
def store():
    try:
        with get_engine().connect():
            pass
    except OperationalError:
        pytest.skip("PostgreSQL is not reachable at GATEWAY_DATABASE_URL")
    return SqlPaymentStore(get_engine())


@pytest.fixture
def key():
    key = f"test-{uuid4().hex}"
    yield key
    with get_engine().begin() as connection:
        connection.execute(delete(payments).where(payments.c.idempotency_key == key))


def rows_for(key: str) -> int:
    with get_engine().connect() as connection:
        return connection.execute(
            select(func.count()).select_from(payments).where(payments.c.idempotency_key == key)
        ).scalar_one()


def test_first_payment_is_stored(store, key):
    payment, replayed = store.pay_once(key, REQUEST)

    assert replayed is False
    assert payment.amount == Decimal("1499.00")
    assert rows_for(key) == 1


def test_same_key_again_replays_the_stored_payment(store, key):
    first, _ = store.pay_once(key, REQUEST)

    second, replayed = store.pay_once(key, REQUEST)

    assert replayed is True
    assert second == first
    assert rows_for(key) == 1


def test_key_survives_a_new_store_as_after_a_gateway_restart(store, key):
    first, _ = store.pay_once(key, REQUEST)

    again, replayed = SqlPaymentStore(get_engine()).pay_once(key, REQUEST)

    assert (again.transaction_id, replayed) == (first.transaction_id, True)


def test_ten_simultaneous_calls_with_one_key_store_one_payment(store, key):
    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(lambda _: store.pay_once(key, REQUEST), range(10)))

    assert len({payment.transaction_id for payment, _ in results}) == 1
    assert [replayed for _, replayed in results].count(False) == 1
    assert rows_for(key) == 1


def test_same_key_with_a_different_amount_is_a_conflict(store, key):
    store.pay_once(key, REQUEST)

    with pytest.raises(IdempotencyConflictError):
        store.pay_once(key, PaymentRequest(refund_id=1, amount=Decimal("1500.00")))
    assert rows_for(key) == 1
