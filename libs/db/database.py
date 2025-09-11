from __future__ import annotations

"""Database setup for SQLAlchemy with async psycopg driver."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import inspect, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.schema import CreateColumn

from libs.core.settings import get_settings

settings = get_settings()
DATABASE_URL = settings.postgres_uri


class Base(DeclarativeBase):
    """Base class for all ORM models."""


# create async engine and session factory
engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False, future=True)
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


async def _ensure_database_exists(database_url: str) -> None:
    """Ensure target PostgreSQL database exists; create it if missing.

    Connects to the server-level "postgres" database and issues
    `CREATE DATABASE <name>` when the target database is absent.
    """

    url = make_url(database_url)
    # Only applicable for PostgreSQL backends; skip for SQLite and others
    if url.get_backend_name() != "postgresql":
        return
    target_db = url.database or "postgres"
    # Connect to the default admin DB to manage databases
    admin_url = url.set(database="postgres")

    admin_engine: AsyncEngine = create_async_engine(
        admin_url, echo=False, future=True, isolation_level="AUTOCOMMIT"
    )
    try:
        async with admin_engine.connect() as conn:
            res = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db"),
                {"db": target_db},
            )
            exists = res.scalar_one_or_none() is not None
            if not exists:
                owner = url.username or "postgres"
                # CREATE DATABASE cannot be parametrized for identifiers
                await conn.execute(
                    text(
                        f'CREATE DATABASE "{target_db}" OWNER "{owner}" '
                        "ENCODING 'UTF8' TEMPLATE template0"
                    )
                )
    finally:
        await admin_engine.dispose()


async def init_db() -> None:
    """Create tables and add missing columns if necessary.

    Attempts to connect to the database multiple times with a delay
    between attempts. Only after a successful connection will the tables be
    created. If all attempts fail, the last exception is propagated.
    """

    async def sync_init(sync_conn):  # type: ignore[override]
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

    max_attempts = 5
    delay = 5
    logger = logging.getLogger(__name__)
    last_exc: SQLAlchemyError | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            # Ensure the database itself exists before creating tables
            await _ensure_database_exists(DATABASE_URL)
            async with engine.begin() as conn:
                await conn.run_sync(sync_init)
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
