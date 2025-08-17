from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from libs.core.models import Note, Chunk


class MetadataRepository:
    """Simple SQLite-based repository for note and chunk metadata."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.conn = sqlite3.connect(str(db_path))
        self._ensure_tables()

    # ------------------------------------------------------------------
    def _ensure_tables(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                title TEXT,
                tags TEXT,
                file_path TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                note_id TEXT,
                pos INTEGER,
                text TEXT
            )
            """
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    def add_note(self, note: Note) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO notes (id, title, tags, file_path) VALUES (?, ?, ?, ?)",
            (note.id, note.title, json.dumps(note.tags), note.file_path),
        )
        self.conn.commit()

    def add_chunks(self, chunks: Iterable[Chunk]) -> None:
        data = [(c.id, c.note_id, c.pos, c.text) for c in chunks]
        cur = self.conn.cursor()
        cur.executemany(
            "INSERT OR REPLACE INTO chunks (id, note_id, pos, text) VALUES (?, ?, ?, ?)",
            data,
        )
        self.conn.commit()
