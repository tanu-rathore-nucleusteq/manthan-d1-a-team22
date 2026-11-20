"""SQLAlchemy 2.0 engine and session factory. One session per request; services own the
transaction boundaries.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from returnright.core.config import Settings, get_settings


def build_engine(settings: Settings, *, pooled: bool = True) -> Engine:
    """PostgreSQL engine with a bounded pool, dead-connection checks and server-side timeouts.
    pooled=False opens one connection per use, for one-off tools such as Alembic.
    """
    pool_args: dict[str, object] = (
        {
            "pool_size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "pool_timeout": settings.db_pool_timeout_seconds,
            "pool_recycle": settings.db_pool_recycle_seconds,
            "pool_pre_ping": True,
        }
        if pooled
        else {"poolclass": NullPool}
    )
    return create_engine(
        settings.database_url,
        **pool_args,
        echo=settings.db_echo,
        connect_args={
            "connect_timeout": settings.db_connect_timeout_seconds,
            "application_name": "returnright-api",
            "options": f"-c statement_timeout={settings.db_statement_timeout_ms} -c timezone=UTC",
        },
    )


@lru_cache
def get_engine() -> Engine:
    """The process-wide engine, created on first use."""
    return build_engine(get_settings())


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request. Services commit; anything left open is
    rolled back when the request ends.
    """
    session = get_session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """A session with its own transaction, for scripts such as the seed: commit on success,
    roll back on error.
    """
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ping_database(session: Session) -> bool:
    """True when PostgreSQL answers a trivial query."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True


def dispose_engine() -> None:
    """Close pooled connections at shutdown."""
    if get_engine.cache_info().currsize:
        get_engine().dispose()
