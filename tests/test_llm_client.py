import json
from types import SimpleNamespace

import pytest
import requests

# Stub settings with fake token
class DummySettings(SimpleNamespace):
    replicate_api_token: str = "token"

from libs.llm.replicate_client import ReplicateLLMClient, LLMClientError


def make_client() -> ReplicateLLMClient:
    return ReplicateLLMClient(settings=DummySettings())


def test_call_success(monkeypatch):
    client = make_client()

    def fake_post(url, json, timeout):
        class Resp:
            status_code = 200
            def raise_for_status(self):
                pass
            def json(self):
                return {"choices": [{"message": {"content": "ok"}}]}
        return Resp()

    monkeypatch.setattr(client.session, "post", fake_post)
    assert client._call("model", []) == "ok"


def test_call_timeout(monkeypatch):
    client = make_client()

    def fake_post(url, json, timeout):
        raise requests.Timeout()

    monkeypatch.setattr(client.session, "post", fake_post)
    with pytest.raises(LLMClientError):
        client._call("model", [])


def test_generate_structured_notes(monkeypatch):
    client = make_client()
    expected = {"insights": []}
    monkeypatch.setattr(client, "_call", lambda m, msgs: json.dumps(expected))
    assert client.generate_structured_notes("text") == expected


def test_render_note_markdown(monkeypatch):
    client = make_client()
    monkeypatch.setattr(client, "_call", lambda m, msgs: "markdown")
    result = client.render_note_markdown({"title": "t", "summary": "", "bullets": [], "tags": []})
    assert result == "markdown"
