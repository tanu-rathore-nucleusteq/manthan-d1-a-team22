"""Readiness probe of the payment gateway (api/v1/endpoints/health.py::check_gateway)."""

import httpx
import pytest

from returnright.api.v1.endpoints import health


@pytest.mark.parametrize(
    ("status_code", "state"),
    [(200, "ok"), (500, "degraded"), (503, "degraded")],
    ids=["healthy", "server error", "outage"],
)
def test_gateway_state_follows_its_health_answer(monkeypatch, status_code, state):
    calls = []

    def fake_get(url, timeout):
        calls.append((url, timeout))
        return httpx.Response(status_code)

    monkeypatch.setattr(health.httpx, "get", fake_get)

    assert health.check_gateway("http://gateway:8001", 1.0) == state
    assert calls == [("http://gateway:8001/health", 1.0)]


def test_unreachable_gateway_is_down():
    assert health.check_gateway("http://127.0.0.1:9", 0.5) == "down"
