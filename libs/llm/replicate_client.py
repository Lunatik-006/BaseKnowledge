from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import requests
import yaml

from libs.core.settings import Settings, get_settings
from .llm_client import LLMClient


class LLMClientError(Exception):
    """Raised when interaction with LLM fails."""


class ReplicateLLMClient(LLMClient):
    """LLM client powered by Replicate API."""

    def __init__(
        self,
        settings: Settings | None = None,
        timeout: float = 30.0,
        prompts_path: str | Path | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.settings.replicate_api_token}",
                "Content-Type": "application/json",
            }
        )

        self.prompts_path = (
            Path(prompts_path)
            if prompts_path is not None
            else Path("/app/config/prompts.yaml")
        )
        try:
            with self.prompts_path.open("r", encoding="utf-8") as fh:
                self.prompts: Dict[str, Dict[str, str]] = yaml.safe_load(fh) or {}
        except FileNotFoundError as exc:
            raise LLMClientError(
                f"Prompts file not found: {self.prompts_path}"
            ) from exc
        except yaml.YAMLError as exc:
            raise LLMClientError("Failed to parse prompts file") from exc

    def _prompt(self, section: str, key: str) -> str:
        try:
            return self.prompts[section][key]
        except KeyError as exc:
            raise LLMClientError(
                f"Prompt '{section}.{key}' not found in {self.prompts_path}"
            ) from exc

    def _call(self, model: str, messages: List[Dict[str, str]]) -> str:
        url = (
            f"https://api.replicate.com/v1/models/{model}/chat/completions"
        )
        payload = {"messages": messages}
        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except requests.Timeout as exc:
            raise LLMClientError("Replicate request timed out") from exc
        except requests.RequestException as exc:
            raise LLMClientError(f"Replicate request failed: {exc}") from exc
        except (KeyError, ValueError) as exc:
            raise LLMClientError("Unexpected response from Replicate") from exc

    def generate_structured_notes(self, text: str) -> List[Dict[str, Any]]:
        user_prompt = self._prompt("insights", "user").format(raw_text=text)
        content = self._call(
            "openai/gpt-5-structured",
            [
                {"role": "system", "content": self._prompt("insights", "system")},
                {"role": "user", "content": user_prompt},
            ],
        )
        return json.loads(content)["insights"]

    def group_topics(self, insights: List[Dict[str, Any]]) -> Dict[str, Any]:
        lines = [
            f"{i.get('id')}\t{i.get('title')}\t{i.get('summary')}" for i in insights
        ]
        user_prompt = self._prompt("topics", "user").format(
            insights="\n".join(lines)
        )
        content = self._call(
            "openai/gpt-5-structured",
            [
                {"role": "system", "content": self._prompt("topics", "system")},
                {"role": "user", "content": user_prompt},
            ],
        )
        return json.loads(content)

    def render_note_markdown(self, insight: Dict[str, Any]) -> str:
        user_prompt = self._prompt("note", "user").format(
            title=insight.get("title", ""),
            summary=insight.get("summary", ""),
            bullets=json.dumps(insight.get("bullets", []), ensure_ascii=False),
            tags=json.dumps(insight.get("tags", []), ensure_ascii=False),
            url=insight.get("source_url", ""),
            author=insight.get("source_author", ""),
            dt=insight.get("source_dt", ""),
            topic_id=insight.get("topic_id", ""),
            candidates=json.dumps(
                insight.get("see_also_candidates", []), ensure_ascii=False
            ),
        )
        return self._call(
            "openai/gpt-5-structured",
            [
                {"role": "system", "content": self._prompt("note", "system")},
                {"role": "user", "content": user_prompt},
            ],
        )

    def generate_moc(self, topics_json: str) -> str:
        user_prompt = self._prompt("moc", "user").format(topics_json=topics_json)
        return self._call(
            "openai/gpt-5-structured",
            [
                {"role": "system", "content": self._prompt("moc", "system")},
                {"role": "user", "content": user_prompt},
            ],
        )

    def find_autolinks(
        self, title: str, summary: str, candidates: List[str]
    ) -> List[str]:
        user_prompt = self._prompt("autolink", "user").format(
            title=title,
            summary=summary,
            candidates=json.dumps(candidates, ensure_ascii=False),
        )
        content = self._call(
            "openai/gpt-5-structured",
            [
                {"role": "system", "content": self._prompt("autolink", "system")},
                {"role": "user", "content": user_prompt},
            ],
        )
        return json.loads(content).get("related_titles", [])

    def answer_from_context(
        self, query: str, fragments: List[Dict[str, str]]
    ) -> str:
        context_lines = []
        for idx, frag in enumerate(fragments, start=1):
            context_lines.append(
                f"{idx}. [{frag.get('title')}] {frag.get('snippet')} ({frag.get('url')})"
            )
        user_prompt = self._prompt("answer", "user").format(
            query=query, context="\n".join(context_lines)
        )
        return self._call(
            "openai/gpt-5-nano",
            [
                {"role": "system", "content": self._prompt("answer", "system")},
                {"role": "user", "content": user_prompt},
            ],
        )
