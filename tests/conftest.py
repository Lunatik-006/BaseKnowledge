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

from apps.api.main import (
    app,
    get_storage,
    get_index,
    get_llm_client,
    get_embeddings_provider,
    get_db,
    DummyVectorIndex,
    DummyDB,
)
from libs.storage import NotesStorage


@pytest.fixture()
def client(tmp_path):
    """FastAPI test client with dependencies overridden."""
    storage = NotesStorage(tmp_path / "vault")
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_index] = lambda: DummyVectorIndex()
    app.dependency_overrides[get_llm_client] = lambda: MagicMock()
    app.dependency_overrides[get_embeddings_provider] = lambda: MagicMock()
    app.dependency_overrides[get_db] = lambda: DummyDB()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
