"""Database engine and session factories."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from astrology_mcp.config import Settings


def create_database_engine(settings: Settings) -> Engine:
    _ensure_sqlite_parent_dir(settings)
    engine = create_engine(
        settings.database_url,
        echo=settings.sqlite_echo,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False},
    )
    _configure_sqlite_pragmas(engine, settings)
    return engine


def _ensure_sqlite_parent_dir(settings: Settings) -> None:
    if settings.database_url.startswith("sqlite:///:memory:"):
        return
    db_path = Path(settings.sqlite_db_path)
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)


def _configure_sqlite_pragmas(engine: Engine, settings: Settings) -> None:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragmas(dbapi_connection: Any, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(f"PRAGMA busy_timeout={settings.sqlite_busy_timeout_ms}")
            if settings.sqlite_enable_foreign_keys:
                cursor.execute("PRAGMA foreign_keys=ON")
            if settings.sqlite_enable_wal and not settings.database_url.startswith("sqlite:///:memory:"):
                cursor.execute("PRAGMA journal_mode=WAL")
        finally:
            cursor.close()


def initialize_sqlite_database(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("SELECT 1"))


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
