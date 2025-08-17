from __future__ import annotations

"""Database setup for SQLAlchemy with async psycopg driver."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


DATABASE_URL = os.getenv(
    "POSTGRES_URI",
    "postgresql+psycopg://postgres:postgres@localhost:5432/postgres",
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


# create async engine and session factory
engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
def get_session() -> AsyncIterator[AsyncSession]:
    """Provide a transactional scope around a series of operations."""

    async with SessionLocal() as session:  # pragma: no cover - simple wrapper
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


__all__ = ["Base", "engine", "SessionLocal", "get_session"]
