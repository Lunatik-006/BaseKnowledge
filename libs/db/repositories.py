"""Repository classes for CRUD operations on ORM models."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models


class UserRepo:
    """CRUD operations for :class:`models.User`."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, telegram_id: int, language: str | None = None) -> models.User:
        user = models.User(telegram_id=telegram_id, language=language or 'en')
        self.session.add(user)
        await self.session.flush()
        return user

    async def get(self, user_id: str) -> Optional[models.User]:
        return await self.session.get(models.User, user_id)

    async def get_by_telegram(self, telegram_id: int) -> Optional[models.User]:
        stmt = select(models.User).where(models.User.telegram_id == telegram_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list(self) -> List[models.User]:
        res = await self.session.execute(select(models.User))
        return list(res.scalars().all())

    async def delete(self, user: models.User) -> None:
        await self.session.delete(user)

    async def set_language(self, user: models.User, lang: str) -> models.User:
        user.language = lang
        await self.session.flush()
        return user


class NoteRepo:
    """CRUD operations for :class:`models.Note`."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        title: str,
        file_path: str,
        tags: Optional[List[str]] = None,
        id: Optional[str] = None,
        **kwargs,
    ) -> models.Note:
        note = models.Note(
            id=id,
            title=title,
            file_path=file_path,
            tags=tags or [],
            **kwargs,
        )
        self.session.add(note)
        await self.session.flush()
        return note

    async def get(self, note_id: str) -> Optional[models.Note]:
        return await self.session.get(models.Note, note_id)

    async def list(self) -> List[models.Note]:
        res = await self.session.execute(select(models.Note))
        return list(res.scalars().all())

    async def delete(self, note: models.Note) -> None:
        await self.session.delete(note)

    async def update(self, note: models.Note, **fields) -> models.Note:
        for key, value in fields.items():
            setattr(note, key, value)
        await self.session.flush()
        return note


class ChunkRepo:
    """CRUD operations for :class:`models.Chunk`."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, note_id: str, pos: int, anchor: Optional[str] = None
    ) -> models.Chunk:
        chunk = models.Chunk(note_id=note_id, pos=pos, anchor=anchor)
        self.session.add(chunk)
        await self.session.flush()
        return chunk

    async def get(self, chunk_id: str) -> Optional[models.Chunk]:
        return await self.session.get(models.Chunk, chunk_id)

    async def list_by_note(self, note_id: str) -> List[models.Chunk]:
        res = await self.session.execute(
            select(models.Chunk).where(models.Chunk.note_id == note_id)
        )
        return list(res.scalars().all())

    async def delete(self, chunk: models.Chunk) -> None:
        await self.session.delete(chunk)

    async def update(self, chunk: models.Chunk, **fields) -> models.Chunk:
        for key, value in fields.items():
            setattr(chunk, key, value)
        await self.session.flush()
        return chunk


__all__ = ["UserRepo", "NoteRepo", "ChunkRepo"]

