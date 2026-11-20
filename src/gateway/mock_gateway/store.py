"""Remembers processed idempotency keys, so a retry returns the original result instead of
paying again.

SqlPaymentStore keeps them in gateway.payments. Its INSERT ... ON CONFLICT DO NOTHING is atomic,
so two requests with the same key arriving at the same moment still create one payment. Only
successful payments are stored; a failed attempt (from the fault switches, later) is not, so a
retry with the same key can still pay.
"""

import threading
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from typing import Protocol
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Engine,
    MetaData,
    Numeric,
    String,
    Table,
    create_engine,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB, insert

from mock_gateway.config import get_gateway_settings
from mock_gateway.dtos import PaymentRequest

payments = Table(
    "payments",
    MetaData(schema="gateway"),
    Column("payment_id", BigInteger, primary_key=True),
    Column("idempotency_key", String(64), nullable=False, unique=True),
    Column("amount", Numeric(12, 2), nullable=False),
    Column("currency", String(3), nullable=False),
    Column("method", String(20), nullable=False),
    Column("status", String(10), nullable=False),
    Column("gateway_reference", String(64), nullable=False, unique=True),
    Column("response_body", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

# Store credit never reaches the gateway, so every payment here goes back to the original method.
_METHOD = "ORIGINAL_PAYMENT"


class IdempotencyConflictError(Exception):
    """The key was already used for a payment with a different refund or amount."""


@dataclass(frozen=True, slots=True)
class StoredPayment:
    transaction_id: str
    refund_id: int
    amount: Decimal
    currency: str


class PaymentStore(Protocol):
    def pay_once(self, key: str, request: PaymentRequest) -> tuple[StoredPayment, bool]:
        """Pay for this key, or replay the first payment made with it. Returns the payment and
        whether it was replayed."""
        ...


def _new_payment(request: PaymentRequest) -> StoredPayment:
    return StoredPayment(
        transaction_id=f"txn_{uuid4().hex}",
        refund_id=request.refund_id,
        amount=request.amount,
        currency=request.currency,
    )


def _check_same_request(stored: StoredPayment, request: PaymentRequest) -> None:
    if (stored.refund_id, stored.amount, stored.currency) != (
        request.refund_id,
        request.amount,
        request.currency,
    ):
        raise IdempotencyConflictError


class SqlPaymentStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def pay_once(self, key: str, request: PaymentRequest) -> tuple[StoredPayment, bool]:
        payment = _new_payment(request)
        body = {
            "transaction_id": payment.transaction_id,
            "refund_id": payment.refund_id,
            "amount": str(payment.amount),
            "currency": payment.currency,
            "status": "succeeded",
        }
        with self._engine.begin() as connection:
            created = connection.execute(
                insert(payments)
                .values(
                    idempotency_key=key,
                    amount=payment.amount,
                    currency=payment.currency,
                    method=_METHOD,
                    status="SUCCESS",
                    gateway_reference=payment.transaction_id,
                    response_body=body,
                )
                .on_conflict_do_nothing(index_elements=["idempotency_key"])
                .returning(payments.c.payment_id)
            ).first()
            if created is not None:
                return payment, False
            saved = connection.execute(
                select(payments.c.response_body).where(payments.c.idempotency_key == key)
            ).scalar_one()

        stored = StoredPayment(
            transaction_id=saved["transaction_id"],
            refund_id=saved["refund_id"],
            amount=Decimal(saved["amount"]),
            currency=saved["currency"],
        )
        _check_same_request(stored, request)
        return stored, True


class InMemoryPaymentStore:
    """Same behaviour without a database, for tests."""

    def __init__(self) -> None:
        self._payments: dict[str, StoredPayment] = {}
        self._lock = threading.Lock()

    def pay_once(self, key: str, request: PaymentRequest) -> tuple[StoredPayment, bool]:
        with self._lock:
            stored = self._payments.get(key)
            if stored is None:
                self._payments[key] = _new_payment(request)
                return self._payments[key], False
        _check_same_request(stored, request)
        return stored, True

    @property
    def payment_count(self) -> int:
        return len(self._payments)


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_gateway_settings().database_url, pool_pre_ping=True)


def get_store() -> PaymentStore:
    """FastAPI dependency; tests override it with an InMemoryPaymentStore."""
    return SqlPaymentStore(get_engine())
