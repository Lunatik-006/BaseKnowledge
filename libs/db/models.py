"""SQLAlchemy ORM models for core entities."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Optional, List

from sqlalchemy import DateTime, ForeignKey, Integer, String, BigInteger
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    language: Mapped[str] = mapped_column(String(8), default='en')
    # UI/UX preferences
    target_level: Mapped[str] = mapped_column(String(16), default='beginner')
    tone: Mapped[str] = mapped_column(String(16), default='pragmatic')
    # UI state persistence (best-effort)
    last_menu_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_screen: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    current_project: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    ui_state_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    topic_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    dt: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    channel: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="note", cascade="all, delete-orphan"
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"))
    pos: Mapped[int] = mapped_column(Integer)
    anchor: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    note: Mapped[Note] = relationship(back_populates="chunks")


__all__ = ["User", "Note", "Chunk"]
