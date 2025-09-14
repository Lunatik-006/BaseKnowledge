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

        # LLM diagnostics and limits (configurable via Settings / env)
        # Fall back to sensible defaults if custom Settings class is used in tests
        self._log_payloads: bool = bool(getattr(self.settings, "llm_log_payloads", False))
        self._max_output_tokens: int = int(
            getattr(self.settings, "llm_max_output_tokens", 2048)
        )
        self._max_completion_tokens: int = int(
            getattr(self.settings, "llm_max_completion_tokens", 1024)
        )

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
        """Call Replicate model using the official client per guide and schemas.

        - For `openai/gpt-5-structured`, follow docs/gpt-5-structured-input-schema.json:
          use `instructions` (system) + `input_item_list` (user) and `response_format`
          for JSON schemas, along with `max_output_tokens`.
        - For `openai/gpt-5-nano`, follow docs/gpt-5-nano-input-schema.json:
          use chat `messages` (or `prompt`) and `max_completion_tokens`.
        """
        try:
            input_payload: Dict[str, Any] = {
                "reasoning_effort": "minimal",
                "verbosity": "low",
            }

            # Merge any extra input passed via a sentinel element at the tail
            extra_input: Dict[str, Any] = {}
            if messages and isinstance(messages[-1], dict) and "_extra_input" in messages[-1]:
                sentinel = messages.pop()  # type: ignore[assignment]
                try:
                    extra_input = dict(sentinel.get("_extra_input") or {})
                except Exception:
                    extra_input = {}

            # Structured vs Nano mapping strictly per schemas in docs
            is_structured = model.endswith("gpt-5-structured")

            if is_structured:
                # docs/gpt-5-structured-input-schema.json
                # Map chat-style messages into schema-compliant fields:
                # - Combine system messages into `instructions`
                # - Convert user messages into `input_item_list` with input_text content
                system_parts = [
                    (m.get("content") or "")
                    for m in messages
                    if isinstance(m, dict) and m.get("role") == "system"
                ]
                user_parts = [
                    (m.get("content") or "")
                    for m in messages
                    if isinstance(m, dict) and m.get("role") == "user"
                ]

                instructions = "\n\n".join([p for p in system_parts if p])
                if instructions:
                    input_payload["instructions"] = instructions

                input_item_list = []
                for part in [p for p in user_parts if p]:
                    input_item_list.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_text",
                                    "text": part,
                                }
                            ],
                        }
                    )
                if input_item_list:
                    input_payload["input_item_list"] = input_item_list

                # Be explicit about model family selection for structured
                input_payload.setdefault("model", "gpt-5")

                # Tokens control per schema
                tokens_key = "max_output_tokens"
                input_payload[tokens_key] = self._max_output_tokens
            else:
                # docs/gpt-5-nano-input-schema.json
                # Prefer passing chat messages, fallback to concatenated prompt
                has_roles = bool(
                    isinstance(messages, list)
                    and messages
                    and isinstance(messages[0], dict)
                    and "role" in messages[0]
                )
                if has_roles:
                    input_payload["messages"] = messages
                else:
                    input_payload["prompt"] = "\n\n".join(
                        [m.get("content", "") for m in messages if isinstance(m, dict)]
                    )

                tokens_key = "max_completion_tokens"
                input_payload[tokens_key] = self._max_completion_tokens

            # Merge any extras (e.g., response_format.json_schema) as recommended by guide
            if extra_input:
                input_payload.update(extra_input)

            # Log full request payload for debugging (standard format)
            try:
                payload_json = json.dumps(input_payload, ensure_ascii=False, default=str)
            except Exception:
                payload_json = repr(input_payload)
            _lvl = logging.INFO if self._log_payloads else logging.DEBUG
            self.logger.log(_lvl, "Replicate request | model=%s | input=%s", model, payload_json)

            out = replicate.run(model, input=input_payload)

            # Capture raw response before joining for logging purposes
            # Normalize output into text while keeping a raw view for logging.
            raw_view: Any = out
            text: str
            if out is None:
                text = ""
            elif isinstance(out, str):
                text = out
            elif isinstance(out, dict):
                # Replicate may return a dict with keys like 'json_output' and 'text'
                if "json_output" in out:
                    jo = out.get("json_output")
                    if isinstance(jo, str):
                        text = jo
                    else:
                        try:
                            text = json.dumps(jo, ensure_ascii=False)
                        except Exception:
                            text = str(jo)
                elif "text" in out and isinstance(out.get("text"), str):
                    text = out.get("text") or ""
                else:
                    # Fallback to dumping the whole object
                    try:
                        text = json.dumps(out, ensure_ascii=False)
                    except Exception:
                        text = str(out)
            else:
                # Many models stream an iterator of string chunks
                try:
                    chunks = list(out)  # type: ignore[arg-type]
                except Exception as exc:  # pragma: no cover - defensive
                    raise LLMClientError("Unexpected streaming output from Replicate") from exc
                try:
                    text = "".join(chunks)
                except Exception:
                    text = "".join(str(c) for c in chunks)

            # Log raw response (as-is chunks) for debugging
            try:
                raw_json = json.dumps(raw_view, ensure_ascii=False, default=str)
            except Exception:
                raw_json = repr(raw_view)
            self.logger.log(_lvl, "Replicate raw response | model=%s | raw=%s", model, raw_json)

            if not text.strip() and tokens_key == "max_output_tokens":
                # Proactive single retry with higher cap for structured outputs
                try:
                    prev = int(input_payload.get(tokens_key, 0))
                except Exception:
                    prev = self._max_output_tokens
                new_cap = min(max(prev * 2, 2048), 4096)
                if new_cap > prev:
                    self.logger.info(
                        "Replicate empty output; retry with %s=%s (prev=%s)",
                        tokens_key,
                        new_cap,
                        prev,
                    )
                    input_payload[tokens_key] = new_cap
                    _retry_out = replicate.run(model, input=input_payload)
                    raw_view = _retry_out
                    if _retry_out is None:
                        text = ""
                    elif isinstance(_retry_out, str):
                        text = _retry_out
                    elif isinstance(_retry_out, dict):
                        if "json_output" in _retry_out:
                            jo = _retry_out.get("json_output")
                            if isinstance(jo, str):
                                text = jo
                            else:
                                try:
                                    text = json.dumps(jo, ensure_ascii=False)
                                except Exception:
                                    text = str(jo)
                        elif "text" in _retry_out and isinstance(_retry_out.get("text"), str):
                            text = _retry_out.get("text") or ""
                        else:
                            try:
                                text = json.dumps(_retry_out, ensure_ascii=False)
                            except Exception:
                                text = str(_retry_out)
                    else:
                        try:
                            _retry_chunks = list(_retry_out)  # type: ignore[arg-type]
                        except Exception as exc:  # pragma: no cover
                            raise LLMClientError("Unexpected streaming output from Replicate") from exc
                        try:
                            text = "".join(_retry_chunks)
                        except Exception:
                            text = "".join(str(c) for c in _retry_chunks)

                    try:
                        raw_json_retry = json.dumps(raw_view, ensure_ascii=False, default=str)
                    except Exception:
                        raw_json_retry = repr(raw_view)
                    self.logger.log(
                        _lvl,
                        "Replicate raw response (retry) | model=%s | raw=%s",
                        model,
                        raw_json_retry,
                    )

            return text
        except Exception as exc:
            # Ensure failure is visible in logs with stack trace
            self.logger.exception("Replicate request failed: %s", exc)
            raise LLMClientError(f"Replicate request failed: {exc}") from exc

    def generate_structured_notes(self, text: str) -> List[Dict[str, Any]]:
        user_prompt = self._prompt("insights", "user").format(raw_text=text)
        # Ask for strict JSON per docs using response_format.json_schema merged via _extra_input
        schema = {
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
                        "required": ["id", "title", "summary", "bullets", "tags", "confidence"],
                        "additionalProperties": False,
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
                {
                    "_extra_input": {
                        "response_format": {
                            "type": "json_schema",
                            "json_schema": {
                                "name": "insights_extraction",
                                "strict": True,
                                "schema": schema,
                            },
                        }
                    }
                },
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
        schema = {
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
                        "additionalProperties": False,
                    },
                },
                "orphans": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["topics"],
            "additionalProperties": False,
        }
        content = self._call(
            "openai/gpt-5-structured",
            [
                {"role": "system", "content": self._prompt("topics", "system")},
                {"role": "user", "content": user_prompt},
                {
                    "_extra_input": {
                        "response_format": {
                            "type": "json_schema",
                            "json_schema": {
                                "name": "topics_grouping",
                                "strict": True,
                                "schema": schema,
                            },
                        }
                    }
                },
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
        schema = {
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
                {
                    "_extra_input": {
                        "response_format": {
                            "type": "json_schema",
                            "json_schema": {
                                "name": "autolinks",
                                "strict": True,
                                "schema": schema,
                            },
                        }
                    }
                },
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
