"""HttpPaymentGateway: timeouts, connection errors and 5xx answers are retried with the same
Idempotency-Key, so a refund is never paid twice. The last tests run the client against the real
mock gateway app, including a timeout after the gateway has already paid.
"""

from decimal import Decimal

import httpx
import pytest
from fastapi.testclient import TestClient

from mock_gateway.main import app as gateway_app
from mock_gateway.store import InMemoryPaymentStore, get_store
from returnright.api.exception_handlers import _status_for
from returnright.core.exceptions import (
    GatewayUnavailableError,
    IdempotencyConflictError,
    PaymentGatewayError,
)
from returnright.domain.refund_policy import refund_idempotency_key
from returnright.dtos.internal.payments import GatewayPaymentRequest
from returnright.integrations.payment_gateway import HttpPaymentGateway

REQUEST = GatewayPaymentRequest(
    refund_id=1, amount=Decimal("1499.00"), idempotency_key=refund_idempotency_key(11)
)
PAID = {"transaction_id": "txn_abc", "status": "succeeded", "amount": "1499.00", "replayed": False}


class ScriptedGateway:
    """Answers each attempt from a script: an exception class to raise, or a status code."""

    def __init__(self, *script):
        self.script = list(script)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        step = self.script.pop(0)
        if isinstance(step, type) and issubclass(step, Exception):
            raise step("simulated", request=request)
        return httpx.Response(step, json=PAID if step == 200 else {"detail": "x"})

    @property
    def keys(self) -> list[str]:
        return [request.headers["Idempotency-Key"] for request in self.requests]


def gateway_client(handler, max_retries: int = 2) -> HttpPaymentGateway:
    return HttpPaymentGateway(
        "http://gateway",
        timeout_seconds=2.0,
        max_retries=max_retries,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=lambda _seconds: None,
    )


def test_successful_payment_returns_the_gateway_result():
    script = ScriptedGateway(200)

    result = gateway_client(script).pay(REQUEST)

    assert (result.transaction_id, result.status, result.replayed) == (
        "txn_abc",
        "succeeded",
        False,
    )
    assert script.keys == ["refund-11"]


def test_amount_is_sent_as_an_exact_decimal_string():
    script = ScriptedGateway(200)

    gateway_client(script).pay(REQUEST)

    assert b'"amount":"1499.00"' in script.requests[0].content


@pytest.mark.parametrize("failure", [httpx.ReadTimeout, httpx.ConnectError, 503, 500])
def test_failure_then_success_retries_with_the_same_key(failure):
    script = ScriptedGateway(failure, 200)

    result = gateway_client(script).pay(REQUEST)

    assert result.transaction_id == "txn_abc"
    assert script.keys == ["refund-11", "refund-11"]


def test_gives_up_after_max_retries_and_says_how_many_attempts():
    script = ScriptedGateway(httpx.ReadTimeout, httpx.ReadTimeout, 503)

    with pytest.raises(GatewayUnavailableError) as error:
        gateway_client(script, max_retries=2).pay(REQUEST)

    assert error.value.attempts == 3
    assert script.keys == ["refund-11"] * 3


def test_zero_retries_means_one_attempt():
    script = ScriptedGateway(503)

    with pytest.raises(GatewayUnavailableError):
        gateway_client(script, max_retries=0).pay(REQUEST)
    assert len(script.requests) == 1


def test_conflict_is_not_retried():
    script = ScriptedGateway(409, 200)

    with pytest.raises(IdempotencyConflictError):
        gateway_client(script).pay(REQUEST)
    assert len(script.requests) == 1


def test_other_4xx_answers_are_not_retried():
    script = ScriptedGateway(422, 200)

    with pytest.raises(PaymentGatewayError, match="422"):
        gateway_client(script).pay(REQUEST)
    assert len(script.requests) == 1


def test_negative_max_retries_is_rejected():
    with pytest.raises(ValueError, match="negative"):
        HttpPaymentGateway("http://gateway", timeout_seconds=1, max_retries=-1)


def test_gateway_errors_map_to_409_and_502():
    assert _status_for(IdempotencyConflictError()) == 409
    assert _status_for(GatewayUnavailableError(3)) == 502


# --- Against the real mock gateway app -------------------------------------------------------


@pytest.fixture
def gateway():
    store = InMemoryPaymentStore()
    gateway_app.dependency_overrides[get_store] = lambda: store
    yield TestClient(gateway_app), store
    gateway_app.dependency_overrides.clear()


def forward_to(test_client: TestClient, *, lose_first_reply: bool = False):
    """Sends each request to the gateway app. With lose_first_reply, the gateway pays on the
    first attempt but its reply never arrives: the client sees a timeout."""
    attempts = []

    def handler(request: httpx.Request) -> httpx.Response:
        reply = test_client.post("/payments", content=request.content, headers=request.headers)
        attempts.append(reply.json())
        if lose_first_reply and len(attempts) == 1:
            raise httpx.ReadTimeout("reply lost", request=request)
        return httpx.Response(reply.status_code, json=reply.json())

    return handler, attempts


def test_double_click_pays_once(gateway):
    test_client, store = gateway
    handler, _ = forward_to(test_client)
    client = gateway_client(handler)

    first = client.pay(REQUEST)
    second = client.pay(REQUEST)

    assert second.transaction_id == first.transaction_id
    assert (first.replayed, second.replayed) == (False, True)
    assert store.payment_count == 1


def test_timeout_after_the_gateway_paid_is_retried_and_pays_once(gateway):
    test_client, store = gateway
    handler, attempts = forward_to(test_client, lose_first_reply=True)

    result = gateway_client(handler).pay(REQUEST)

    assert len(attempts) == 2
    assert result.replayed is True
    assert result.transaction_id == attempts[0]["transaction_id"]
    assert store.payment_count == 1
