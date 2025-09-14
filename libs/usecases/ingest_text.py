from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List
import json

from libs.llm import LLMClient, EmbeddingsProvider
from libs.rag import VectorIndex
from libs.storage import NotesStorage, Note as FsNote
from libs.db import models, NoteRepo, ChunkRepo
from libs.storage.notes_storage import _load_yaml



_CYRILLIC_MAP = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}

# Correct transliteration map (lowercase), used when present
_CYRILLIC_MAP_FIX = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def _slugify(text: str) -> str:
    text = text.lower()
    # Prefer the fixed map; fallback to legacy map for any missing chars
    text = "".join(_CYRILLIC_MAP_FIX.get(ch, _CYRILLIC_MAP.get(ch, ch)) for ch in text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
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


def _normalize_tag(tag: str) -> str:
    tag = tag.strip()
    if not tag:
        return ""
    return _slugify(tag)


def _dedup_preserve_order(items: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out


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
        if not insights:
            return []

        topics_info = self.llm.group_topics(insights)
        insight_map = {ins.get("id"): ins for ins in insights if ins.get("id")}
        id_to_topic: Dict[str, str] = {}
        for topic in topics_info.get("topics", []):
            for iid in topic.get("insight_ids", []):
                id_to_topic[iid] = topic.get("topic_id")

        for ins in insights:
            topic_id = id_to_topic.get(ins.get("id"))
            if topic_id:
                ins.setdefault("meta", {})["topic_id"] = topic_id

        all_titles = [i.get("title", "") for i in insights]
        for ins in insights:
            candidates = [t for t in all_titles if t != ins.get("title")]
            related = self.llm.find_autolinks(
                ins.get("title", ""),
                ins.get("summary", ""),
                candidates,
            )
            ins["see_also_candidates"] = related

        self.storage.notes_dir.mkdir(parents=True, exist_ok=True)

        notes: List[models.Note] = []
        import logging as _logging
        required_fields = {"id", "title", "summary", "bullets", "tags", "confidence"}
        for insight in insights:
            # Validate and normalize insight fields server-side
            title = str(insight.get("title", "")).strip() or "untitled"
            if len(title) > 80:
                title = title[:77] + "..."
            bullets_in = [str(b) for b in (insight.get("bullets") or []) if str(b).strip()]
            bullets_in = _dedup_preserve_order(bullets_in)
            tags_in = [str(t) for t in (insight.get("tags") or []) if str(t).strip()]
            tags_norm = _dedup_preserve_order([_normalize_tag(t) for t in tags_in if _normalize_tag(t)])

            # Write back normalized values for downstream prompt
            insight["title"] = title
            insight["bullets"] = bullets_in
            insight["tags"] = tags_norm

            # Quick validity check and controlled degradation
            missing = [k for k in required_fields if k not in insight]
            if missing:
                _logging.getLogger("ingest").warning(
                    "llm_invalid_insight_missing_fields",
                    extra={"missing": missing, "insight_preview": {"title": title}},
                )
                # Fill sane defaults to avoid pipeline failure
                insight.setdefault("summary", "")
                insight.setdefault("bullets", [])
                insight.setdefault("tags", [])
                insight.setdefault("confidence", 0.0)

            rendered = self.llm.render_note_markdown(insight)
            front: Dict[str, Any] = {}
            body = rendered
            if rendered.startswith("---"):
                parts = rendered.split("---", 2)
                if len(parts) == 3:
                    _, fm, body = parts
                    front = _load_yaml(fm)
                    body = body.lstrip("\n")

            # Prefer normalized server-side values over model/frontmatter
            title = front.get("title") or title
            tags = front.get("tags") or tags_norm

            fm_meta = {k: v for k, v in front.items() if k not in {"title", "tags"}}
            meta = {**insight.get("meta", {}), **fm_meta}

            slug = _slugify(title)

            # Generate server-side created timestamp if not provided
            from datetime import datetime, timezone
            created_str = meta.get("created")
            if not created_str:
                created_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            fs_note = FsNote(
                slug=slug,
                title=title,
                tags=tags,
                body=body,
                created=created_str,
                source_url=meta.get("source_url"),
                author=meta.get("source_author"),
                dt=meta.get("source_dt"),
                topic_id=meta.get("topic_id"),
                channel=meta.get("source_channel"),
            )
            self.storage._write_note_file(fs_note)

            meta_mapping = {
                "source_author": "author",
                "source_dt": "dt",
                "source_channel": "channel",
            }
            allowed_fields = {"source_url", "author", "dt", "topic_id", "channel"}
            db_meta: Dict[str, Any] = {}
            for key, value in meta.items():
                mapped = meta_mapping.get(key, key)
                if mapped in allowed_fields:
                    # Normalize empty strings to None
                    if isinstance(value, str) and not value.strip():
                        value = None
                    db_meta[mapped] = value

            note = await self.note_repo.create(
                id=slug,
                title=title,
                file_path=str(self.storage.notes_dir / f"{slug}.md"),
                tags=tags,
                **db_meta,
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
        topics_for_moc = []
        for topic in topics_info.get("topics", []):
            notes_list = []
            for iid in topic.get("insight_ids", []):
                ins = insight_map.get(iid)
                if ins:
                    notes_list.append(
                        {
                            "title": ins.get("title", ""),
                            "summary": ins.get("summary", ""),
                        }
                    )
            topics_for_moc.append(
                {
                    "topic_id": topic.get("topic_id"),
                    "title": topic.get("title"),
                    "desc": topic.get("desc"),
                    "notes": notes_list,
                }
            )

        topics_json = json.dumps({"topics": topics_for_moc}, ensure_ascii=False)
        moc = self.llm.generate_moc(topics_json)
        self.storage.moc_dir.mkdir(parents=True, exist_ok=True)
        self.storage.moc_file.write_text(moc.rstrip() + "\n", encoding="utf-8")

        return notes
