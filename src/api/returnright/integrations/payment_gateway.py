"""HTTP client for the mock payment gateway: a timeout on every call, and retries that always
reuse the same idempotency key, so a retry can never pay twice.
"""

import time
from functools import lru_cache

import httpx

from returnright.dtos.internal.payments import GatewayPaymentRequest, GatewayPaymentResult
from returnright.interfaces.payment_gateway import GatewayUnavailableError

RETRY_BACKOFF_SECONDS = 0.2


@lru_cache
def http_client(base_url: str, timeout_seconds: float) -> httpx.Client:
    """One pooled client per gateway URL for the whole process."""
    return httpx.Client(base_url=base_url, timeout=timeout_seconds)


class HttpPaymentGateway:
    def __init__(self, client: httpx.Client, max_retries: int) -> None:
        self._client = client
        self._max_retries = max_retries

    def pay(self, request: GatewayPaymentRequest) -> GatewayPaymentResult:
        last_error = "no attempt made"
        for attempt in range(self._max_retries + 1):
            if attempt:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
            started = time.perf_counter()
            try:
                reply = self._client.post(
                    "/payments",
                    json={
                        "refund_id": request.refund_id,
                        "amount": str(request.amount),
                        "currency": request.currency,
                    },
                    headers={"Idempotency-Key": request.idempotency_key},
                )
            except httpx.HTTPError as error:  # timeouts and connection errors: retry
                last_error = type(error).__name__
                continue
            if reply.status_code >= 500:  # simulated bank error or outage: retry
                last_error = f"HTTP {reply.status_code}"
                continue
            if reply.status_code != httpx.codes.OK:  # a 4xx won't change on retry
                raise GatewayUnavailableError(f"HTTP {reply.status_code}: {reply.text[:200]}")
            body = reply.json()
            return GatewayPaymentResult(
                transaction_id=body["transaction_id"],
                status=body["status"],
                replayed=body.get("replayed", False),
                latency_ms=(time.perf_counter() - started) * 1000,
            )
        raise GatewayUnavailableError(last_error)
