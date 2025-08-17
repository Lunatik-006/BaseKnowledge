"""Pydantic models representing core domain entities."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class User(BaseModel):
    """Application user identified via Telegram."""

    id: str = Field(..., description="Internal user identifier")
    telegram_id: int = Field(..., description="Telegram user id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Note(BaseModel):
    """Metadata about a note stored on disk and indexed for search."""

    id: str
    title: str
    tags: List[str] = Field(default_factory=list)
    topic_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    file_path: str
    source_url: Optional[str] = None
    author: Optional[str] = None
    dt: Optional[datetime] = None
    channel: Optional[str] = None


class Chunk(BaseModel):
    """Small piece of a note used for vector search."""

    id: str
    note_id: str
    pos: int
    text: str
    anchor: Optional[str] = None


class SearchResult(BaseModel):
    """Single search result item returned from RAG pipeline."""

    id: str
    title: str
    url: str
    snippet: str


__all__ = ["User", "Note", "Chunk", "SearchResult"]
