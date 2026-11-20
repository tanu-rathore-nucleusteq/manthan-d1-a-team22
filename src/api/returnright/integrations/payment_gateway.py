"""HTTP client for the mock gateway, implementing the PaymentGateway port: timeout, bounded
retries with the same idempotency key, latency recorded as a metric.

Implemented so far: timeout and bounded retries. Every attempt sends the same Idempotency-Key, so
a retry after a timeout (when the gateway may already have paid) gets the first answer replayed
instead of a second payment. The latency metric joins with the observability story.
"""

import time
from collections.abc import Callable

import httpx

from returnright.core.exceptions import (
    GatewayUnavailableError,
    IdempotencyConflictError,
    PaymentGatewayError,
)
from returnright.dtos.internal.payments import GatewayPaymentRequest, GatewayPaymentResult

IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"
RETRYABLE_STATUS_CODES = frozenset({500, 502, 503, 504})


class HttpPaymentGateway:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float,
        max_retries: int,
        client: httpx.Client | None = None,
        backoff_seconds: float = 0.2,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        self._url = f"{base_url.rstrip('/')}/payments"
        self._timeout = timeout_seconds
        self._attempts = max_retries + 1
        self._client = client or httpx.Client()
        self._backoff = backoff_seconds
        self._sleep = sleep

    def pay(self, request: GatewayPaymentRequest) -> GatewayPaymentResult:
        """Retry timeouts, connection errors and 5xx answers with the same key; never retry a
        4xx answer, because sending the same request again cannot change it."""
        body = {
            "refund_id": request.refund_id,
            "amount": str(request.amount),  # exact decimal, never float
            "currency": request.currency,
        }
        headers = {IDEMPOTENCY_KEY_HEADER: request.idempotency_key}

        for attempt in range(1, self._attempts + 1):
            started = time.perf_counter()
            try:
                reply = self._client.post(
                    self._url, json=body, headers=headers, timeout=self._timeout
                )
            except httpx.TransportError:
                reply = None
            latency_ms = (time.perf_counter() - started) * 1000

            if reply is not None and reply.status_code == httpx.codes.OK:
                data = reply.json()
                return GatewayPaymentResult(
                    transaction_id=data["transaction_id"],
                    status=data["status"],
                    replayed=data["replayed"],
                    latency_ms=latency_ms,
                )
            if reply is not None and reply.status_code == httpx.codes.CONFLICT:
                raise IdempotencyConflictError()
            if reply is not None and reply.status_code not in RETRYABLE_STATUS_CODES:
                raise PaymentGatewayError(
                    f"The payment gateway refused the request ({reply.status_code})."
                )

            if attempt < self._attempts:
                self._sleep(self._backoff * attempt)

        raise GatewayUnavailableError(self._attempts)
