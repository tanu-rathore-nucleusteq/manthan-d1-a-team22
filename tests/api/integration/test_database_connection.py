"""Connects to the real PostgreSQL in DATABASE_URL; skipped when it is not running."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from returnright.db.session import get_engine, ping_database, session_scope


@pytest.fixture(scope="module")
def database():
    try:
        with get_engine().connect():
            pass
    except OperationalError:
        pytest.skip("PostgreSQL is not reachable at DATABASE_URL")
    yield


def test_session_reaches_postgres_18(database):
    with session_scope() as session:
        assert ping_database(session)
        version = session.execute(text("SHOW server_version")).scalar_one()
    assert version.startswith("18")


def test_connection_uses_utc_and_statement_timeout(database):
    with session_scope() as session:
        assert session.execute(text("SHOW timezone")).scalar_one() == "UTC"
        assert session.execute(text("SHOW statement_timeout")).scalar_one() != "0"
