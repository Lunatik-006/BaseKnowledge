from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from telegram import Bot, Update

# ---------------------------------------------------------------------------
# Dependencies


class DummyDB:
    """Placeholder database connection."""

    def __init__(self) -> None:
        self.telegram_users: set[int] = set()

    def save_telegram_user(self, user_id: int) -> None:
        self.telegram_users.add(user_id)


class DummyVectorIndex:
    """Fallback in case real Milvus index is unavailable."""

    def upsert_chunks(self, chunks: List[Dict[str, Any]]) -> None:  # pragma: no cover - stub
        return None

    def search(self, query_vec: List[float], k: int = 5) -> List[Dict[str, Any]]:  # pragma: no cover - stub
        return []


try:  # pragma: no cover - optional dependency
    from libs.rag.vector_index import VectorIndex as RealVectorIndex
except Exception:  # Milvus client may be missing
    RealVectorIndex = None  # type: ignore

from libs.storage.notes_storage import NotesStorage, Note
from libs.llm.replicate_client import ReplicateLLMClient
from libs.llm.embeddings_provider import EmbeddingsProvider

MAX_NOTE_LEN = 1000

def get_db() -> DummyDB:
    return DummyDB()


def get_storage() -> NotesStorage:
    vault = Path("/tmp/vault")
    return NotesStorage(vault)


def get_index() -> Any:
    if RealVectorIndex is None:
        return DummyVectorIndex()
    try:
        return RealVectorIndex()
    except Exception:  # pragma: no cover - connection failure
        return DummyVectorIndex()


def get_llm_client() -> ReplicateLLMClient:
    return ReplicateLLMClient()


def get_embeddings_provider() -> EmbeddingsProvider:
    return EmbeddingsProvider()


# ---------------------------------------------------------------------------
# Use cases (minimal stubs)


class IngestText:
    def __init__(
        self,
        storage: NotesStorage,
        index: Any,
        llm: ReplicateLLMClient,
        embeddings: EmbeddingsProvider,
        db: DummyDB,
    ) -> None:
        self.storage = storage
        self.index = index
        self.llm = llm
        self.embeddings = embeddings
        self.db = db

    def __call__(self, payload: "IngestTextRequest") -> Dict[str, Any]:
        # Minimal stub: save text as a note with generated slug
        slug = f"note-{int(datetime.utcnow().timestamp())}"
        note = Note(slug=slug, title="Auto note", tags=[], body=payload.text)
        self.storage.save_note(note)
        return {"notes": [{"id": slug, "title": note.title, "file_path": str(self.storage.notes_dir / f"{slug}.md")}]}


class Search:
    def __init__(
        self,
        index: Any,
        llm: ReplicateLLMClient,
        embeddings: EmbeddingsProvider,
        db: DummyDB,
    ) -> None:
        self.index = index
        self.llm = llm
        self.embeddings = embeddings
        self.db = db

    def __call__(self, payload: "SearchRequest") -> Dict[str, Any]:
        return {"answer_md": "", "items": []}


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

def ingest_text_uc(
    storage: NotesStorage = Depends(get_storage),
    index: Any = Depends(get_index),
    llm: ReplicateLLMClient = Depends(get_llm_client),
    emb: EmbeddingsProvider = Depends(get_embeddings_provider),
    db: DummyDB = Depends(get_db),
) -> IngestText:
    return IngestText(storage, index, llm, emb, db)


def search_uc(
    index: Any = Depends(get_index),
    llm: ReplicateLLMClient = Depends(get_llm_client),
    emb: EmbeddingsProvider = Depends(get_embeddings_provider),
    db: DummyDB = Depends(get_db),
) -> Search:
    return Search(index, llm, emb, db)


# Routes ---------------------------------------------------------------------


@app.post("/ingest/text", status_code=status.HTTP_201_CREATED)
def ingest_text(req: IngestTextRequest, uc: IngestText = Depends(ingest_text_uc)) -> JSONResponse:
    try:
        result = uc(req)
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
def search(req: SearchRequest, uc: Search = Depends(search_uc)) -> Dict[str, Any]:
    try:
        return uc(req)
    except Exception as exc:  # pragma: no cover - generic error
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@app.get("/notes/{note_id}")
def get_note(note_id: str, storage: NotesStorage = Depends(get_storage)) -> Dict[str, Any]:
    try:
        note = storage.read_note(note_id)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return asdict(note)


@app.get("/export/zip")
def export_zip(storage: NotesStorage = Depends(get_storage)) -> FileResponse:
    output = Path("/tmp/export.zip")
    storage.export_zip(output)
    if not output.exists():  # pragma: no cover - safety check
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Export failed")
    return FileResponse(output)


@app.post("/telegram/webhook/{secret}")
def telegram_webhook(
    secret: str,
    payload: Dict[str, Any],
    uc: IngestText = Depends(ingest_text_uc),
    db: DummyDB = Depends(get_db),
) -> Dict[str, str]:
    expected = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    if expected and secret != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid secret")

    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    bot = Bot(token) if token else None
    update = Update.de_json(payload, bot)
    msg = update.message

    if not msg or not msg.forward_date or not msg.text:
        return {"status": "ignored"}

    user_id = msg.from_user.id if msg.from_user else None
    if user_id is not None:
        db.save_telegram_user(user_id)

    text = msg.text
    parts = [text] if len(text) <= MAX_NOTE_LEN else [text[i : i + MAX_NOTE_LEN] for i in range(0, len(text), MAX_NOTE_LEN)]
    for part in parts:
        req = IngestTextRequest(text=part, author=str(user_id) if user_id else None, channel="telegram")
        uc(req)

    return {"status": "ok"}


__all__ = ["app"]
