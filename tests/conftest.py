import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Provide dummy external modules


class _DummyBot:
    def __init__(self, token: str | None = None) -> None:
        self.token = token


class _DummyUpdate:
    @staticmethod
    def de_json(data, bot):  # type: ignore[override]
        msg = data.get("message")
        if msg:
            return SimpleNamespace(message=SimpleNamespace(**msg))
        return SimpleNamespace(message=None)


sys.modules.setdefault("telegram", SimpleNamespace(Bot=_DummyBot, Update=_DummyUpdate))
sys.modules.setdefault("replicate", SimpleNamespace(run=lambda *args, **kwargs: None))

# Avoid slow network calls to Milvus during tests
try:
    import pymilvus

    pymilvus.connections.connect = lambda *args, **kwargs: None
    pymilvus.utility.has_collection = lambda name: True

    class _DummyCollection:
        def __init__(self, *args, **kwargs) -> None:  # pragma: no cover - simple stub
            pass

        def load(self) -> None:  # pragma: no cover - simple stub
            pass

        def upsert(self, data):  # pragma: no cover - simple stub
            pass

        def search(self, *args, **kwargs):  # pragma: no cover - simple stub
            return []

    pymilvus.Collection = _DummyCollection
except Exception:  # pragma: no cover - if pymilvus missing
    pass

from apps.api.main import app, get_storage, ingest_text_uc, search_uc, current_user
from libs.storage import NotesStorage, Note


class DummyIngestText:
    def __init__(self, storage: NotesStorage) -> None:
        self.storage = storage

    async def __call__(self, text: str):
        note = Note(slug="n1", title="n1", tags=[], body=text)
        self.storage.save_note(note)
        return [SimpleNamespace(id=note.slug, title=note.title)]


@pytest.fixture()
def client(tmp_path):
    """FastAPI test client with dependencies overridden."""

    storage = NotesStorage(tmp_path / "vault")
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[ingest_text_uc] = lambda: DummyIngestText(storage)
    app.dependency_overrides[search_uc] = lambda: MagicMock(return_value=("answer", []))
    app.dependency_overrides[current_user] = lambda: SimpleNamespace(id=1, telegram_id=1)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

