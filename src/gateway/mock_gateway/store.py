"""Remembers processed idempotency keys, so a retry returns the original result instead of
paying again. PostgresStore keeps them in the gateway schema; MemoryStore needs no database.
"""

import secrets
import threading
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Protocol

import psycopg
from psycopg.types.json import Jsonb

SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS gateway;
CREATE TABLE IF NOT EXISTS gateway.payments (
    payment_id        BIGSERIAL     PRIMARY KEY,
    idempotency_key   VARCHAR(64)   NOT NULL UNIQUE,
    amount            NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    currency          CHAR(3)       NOT NULL DEFAULT 'INR',
    method            VARCHAR(20)   NOT NULL,
    status            VARCHAR(10)   NOT NULL CHECK (status IN ('SUCCESS','FAILED')),
    gateway_reference VARCHAR(64)   NOT NULL UNIQUE,
    response_body     JSONB         NOT NULL,
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT now()
);
"""

INSERT_SQL = """
INSERT INTO gateway.payments
    (idempotency_key, amount, currency, method, status, gateway_reference, response_body)
VALUES (%s, %s, %s, 'REFUND', 'SUCCESS', %s, %s)
ON CONFLICT (idempotency_key) DO NOTHING
RETURNING payment_id
"""


@dataclass(frozen=True, slots=True)
class Payment:
    idempotency_key: str
    refund_id: int
    amount: Decimal
    currency: str
    transaction_id: str


class KeyReusedError(Exception):
    """The key was already used for a payment with a different refund or amount."""


class PaymentStore(Protocol):
    def pay_once(
        self, key: str, refund_id: int, amount: Decimal, currency: str
    ) -> tuple[Payment, bool]:
        """Record the payment, or return the one already recorded for this key.
        The flag is True when the answer is a replay."""
        ...


def new_transaction_id() -> str:
    return "gw_" + secrets.token_hex(8)


def check_same_payment(existing: Payment, refund_id: int, amount: Decimal) -> None:
    if existing.refund_id != refund_id or existing.amount != amount:
        raise KeyReusedError(existing.idempotency_key)


class MemoryStore:
    def __init__(self) -> None:
        self._payments: dict[str, Payment] = {}
        self._lock = threading.Lock()

    def pay_once(
        self, key: str, refund_id: int, amount: Decimal, currency: str
    ) -> tuple[Payment, bool]:
        with self._lock:
            existing = self._payments.get(key)
            if existing is not None:
                check_same_payment(existing, refund_id, amount)
                return existing, True
            payment = Payment(key, refund_id, amount, currency, new_transaction_id())
            self._payments[key] = payment
            return payment, False


class PostgresStore:
    """One row per key in gateway.payments; the unique key makes concurrent retries safe."""

    def __init__(self, database_url: str) -> None:
        self._url = database_url.replace("postgresql+psycopg://", "postgresql://")
        with self._connect() as connection:
            connection.execute(SCHEMA_SQL)

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._url, autocommit=True, connect_timeout=5)

    def pay_once(
        self, key: str, refund_id: int, amount: Decimal, currency: str
    ) -> tuple[Payment, bool]:
        payment = Payment(key, refund_id, amount, currency, new_transaction_id())
        body = {**asdict(payment), "amount": str(amount), "status": "succeeded"}
        with self._connect() as connection:
            inserted = connection.execute(
                INSERT_SQL, (key, amount, currency, payment.transaction_id, Jsonb(body))
            ).fetchone()
            if inserted is not None:
                return payment, False
            stored = connection.execute(
                "SELECT response_body FROM gateway.payments WHERE idempotency_key = %s", (key,)
            ).fetchone()

        saved = stored[0]
        existing = Payment(
            key,
            int(saved["refund_id"]),
            Decimal(saved["amount"]),
            saved["currency"],
            saved["transaction_id"],
        )
        check_same_payment(existing, refund_id, amount)
        return existing, True
