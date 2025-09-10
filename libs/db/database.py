from __future__ import annotations

"""Database setup for SQLAlchemy with async psycopg driver."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import inspect, text
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


async def init_db() -> None:
    """Create tables and add missing columns if necessary."""

    async def sync_init(sync_conn):  # type: ignore[override]
        Base.metadata.create_all(sync_conn)
        inspector = inspect(sync_conn)
        for table in Base.metadata.tables.values():
            existing = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name not in existing:
                    col_ddl = CreateColumn(column.copy()).compile(dialect=sync_conn.dialect)
                    sync_conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {col_ddl}"))

    try:
        async with engine.begin() as conn:
            await conn.run_sync(sync_init)
    except SQLAlchemyError as exc:  # pragma: no cover - best effort
        logging.getLogger(__name__).warning("DB init skipped: %s", exc)


__all__ = ["Base", "engine", "SessionLocal", "get_session", "init_db"]
