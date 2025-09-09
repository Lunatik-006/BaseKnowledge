import json
from pathlib import Path
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
    expected = {"insights": [{"title": "t"}]}
    monkeypatch.setattr(client, "_call", lambda m, msgs: json.dumps(expected))
    assert client.generate_structured_notes("text") == expected["insights"]


def test_render_note_markdown(monkeypatch):
    client = make_client()
    monkeypatch.setattr(client, "_call", lambda m, msgs: "markdown")
    result = client.render_note_markdown({"title": "t", "summary": "", "bullets": [], "tags": []})
    assert result == "markdown"


def test_group_topics(monkeypatch):
    client = make_client()
    expected = {"topics": [], "orphans": []}
    monkeypatch.setattr(client, "_call", lambda m, msgs: json.dumps(expected))
    result = client.group_topics([{"id": "i-1", "title": "t1", "summary": "s"}])
    assert result == expected


def test_generate_moc(monkeypatch):
    client = make_client()
    monkeypatch.setattr(client, "_call", lambda m, msgs: "moc")
    assert client.generate_moc("{}") == "moc"


def test_find_autolinks(monkeypatch):
    client = make_client()
    expected = {"related_titles": ["A", "B"]}
    monkeypatch.setattr(client, "_call", lambda m, msgs: json.dumps(expected))
    result = client.find_autolinks("t", "s", ["A", "B", "C"])
    assert result == expected["related_titles"]


def test_missing_prompts_file(tmp_path: Path) -> None:
    missing = tmp_path / "nope.yaml"
    with pytest.raises(LLMClientError):
        ReplicateLLMClient(settings=DummySettings(), prompts_path=missing)


def test_missing_prompt_key(monkeypatch, tmp_path: Path) -> None:
    prompts_file = tmp_path / "p.yaml"
    prompts_file.write_text("insights:\n  system: s\n  user: u\n", encoding="utf-8")
    client = ReplicateLLMClient(settings=DummySettings(), prompts_path=prompts_file)
    monkeypatch.setattr(client, "_call", lambda m, msgs: "{}")
    with pytest.raises(LLMClientError):
        client.group_topics([])
