from pathlib import Path


def test_ingest_text_endpoint(client):
    response = client.post("/ingest/text", json={"text": "hello"})
    assert response.status_code == 201
    data = response.json()
    assert "notes" in data
    file_path = Path(data["notes"][0]["file_path"])
    assert file_path.exists()


def test_search_endpoint(client):
    response = client.post("/search", json={"query": "hello"})
    assert response.status_code == 200
    data = response.json()
    assert "answer_md" in data
    assert "items" in data
