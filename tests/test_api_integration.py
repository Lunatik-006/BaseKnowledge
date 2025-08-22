def test_ingest_text_endpoint(client):
    response = client.post("/ingest/text", json={"text": "hello"})
    assert response.status_code == 201
    data = response.json()
    assert "notes" in data
    note = data["notes"][0]
    assert note["content"] == "hello"


def test_search_endpoint(client):
    response = client.post("/search", json={"query": "hello"})
    assert response.status_code == 200
    data = response.json()
    assert "answer_md" in data
    assert "items" in data


def test_webhook_secret_validation(client, monkeypatch):
    from types import SimpleNamespace
    from apps.api import main

    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(telegram_webhook_secret="expected", telegram_bot_token=""),
    )

    response = client.post("/telegram/webhook/bad", json={})
    assert response.status_code == 403


def test_webhook_splits_long_message(client, monkeypatch):
    from types import SimpleNamespace
    from apps.api import main

    calls: list[str] = []

    async def fake_uc(text: str) -> None:
        calls.append(text)

    monkeypatch.setattr(main, "get_settings", lambda: SimpleNamespace(telegram_webhook_secret="s", telegram_bot_token=""))
    monkeypatch.setattr(main, "MAX_NOTE_LEN", 10)
    main.app.dependency_overrides[main.ingest_text_uc] = lambda: fake_uc

    payload = {"message": {"forward_date": 1, "text": "a" * 25}}
    response = client.post("/telegram/webhook/s", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert calls == ["a" * 10, "a" * 10, "a" * 5]


def test_get_note_metadata(client):
    from apps.api import main
    from libs.storage import Note

    storage = main.app.dependency_overrides[main.get_storage]()
    note = Note(
        slug="meta",
        title="Meta",
        tags=["t"],
        body="b",
        author="Alice",
        source_url="http://example.com",
        dt="2024-01-01",
        channel="telegram",
    )
    storage.save_note(note)

    response = client.get("/notes/meta")
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"]["author"] == "Alice"
    assert data["metadata"]["source_url"] == "http://example.com"
    assert data["metadata"]["dt"] == "2024-01-01"
    assert data["metadata"]["channel"] == "telegram"
