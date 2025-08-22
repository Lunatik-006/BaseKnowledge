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
sys.modules.setdefault("telegram", SimpleNamespace(Bot=object, Update=object))
sys.modules.setdefault("replicate", SimpleNamespace(run=lambda *args, **kwargs: None))

from apps.api.main import app, get_storage, ingest_text_uc, search_uc
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

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

