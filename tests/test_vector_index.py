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
