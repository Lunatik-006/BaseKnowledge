from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, AsyncIterator, List

from fastapi import Depends, FastAPI, HTTPException, Header, Query, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from telegram import Bot, Update

from sqlalchemy.ext.asyncio import AsyncSession

from libs.core.settings import get_settings
from libs.storage.notes_storage import NotesStorage
from libs.llm.replicate_client import ReplicateLLMClient
from libs.llm.embeddings_provider import EmbeddingsProvider
from libs.rag import VectorIndex
from libs.usecases import IngestText, Search
from libs.db import get_session, NoteRepo, ChunkRepo, UserRepo, models

import hmac
import hashlib
import json
from urllib.parse import parse_qsl

MAX_NOTE_LEN = 1000


# ---------------------------------------------------------------------------
# Dependency factories


def get_storage() -> NotesStorage:
    settings = get_settings()
    vault_dir = Path(settings.vault_dir)
    return NotesStorage(vault_dir)


def get_index() -> VectorIndex:
    try:
        return VectorIndex()
    except RuntimeError as exc:
        real_uri = "http://milvus:19530"
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"MILVUS_URI is not configured. Реальный адрес {real_uri}",
        ) from exc


def get_llm_client() -> ReplicateLLMClient:
    return ReplicateLLMClient()


def get_embeddings_provider() -> EmbeddingsProvider:
    return EmbeddingsProvider()


async def db_session() -> AsyncIterator[AsyncSession]:
    async with get_session() as session:
        yield session


async def current_user(
    init_data: str | None = Header(None, alias="X-Telegram-Init-Data"),
    init_data_q: str | None = Query(None, alias="initData"),
    session: AsyncSession = Depends(db_session),
) -> models.User:
    """Validate Telegram initData and return associated user."""
    raw = init_data or init_data_q
    if not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Missing initData")

    data = dict(parse_qsl(raw))
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid initData")

    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    settings = get_settings()
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=settings.telegram_bot_token.encode(),
        digestmod=hashlib.sha256,
    ).digest()
    calculated = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid initData")

    user_data = json.loads(data["user"])
    telegram_id = int(user_data["id"])
    repo = UserRepo(session)
    user = await repo.get_by_telegram(telegram_id)
    if not user:
        user = await repo.create(telegram_id)
    return user


# ---------------------------------------------------------------------------
# Pydantic schemas


class IngestTextRequest(BaseModel):
    text: str
    source_url: Optional[str] = None
    author: Optional[str] = None
    dt: Optional[datetime] = None
    channel: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    k: int = Field(5, ge=1, le=50)


# ---------------------------------------------------------------------------
# FastAPI application

app = FastAPI(title="BaseKnowledge API")


# Factory dependencies for use cases -------------------------------------------------

async def ingest_text_uc(
    storage: NotesStorage = Depends(get_storage),
    index: VectorIndex = Depends(get_index),
    llm: ReplicateLLMClient = Depends(get_llm_client),
    emb: EmbeddingsProvider = Depends(get_embeddings_provider),
    session: AsyncSession = Depends(db_session),
) -> IngestText:
    note_repo = NoteRepo(session)
    chunk_repo = ChunkRepo(session)
    return IngestText(llm, storage, emb, index, note_repo, chunk_repo)


def search_uc(
    storage: NotesStorage = Depends(get_storage),
    index: VectorIndex = Depends(get_index),
    llm: ReplicateLLMClient = Depends(get_llm_client),
    emb: EmbeddingsProvider = Depends(get_embeddings_provider),
) -> Search:
    return Search(llm, emb, index, storage)


# Routes ---------------------------------------------------------------------


@app.post("/auth/telegram")
async def auth_telegram(user: models.User = Depends(current_user)) -> Dict[str, Any]:
    return {"id": user.id, "telegram_id": user.telegram_id}


@app.post("/ingest/text", status_code=status.HTTP_201_CREATED)
async def ingest_text(
    req: IngestTextRequest,
    uc: IngestText = Depends(ingest_text_uc),
    storage: NotesStorage = Depends(get_storage),
    user: models.User = Depends(current_user),
) -> JSONResponse:
    try:
        notes = await uc(req.text)
        result = {
            "notes": [
                {
                    "id": n.id,
                    "title": n.title,
                    "content": storage.read_note(n.id).body,
                }
                for n in notes
            ]
        }
        return JSONResponse(status_code=status.HTTP_201_CREATED, content=result)
    except Exception as exc:  # pragma: no cover - generic error
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@app.post("/ingest/video", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def ingest_video() -> Dict[str, str]:
    return {"detail": "Not implemented"}


@app.post("/ingest/image", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def ingest_image() -> Dict[str, str]:
    return {"detail": "Not implemented"}


@app.post("/search")
def search(
    req: SearchRequest,
    uc: Search = Depends(search_uc),
    user: models.User = Depends(current_user),
) -> Dict[str, Any]:
    try:
        answer_md, items = uc(req.query, req.k)
        # Filter out any missing fragments to return only existing notes
        filtered_items = [item for item in items if item]
        return {"answer_md": answer_md, "items": filtered_items}
    except Exception as exc:  # pragma: no cover - generic error
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@app.get("/notes")
def list_notes(
    storage: NotesStorage = Depends(get_storage),
    user: models.User = Depends(current_user),
) -> List[Dict[str, str]]:
    notes = storage.list_notes()
    return [{"id": n.slug, "title": n.title} for n in notes]


@app.get("/notes/{note_id}")
def get_note(
    note_id: str,
    storage: NotesStorage = Depends(get_storage),
    user: models.User = Depends(current_user),
) -> Dict[str, Any]:
    try:
        note = storage.read_note(note_id)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return {
        "id": note.slug,
        "title": note.title,
        "content": note.body,
        "metadata": {
            "tags": note.tags,
            "created": note.created,
            "source_url": note.source_url,
            "author": note.author,
            "dt": note.dt,
            "topic_id": note.topic_id,
            "channel": note.channel,
        },
    }


@app.get("/export/zip")
def export_zip(
    storage: NotesStorage = Depends(get_storage),
    user: models.User = Depends(current_user),
) -> FileResponse:
    output = Path("/tmp/export.zip")
    storage.export_zip(output)
    if not output.exists():  # pragma: no cover - safety check
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Export failed")
    return FileResponse(output)


@app.post("/telegram/webhook/{secret}")
async def telegram_webhook(
    secret: str,
    payload: Dict[str, Any],
    uc: IngestText = Depends(ingest_text_uc),
) -> Dict[str, str]:
    settings = get_settings()
    expected = settings.telegram_webhook_secret
    if expected and secret != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid secret")

    token = settings.telegram_bot_token
    bot = Bot(token) if token else None
    update = Update.de_json(payload, bot)
    msg = update.message

    if not msg or not msg.forward_date or not msg.text:
        return {"status": "ignored"}

    text = msg.text
    parts = [text] if len(text) <= MAX_NOTE_LEN else [text[i : i + MAX_NOTE_LEN] for i in range(0, len(text), MAX_NOTE_LEN)]
    for part in parts:
        await uc(part)

    return {"status": "ok"}


__all__ = ["app"]
