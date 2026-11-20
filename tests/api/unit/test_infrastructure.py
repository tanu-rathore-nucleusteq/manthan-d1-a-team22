"""Edge paths of the shared building blocks: passwords, tokens, sessions, settings, paging,
error fallback and the app lifespan. No database needed.
"""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from returnright import main
from returnright.api.deps import PageParams
from returnright.api.exception_handlers import register_exception_handlers
from returnright.core.config import Settings
from returnright.core.exceptions import DomainError
from returnright.core.security import decode_access_token, verify_password
from returnright.db import session as db_session

SETTINGS = Settings(jwt_secret="test-secret-that-is-at-least-32-bytes-long")


def token(**claims) -> str:
    payload = {"sub": "1", "role": "warehouse_agent", "exp": datetime.now(UTC) + timedelta(hours=1)}
    return jwt.encode({**payload, **claims}, SETTINGS.jwt_secret, algorithm="HS256")


def test_password_against_a_malformed_hash_is_a_mismatch_not_an_error():
    assert verify_password("change-me-demo", "not-a-bcrypt-hash") is False


@pytest.mark.parametrize(
    "claims",
    [{"role": "superuser"}, {"sub": "not-a-number"}],
    ids=["unknown role", "non-numeric subject"],
)
def test_token_with_malformed_claims_is_invalid(claims):
    with pytest.raises(jwt.InvalidTokenError, match="Malformed claims"):
        decode_access_token(token(**claims), SETTINGS)


def test_session_scope_rolls_back_and_closes_when_the_work_fails(monkeypatch):
    class FakeSession:
        committed = rolled_back = closed = False

        def commit(self):
            self.committed = True

        def rollback(self):
            self.rolled_back = True

        def close(self):
            self.closed = True

    fake = FakeSession()
    monkeypatch.setattr(db_session, "get_session_factory", lambda: lambda: fake)

    with pytest.raises(RuntimeError), db_session.session_scope():
        raise RuntimeError("seed step failed")

    assert (fake.committed, fake.rolled_back, fake.closed) == (False, True, True)


def test_dispose_engine_closes_a_created_engine_without_error():
    db_session.get_engine()  # creating the engine does not connect

    db_session.dispose_engine()


def test_app_shutdown_disposes_the_engine(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "dispose_engine", lambda: calls.append("disposed"))

    with TestClient(main.create_app()):
        assert calls == []

    assert calls == ["disposed"]


def test_cors_origins_accept_a_comma_separated_env_value():
    settings = Settings(cors_origins="http://localhost:5173, http://127.0.0.1:5173 ,")

    assert settings.cors_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_page_offset_skips_the_earlier_pages():
    assert PageParams(page=3, size=20).offset == 40


def test_a_domain_error_without_a_mapped_status_is_400_in_the_error_shape():
    class UnmappedError(DomainError):
        code = "unmapped_error"

    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    def boom():
        raise UnmappedError("Something specific went wrong.")

    response = TestClient(app).get("/boom")

    assert response.status_code == 400
    assert response.json()["code"] == "unmapped_error"
    assert response.json()["message"] == "Something specific went wrong."
