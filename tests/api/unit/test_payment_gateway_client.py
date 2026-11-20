"""The API's HTTP gateway client (integrations/payment_gateway.py) against the real mock gateway.

The mock gateway runs in process (its FastAPI app behind a TestClient), so these tests check the
contract between the two services: idempotency keys, retries after timeouts and 5xx answers,
and no retry on a 4xx. A thin recorder wraps the client to count attempts and inject failures.
"""

from decimal import Decimal

import httpx
import pytest
from fastapi.testclient import TestClient

from mock_gateway.config import GatewaySettings
from mock_gateway.main import create_app
from mock_gateway.store import MemoryStore
from returnright.dtos.internal.payments import GatewayPaymentRequest
from returnright.integrations import payment_gateway
from returnright.integrations.payment_gateway import HttpPaymentGateway
from returnright.interfaces.payment_gateway import GatewayUnavailableError


@pytest.fixture(autouse=True)
def no_backoff(monkeypatch):
    monkeypatch.setattr(payment_gateway, "RETRY_BACKOFF_SECONDS", 0)


class Recorder:
    """Forwards to the gateway and records every attempt; hooks can fail or fix an attempt."""

    def __init__(self, gateway: TestClient, before=None, after=None) -> None:
        self.gateway = gateway
        self.keys: list[str] = []
        self._before = before
        self._after = after

    @property
    def attempts(self) -> int:
        return len(self.keys)

    def post(self, url, json, headers):
        self.keys.append(headers["Idempotency-Key"])
        if self._before:
            self._before(self)
        reply = self.gateway.post(url, json=json, headers=headers)
        if self._after:
            self._after(self)
        return reply


def gateway(**settings) -> TestClient:
    return TestClient(create_app(GatewaySettings(**settings), MemoryStore()))


def request(key: str = "refund-7", amount: str = "1500.00") -> GatewayPaymentRequest:
    return GatewayPaymentRequest(refund_id=7, amount=Decimal(amount), idempotency_key=key)


def test_client_pays_through_the_real_gateway_and_a_repeat_replays_the_payment():
    client = HttpPaymentGateway(gateway(), max_retries=2)

    first = client.pay(request())
    second = client.pay(request())

    assert first.status == "succeeded"
    assert first.replayed is False
    assert second.replayed is True
    assert second.transaction_id == first.transaction_id


def test_timeout_after_the_gateway_took_the_money_retries_with_the_same_key_and_pays_once():
    def lose_the_first_answer(recorder: Recorder) -> None:
        if recorder.attempts == 1:  # the gateway paid, but the answer never arrived
            raise httpx.ReadTimeout("timed out")

    recorder = Recorder(gateway(), after=lose_the_first_answer)

    result = HttpPaymentGateway(recorder, max_retries=2).pay(request())

    assert recorder.keys == ["refund-7", "refund-7"]
    assert result.status == "succeeded"
    assert result.replayed is True  # the retry got the first payment back, not a second one


def test_bank_error_is_retried_until_the_gateway_recovers():
    def recover_after_first_attempt(recorder: Recorder) -> None:
        if recorder.attempts == 1:
            recorder.gateway.post("/admin/faults", json={"error_rate": 0.0})

    recorder = Recorder(gateway(error_rate=1.0), after=recover_after_first_attempt)

    result = HttpPaymentGateway(recorder, max_retries=2).pay(request())

    assert recorder.attempts == 2
    assert result.status == "succeeded"
    assert result.replayed is False


def test_gateway_failing_on_every_retry_is_unavailable_after_max_retries():
    recorder = Recorder(gateway(error_rate=1.0))

    with pytest.raises(GatewayUnavailableError, match="HTTP 502"):
        HttpPaymentGateway(recorder, max_retries=2).pay(request())

    assert recorder.attempts == 3
    assert set(recorder.keys) == {"refund-7"}


def test_gateway_outage_is_unavailable():
    recorder = Recorder(gateway(down=True))

    with pytest.raises(GatewayUnavailableError, match="HTTP 503"):
        HttpPaymentGateway(recorder, max_retries=1).pay(request())

    assert recorder.attempts == 2


def test_a_4xx_answer_is_not_retried():
    shared = gateway()
    HttpPaymentGateway(shared, max_retries=2).pay(request(amount="1500.00"))
    recorder = Recorder(shared)

    with pytest.raises(GatewayUnavailableError, match="HTTP 409"):
        HttpPaymentGateway(recorder, max_retries=2).pay(request(amount="9999.00"))

    assert recorder.attempts == 1


def test_unreachable_gateway_is_unavailable():
    client = httpx.Client(base_url="http://127.0.0.1:9", timeout=0.5)

    # Refused on Linux, a connect timeout on Windows: both are connection failures.
    with pytest.raises(GatewayUnavailableError, match="Connect(Error|Timeout)"):
        HttpPaymentGateway(client, max_retries=0).pay(request())
