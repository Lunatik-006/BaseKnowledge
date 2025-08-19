from pathlib import Path
from unittest.mock import MagicMock

from libs.usecases import IngestText, Search
from libs.storage import NotesStorage, Note
from libs.db import MetadataRepository


def test_ingest_text_pipeline(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    storage = NotesStorage(vault)

    llm = MagicMock()
    llm.generate_structured_notes.return_value = [
        {"title": "My Note", "tags": ["x"], "meta": {}}
    ]
    llm.render_note_markdown.return_value = (
        "---\n"
        "title: My Note\n"
        "tags:\n  - x\n"
        "---\n\n"
        "Body text"
    )

    embedder = MagicMock()
    embedder.embed_texts.return_value = [[0.0, 0.1, 0.2]]

    index = MagicMock()
    repo = MetadataRepository()

    ingest = IngestText(llm, storage, embedder, index, repo)
    ingest("raw text")

    llm.generate_structured_notes.assert_called_once_with("raw text")
    llm.render_note_markdown.assert_called_once()
    embedder.embed_texts.assert_called_once_with(["Body text"])
    index.upsert_chunks.assert_called_once()
    note_path = vault / "10_Notes" / "my-note.md"
    assert note_path.exists()
    content = note_path.read_text()
    assert content.count("---") == 2
    assert content.endswith("Body text\n")


def test_search_returns_answer(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    storage = NotesStorage(vault)
    storage.save_note(Note(slug="n1", title="Note 1", tags=[], meta={}, body="body"))

    llm = MagicMock()
    llm.answer_from_context.return_value = "answer"

    embedder = MagicMock()
    embedder.embed_texts.return_value = [[0.0, 0.1, 0.2]]

    index = MagicMock()
    index.search.return_value = [
        {"chunk_id": 1, "note_id": "n1", "pos": 0, "text": "body"}
    ]

    searcher = Search(llm, embedder, index, storage)
    result = searcher("query")

    embedder.embed_texts.assert_called_once_with(["query"])
    index.search.assert_called_once()
    llm.answer_from_context.assert_called_once()
    assert result == "answer"
