from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

from libs.usecases import IngestText, Search
from libs.storage import NotesStorage, Note
from libs.db import models, NoteRepo, ChunkRepo


def test_ingest_text_pipeline(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    storage = NotesStorage(vault)

    llm = MagicMock()

    llm.generate_structured_notes.return_value = [
        {
            "title": "My Note",
            "tags": ["x"],
            "meta": {
                "source_url": "http://example.com",
                "source_author": "Alice",
                "source_dt": "2024-02-02",
                "topic_id": "topic42",
                "source_channel": "telegram",
            },
        }
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
    note_repo = AsyncMock(spec=NoteRepo)
    note_repo.create.return_value = models.Note(
        id="my-note",
        title="My Note",
        tags=["x"],
        file_path=str(storage.notes_dir / "my-note.md"),
    )
    chunk_repo = AsyncMock(spec=ChunkRepo)
    chunk_repo.create.return_value = models.Chunk(
        id="1", note_id="my-note", pos=0, anchor=None
    )

    ingest = IngestText(llm, storage, embedder, index, note_repo, chunk_repo)
    import asyncio
    asyncio.run(ingest("raw text"))

    llm.generate_structured_notes.assert_called_once_with("raw text")
    llm.render_note_markdown.assert_called_once()
    embedder.embed_texts.assert_called_once_with(["Body text"])
    index.upsert_chunks.assert_called_once()
    note_path = vault / "10_Notes" / "my-note.md"
    assert note_path.exists()
    content = note_path.read_text()
    assert content.count("---") == 2
    assert content.endswith("Body text\n")
    fm = content.split("---")[1]
    assert "author: Alice" in fm
    assert "dt: 2024-02-02" in fm
    assert "source_url: http://example.com" in fm
    assert "topic_id: topic42" in fm
    assert "channel: telegram" in fm

    kwargs = note_repo.create.call_args.kwargs
    assert kwargs["author"] == "Alice"
    assert kwargs["dt"] == "2024-02-02"
    assert kwargs["source_url"] == "http://example.com"
    assert kwargs["topic_id"] == "topic42"
    assert kwargs["channel"] == "telegram"


def test_ingest_text_handles_no_insights(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    storage = NotesStorage(vault)

    llm = MagicMock()
    llm.generate_structured_notes.return_value = []

    embedder = MagicMock()
    index = MagicMock()
    note_repo = AsyncMock(spec=NoteRepo)
    chunk_repo = AsyncMock(spec=ChunkRepo)

    ingest = IngestText(llm, storage, embedder, index, note_repo, chunk_repo)
    import asyncio
    result = asyncio.run(ingest("raw text"))

    assert result == []
    llm.render_note_markdown.assert_not_called()
    embedder.embed_texts.assert_not_called()
    index.upsert_chunks.assert_not_called()
    assert not (vault / "10_Notes").exists()


def test_ingest_text_russian_title(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    storage = NotesStorage(vault)

    llm = MagicMock()
    llm.generate_structured_notes.return_value = [
        {"title": "Привет Мир", "tags": [], "meta": {}}
    ]
    llm.render_note_markdown.return_value = "Body text"

    embedder = MagicMock()
    embedder.embed_texts.return_value = [[0.0, 0.1, 0.2]]

    index = MagicMock()
    note_repo = AsyncMock(spec=NoteRepo)
    note_repo.create.return_value = models.Note(
        id="privet-mir", title="Привет Мир", tags=[], file_path=str(storage.notes_dir / "privet-mir.md")
    )
    chunk_repo = AsyncMock(spec=ChunkRepo)

    ingest = IngestText(llm, storage, embedder, index, note_repo, chunk_repo)
    import asyncio
    asyncio.run(ingest("raw text"))

    assert (vault / "10_Notes" / "privet-mir.md").exists()


def test_search_returns_answer(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    storage = NotesStorage(vault)
    storage.save_note(Note(slug="n1", title="Note 1", tags=[], body="body"))

    llm = MagicMock()
    llm.answer_from_context.return_value = "answer"

    embedder = MagicMock()
    embedder.embed_texts.return_value = [[0.0, 0.1, 0.2]]

    index = MagicMock()
    long_text = "x" * 250
    index.search.return_value = [
        {"chunk_id": 1, "note_id": "n1", "pos": 0, "text": long_text}
    ]

    searcher = Search(llm, embedder, index, storage)
    answer, fragments = searcher("query")

    embedder.embed_texts.assert_called_once_with(["query"])
    index.search.assert_called_once()
    llm.answer_from_context.assert_called_once()
    args, _ = llm.answer_from_context.call_args
    fragments_arg = args[1]
    assert fragments_arg[0]["snippet"].endswith("...")
    assert len(fragments_arg[0]["snippet"]) <= 200
    assert answer == "answer"
