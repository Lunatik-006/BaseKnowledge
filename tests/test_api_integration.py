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
