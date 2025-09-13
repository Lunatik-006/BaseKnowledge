from __future__ import annotations

import json
from pathlib import Path
import logging
from typing import Any, Dict, Iterable, List, Union

import replicate
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
        self.timeout = timeout  # reserved for future granular timeouts
        self.logger = logging.getLogger(__name__)

        self.prompts_path = (
            Path(prompts_path)
            if prompts_path is not None
            else Path("/app/config/prompts.yaml")
        )
        try:
            with self.prompts_path.open("r", encoding="utf-8") as fh:
                self.prompts: Dict[str, Dict[str, str]] = yaml.safe_load(fh) or {}
            # Log which prompts file is loaded for transparency
            self.logger.debug("Prompts loaded from: %s", str(self.prompts_path))
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

    def _join_output(self, out: Union[str, Iterable[str], None]) -> str:
        if out is None:
            return ""
        if isinstance(out, str):
            return out
        try:
            return "".join(list(out))  # type: ignore[arg-type]
        except Exception as exc:  # pragma: no cover - defensive
            raise LLMClientError("Unexpected streaming output from Replicate") from exc

    def _clean_json_text(self, text: str) -> str:
        """Try to clean common wrappers around JSON.

        - Strip code fences like ```json ... ``` or ``` ... ```
        - Trim whitespace
        - If still fails, try to slice from first '{' to last '}'
        """
        s = text.strip()
        if not s:
            return s
        # Remove Markdown code fences
        if s.startswith("```"):
            # Drop the first fence line
            parts = s.splitlines()
            # Find closing fence
            try:
                end_idx = next(i for i, line in enumerate(parts[1:], start=1) if line.strip().startswith("```") )
                s = "\n".join(parts[1:end_idx]).strip()
            except StopIteration:
                # No closing fence; fall back to slicing braces below
                pass
        # If it already looks like JSON, return
        if s.startswith("{") and s.endswith("}"):
            return s
        # Try to slice by outermost braces
        if "{" in s and "}" in s:
            start = s.find("{")
            end = s.rfind("}")
            if start != -1 and end != -1 and end > start:
                candidate = s[start : end + 1].strip()
                return candidate
        return s

    def _parse_json(self, text: str) -> Any:
        s = text.strip()
        if not s:
            raise LLMClientError("Empty response from Replicate when JSON was expected")
        try:
            return json.loads(s)
        except Exception:
            s2 = self._clean_json_text(s)
            try:
                return json.loads(s2)
            except Exception as exc:
                preview = (s2[:200] + "…") if len(s2) > 200 else s2
                raise LLMClientError(
                    f"Failed to parse JSON from Replicate output. Preview: {preview}"
                ) from exc

    def _call(self, model: str, messages: List[Dict[str, str]]) -> str:
        """Call Replicate model using the official client per guide.

        - For gpt-5-structured, tokens param is `max_output_tokens`.
        - For gpt-5-nano, tokens param is `max_completion_tokens`.
        """
        try:
            input_payload: Dict[str, Any] = {
                "reasoning_effort": "minimal",
                "verbosity": "low",
            }

            # Merge messages or prompt + any extra input passed via a sentinel element
            extra_input: Dict[str, Any] = {}
            if messages and isinstance(messages[-1], dict) and "_extra_input" in messages[-1]:
                sentinel = messages.pop()  # type: ignore[assignment]
                try:
                    extra_input = dict(sentinel.get("_extra_input") or {})
                except Exception:
                    extra_input = {}

            # Support passing either chat messages or a single prompt string
            if isinstance(messages, list) and messages and isinstance(messages[0], dict) and "role" in messages[0]:
                input_payload["messages"] = messages
            else:  # Fallback to prompt concatenation if something else was provided
                # Keep a conservative fallback; callers should pass proper messages normally
                input_payload["prompt"] = "\n\n".join(
                    [m.get("content", "") for m in messages if isinstance(m, dict)]
                )

            # Tokens knob depends on model family
            if model.endswith("gpt-5-structured"):
                input_payload["max_output_tokens"] = 900
            else:
                input_payload["max_completion_tokens"] = 900

            # Merge any extras (e.g., json_schema) as recommended by guide
            if extra_input:
                input_payload.update(extra_input)

            # Log full request payload for debugging (standard format)
            try:
                payload_json = json.dumps(input_payload, ensure_ascii=False, default=str)
            except Exception:
                payload_json = repr(input_payload)
            self.logger.debug("Replicate request | model=%s | input=%s", model, payload_json)

            out = replicate.run(model, input=input_payload)

            # Capture raw response before joining for logging purposes
            raw_chunks: List[str]
            if out is None:
                raw_chunks = []
            elif isinstance(out, str):
                raw_chunks = [out]
            else:
                try:
                    raw_chunks = list(out)  # type: ignore[arg-type]
                except Exception as exc:  # pragma: no cover - defensive
                    raise LLMClientError("Unexpected streaming output from Replicate") from exc

            # Log raw response (as-is chunks) for debugging
            try:
                raw_json = json.dumps(raw_chunks, ensure_ascii=False, default=str)
            except Exception:
                raw_json = repr(raw_chunks)
            self.logger.debug("Replicate raw response | model=%s | raw=%s", model, raw_json)

            text = "".join(raw_chunks)
            return text
        except Exception as exc:
            # Ensure failure is visible in logs with stack trace
            self.logger.exception("Replicate request failed: %s", exc)
            raise LLMClientError(f"Replicate request failed: {exc}") from exc

    def generate_structured_notes(self, text: str) -> List[Dict[str, Any]]:
        user_prompt = self._prompt("insights", "user").format(raw_text=text)
        # Ask for strict JSON per docs using json_schema merged via _extra_input
        json_schema = {
            "type": "object",
            "properties": {
                "insights": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "summary": {"type": "string"},
                            "bullets": {"type": "array", "items": {"type": "string"}},
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "confidence": {"type": "number"},
                            "meta": {"type": "object"},
                        },
                        "required": ["title", "summary"],
                        "additionalProperties": True,
                    },
                }
            },
            "required": ["insights"],
            "additionalProperties": False,
        }
        content = self._call(
            "openai/gpt-5-structured",
            [
                {"role": "system", "content": self._prompt("insights", "system")},
                {"role": "user", "content": user_prompt},
                {"_extra_input": {"json_schema": json_schema}},
            ],
        )
        data = self._parse_json(content)
        return data.get("insights", [])

    def group_topics(self, insights: List[Dict[str, Any]]) -> Dict[str, Any]:
        lines = [
            f"{i.get('id')}\t{i.get('title')}\t{i.get('summary')}" for i in insights
        ]
        user_prompt = self._prompt("topics", "user").format(
            insights="\n".join(lines)
        )
        json_schema = {
            "type": "object",
            "properties": {
                "topics": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "topic_id": {"type": "string"},
                            "title": {"type": "string"},
                            "desc": {"type": "string"},
                            "insight_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["topic_id", "title", "insight_ids"],
                        "additionalProperties": True,
                    },
                },
                "orphans": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["topics"],
            "additionalProperties": True,
        }
        content = self._call(
            "openai/gpt-5-structured",
            [
                {"role": "system", "content": self._prompt("topics", "system")},
                {"role": "user", "content": user_prompt},
                {"_extra_input": {"json_schema": json_schema}},
            ],
        )
        return self._parse_json(content)

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
        json_schema = {
            "type": "object",
            "properties": {
                "related_titles": {
                    "type": "array",
                    "items": {"type": "string"},
                }
            },
            "required": ["related_titles"],
            "additionalProperties": False,
        }
        content = self._call(
            "openai/gpt-5-structured",
            [
                {"role": "system", "content": self._prompt("autolink", "system")},
                {"role": "user", "content": user_prompt},
                {"_extra_input": {"json_schema": json_schema}},
            ],
        )
        data = self._parse_json(content)
        return data.get("related_titles", [])

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
