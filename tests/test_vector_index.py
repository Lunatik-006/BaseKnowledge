def test_vector_index_prefixes_http(monkeypatch):
    from types import SimpleNamespace
    import libs.rag.vector_index as vi

    # Provide settings with URI lacking scheme
    monkeypatch.setattr(vi, "get_settings", lambda: SimpleNamespace(milvus_uri="milvus:19530"))

    captured = {}

    def fake_connect(alias, uri):
        captured["alias"] = alias
        captured["uri"] = uri

    # Avoid real network calls
    monkeypatch.setattr(vi.connections, "connect", fake_connect)
    monkeypatch.setattr(vi.utility, "has_collection", lambda name: True)

    vi.VectorIndex()

    assert captured["uri"] == "http://milvus:19530"


def test_upsert_chunks(monkeypatch):
    """Ensure upsert_chunks formats data correctly and calls Collection."""
    from types import SimpleNamespace
    import libs.rag.vector_index as vi

    # Avoid network and collection setup
    monkeypatch.setattr(vi, "connections", SimpleNamespace(connect=lambda alias, uri: None))
    monkeypatch.setattr(vi.VectorIndex, "_ensure_chunks_collection", lambda self: None)

    index = vi.VectorIndex(uri="milvus:19530")

    captured: dict[str, list] = {}

    class DummyCollection:
        def __init__(self, name):
            captured["name"] = name

        def upsert(self, data):
            captured["data"] = data

    monkeypatch.setattr(vi, "Collection", DummyCollection)

    chunks = [
        {"chunk_id": 1, "note_id": "n1", "pos": 0, "text": "t", "embedding": [0.1, 0.2]},
        {"chunk_id": 2, "note_id": "n2", "pos": 1, "text": "u", "embedding": [0.3, 0.4]},
    ]

    index.upsert_chunks(chunks)

    assert captured["name"] == index.chunks_collection
    assert captured["data"] == [
        [1, 2],
        ["n1", "n2"],
        [0, 1],
        ["t", "u"],
        [[0.1, 0.2], [0.3, 0.4]],
    ]


def test_search_returns_hits(monkeypatch):
    """search() should transform Milvus results into dictionaries."""
    from types import SimpleNamespace
    import libs.rag.vector_index as vi

    # Avoid network and collection setup
    monkeypatch.setattr(vi, "connections", SimpleNamespace(connect=lambda alias, uri: None))
    monkeypatch.setattr(vi.VectorIndex, "_ensure_chunks_collection", lambda self: None)

    index = vi.VectorIndex(uri="milvus:19530")

    class DummyCollection:
        def __init__(self, name):
            pass

        def load(self):
            captured["load"] = True  # type: ignore[name-defined]

        def search(self, data, anns_field, param, limit, output_fields):
            entity = {"chunk_id": 1, "note_id": "n1", "pos": 2, "text": "snippet"}

            class Hit:
                def __init__(self, entity):
                    self.entity = entity
                    self.score = 0.42

            return [[Hit(entity)]]

    captured: dict[str, bool] = {}
    monkeypatch.setattr(vi, "Collection", DummyCollection)

    hits = index.search([0.0, 0.1], k=1)

    assert captured.get("load") is True
    assert hits == [
        {"chunk_id": 1, "note_id": "n1", "pos": 2, "text": "snippet", "score": 0.42}
    ]
