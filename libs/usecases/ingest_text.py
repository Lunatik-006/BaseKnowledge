from __future__ import annotations

import re
from typing import Any, Dict, List

from libs.llm import LLMClient, EmbeddingsProvider
from libs.rag import VectorIndex
from libs.storage import NotesStorage, Note as FsNote
from libs.db import models, NoteRepo, ChunkRepo


def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def _chunk_text(text: str, size: int = 500, overlap: int = 50) -> List[str]:
    if not text:
        return []
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


class IngestText:
    """Pipeline to convert raw text into notes and index them for search."""

    def __init__(
        self,
        llm: LLMClient,
        storage: NotesStorage,
        embeddings: EmbeddingsProvider,
        index: VectorIndex,
        note_repo: NoteRepo,
        chunk_repo: ChunkRepo,
    ) -> None:
        self.llm = llm
        self.storage = storage
        self.embeddings = embeddings
        self.index = index
        self.note_repo = note_repo
        self.chunk_repo = chunk_repo

    # ------------------------------------------------------------------
    async def __call__(self, text: str) -> List[models.Note]:
        insights: List[Dict[str, Any]] = self.llm.generate_structured_notes(text)
        notes: List[models.Note] = []
        for insight in insights:
            title = insight.get("title", "untitled")
            slug = _slugify(title)
            body = self.llm.render_note_markdown(insight)
            tags = insight.get("tags", [])
            meta = insight.get("meta", {})

            fs_note = FsNote(slug=slug, title=title, tags=tags, meta=meta, body=body)
            self.storage.save_note(fs_note)

            note = await self.note_repo.create(
                id=slug,
                title=title,
                file_path=str(self.storage.notes_dir / f"{slug}.md"),
                tags=tags,
                **meta,
            )

            chunk_texts = _chunk_text(body)
            embeddings = self.embeddings.embed_texts(chunk_texts)
            chunks_for_index = []
            for pos, (ch_text, emb) in enumerate(zip(chunk_texts, embeddings)):
                chunk = await self.chunk_repo.create(note_id=note.id, pos=pos)
                chunks_for_index.append(
                    {
                        "chunk_id": chunk.id,
                        "note_id": note.id,
                        "pos": pos,
                        "text": ch_text,
                        "embedding": emb,
                    }
                )
            if chunks_for_index:
                self.index.upsert_chunks(chunks_for_index)
            notes.append(note)
        return notes
