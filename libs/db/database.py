from __future__ import annotations

"""Database setup for SQLAlchemy with async psycopg driver."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import inspect, text, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.schema import CreateColumn
from sqlalchemy.engine.url import make_url

from libs.core.settings import get_settings

settings = get_settings()
DATABASE_URL = settings.postgres_uri


class Base(DeclarativeBase):
    """Base class for all ORM models."""


# create async engine and session factory
# Create async engine with resilient pool settings to survive Postgres restarts
# - pool_pre_ping: validate connections before using
# - pool_recycle: proactively recycle connections to avoid server-side timeouts
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=1800,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Provide a transactional scope around a series of operations."""

    async with SessionLocal() as session:  # pragma: no cover - simple wrapper
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create tables and add missing columns if necessary.

    Attempts to connect to the database multiple times with a delay
    between attempts. Only after a successful connection will the tables be
    created. If all attempts fail, the last exception is propagated.
    """

    # Import models to ensure Base.metadata is populated even when this module
    # is imported standalone (e.g., in db-init one-off container).
    from . import models  # noqa: F401

    def sync_init(sync_conn):  # type: ignore[override]
        Base.metadata.create_all(sync_conn)
        inspector = inspect(sync_conn)
        for table in Base.metadata.tables.values():
            existing = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name not in existing:
                    col_ddl = CreateColumn(column.copy()).compile(
                        dialect=sync_conn.dialect
                    )
                    sync_conn.execute(
                        text(f"ALTER TABLE {table.name} ADD COLUMN {col_ddl}")
                    )
        # Optional: create recommended indexes in Postgres
        try:
            if sync_conn.dialect.name == "postgresql":
                # Ensure users.telegram_id is BIGINT (Telegram IDs exceed INT range)
                try:
                    res = sync_conn.execute(
                        text(
                            """
                            SELECT data_type
                            FROM information_schema.columns
                            WHERE table_name = 'users' AND column_name = 'telegram_id'
                            """
                        )
                    )
                    current_type = res.scalar()
                    if current_type == "integer":
                        sync_conn.execute(
                            text(
                                "ALTER TABLE users ALTER COLUMN telegram_id TYPE BIGINT USING telegram_id::bigint"
                            )
                        )
                except Exception:
                    # Best-effort adjustment; ignore if not applicable
                    pass
                sync_conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_chunks_note_pos ON chunks (note_id, pos)"
                    )
                )
        except Exception:  # pragma: no cover - best effort only
            pass

    max_attempts = 5
    delay = 5
    logger = logging.getLogger(__name__)
    last_exc: SQLAlchemyError | None = None

    # Proactively ensure target database exists (Postgres only)
    try:
        url = make_url(DATABASE_URL)
    except Exception:  # pragma: no cover - defensive
        url = None

    if url is not None and url.drivername.startswith("postgresql"):
        try:
            maint_url = url.set(database="postgres")
            maint_engine = create_engine(maint_url)
            with maint_engine.connect() as conn:
                exists = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname=:db"),
                    {"db": url.database},
                ).scalar()
                if exists != 1:
                    # CREATE DATABASE must run outside a transaction block
                    conn.execution_options(isolation_level="AUTOCOMMIT").execute(
                        text(f'CREATE DATABASE "{url.database}"')
                    )
                    logging.getLogger(__name__).info(
                        "Created missing database '%s'", url.database
                    )
            maint_engine.dispose()
        except Exception:  # pragma: no cover - best effort
            pass

    for attempt in range(1, max_attempts + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(sync_init)
            logger.info("DB schema ensured (attempt %d)", attempt)
            return
        except SQLAlchemyError as exc:  # pragma: no cover - best effort
            last_exc = exc
            if attempt == max_attempts:
                break
            logger.warning(
                "DB init attempt %d failed: %s. Retrying in %ds", attempt, exc, delay
            )
            await asyncio.sleep(delay)

    logger.error("DB init failed after %d attempts", max_attempts)
    if last_exc is not None:
        raise last_exc


__all__ = ["Base", "engine", "SessionLocal", "get_session", "init_db"]
