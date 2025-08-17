from __future__ import annotations

import json
from typing import Any, Dict, List

import requests

from libs.core.settings import Settings, get_settings
from .llm_client import LLMClient


# Prompts from Technical Specification sections 8.1-8.6
PROMPT_INSIGHTS_SYSTEM = """Ты — редактор знаний. Выделяй "чистое знание" из входного текста разной длины:
— короткие посты: 1–3 компактных insights;
— длинные тексты: 5–30 insights, объединённых по смыслу.
Каждый insight — атомная единица знания (1 мысль/правило/шаг).
Удаляй рекламу/воду, сохраняй важные caveats.

Строго верни JSON по схеме:
{
"insights": [
{
"id": "i-<uuid-like>",
"title": "≤80 символов",
"summary": "1–3 предложения сути",
"bullets": ["атомный тезис 1", "атомный тезис 2", "..."],
"tags": ["до 5 коротких тегов"],
"confidence": 0.0..1.0
},
]
}
Никаких комментариев вне JSON.
"""

PROMPT_INSIGHTS_USER = """Текст:
<<<
{raw_text}

> > >

Метаданные (опц): source_url={{{{URL}}}}, author={{{{AUTHOR}}}}, dt={{{{DATETIME}}}}, channel={{{{CHANNEL}}}}
Задача: верни JSON по схеме. Если текста мало — верни 1–2 insights.
"""

PROMPT_TOPICS_SYSTEM = """Ты — куратор. Сгруппируй список инсайтов по 10–30 темам.
Верни JSON:
{
"topics":[{"topic_id":"t-<id>","title":"название темы","desc":"1–2 предложения","insight_ids":["i-1","i-2","..."]}],
"orphans":["i-..."]
}
Без комментариев вне JSON.
"""

PROMPT_TOPICS_USER = """Инсайты (id, title, summary):
<<<
{insights}

> > >

Сгруппируй и верни JSON.
"""

PROMPT_NOTE_SYSTEM = """Ты — генератор Obsidian-заметок. Верни ровно ОДИН Markdown-документ.
Требования:

* YAML: title, created (ISO), tags[], source_url?, source_author?, source_dt?, topic_id?
* Тело:

  * 3–5 предложений описания (суть из summary)
  * Раздел "Тезисы": маркдаун-список из bullets (каждый — 1 факт/правило)
  * (опц) "Применение": когда и как использовать
  * "Источники": список ссылок (если есть source_url)
  * (опц) "См. также": до 5 [[Заголовок]] из предоставленного списка candidates
    Никаких комментариев вне Markdown.
    Строго сохраняй смысл, не выдумывай факты.
"""

PROMPT_NOTE_USER = """Данные:
title="{title}"
summary="{summary}"
bullets={bullets}
tags={tags}
meta: source_url={url}, source_author={author}, source_dt={dt}, topic_id={topic_id}
Кандидаты для "См. также": {candidates}
Сгенерируй один Markdown.
"""

PROMPT_MOC_SYSTEM = """Ты — редактор MOC. Верни один Markdown с оглавлением по темам.
Для каждой темы: "## {{title}}" и список "- [[NoteTitle]] — 1 строка описания".
Без комментариев вне Markdown.
"""

PROMPT_MOC_USER = """Темы и заметки:
{topics_json}
Сгенерируй один Markdown MOC.
"""

PROMPT_AUTOLINK_SYSTEM = """Ты — помощник связей. По заголовку/summary текущей заметки выбери до 5 релевантных из списка кандидатов.
Верни JSON: {"related_titles":["...", "..."]} без комментариев.
"""

PROMPT_AUTOLINK_USER = """Текущая заметка: title="{title}", summary="{summary}"
Кандидаты: {candidates}
Верни JSON.
"""

PROMPT_ANSWER_SYSTEM = """Ты — ассистент базы заметок. Отвечай ТОЛЬКО по CONTEXT (список фрагментов).
Если ответа нет — скажи "не нашёл в базе".
В конце дай раздел "См. также" со списком до 5 заметок (title → ссылка).
Верни Markdown.
"""

PROMPT_ANSWER_USER = """QUERY: {query}
CONTEXT:

{context}
Сформируй краткий, точный ответ только из CONTEXT.
"""


class LLMClientError(Exception):
    """Raised when interaction with LLM fails."""


class ReplicateLLMClient(LLMClient):
    """LLM client powered by Replicate API."""

    def __init__(self, settings: Settings | None = None, timeout: float = 30.0) -> None:
        self.settings = settings or get_settings()
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.settings.replicate_api_token}",
                "Content-Type": "application/json",
            }
        )
        self.api_url = "https://api.replicate.com/v1/chat/completions"

    def _call(self, model: str, messages: List[Dict[str, str]]) -> str:
        payload = {"model": model, "messages": messages}
        try:
            response = self.session.post(
                self.api_url, json=payload, timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except requests.Timeout as exc:
            raise LLMClientError("Replicate request timed out") from exc
        except requests.RequestException as exc:
            raise LLMClientError(f"Replicate request failed: {exc}") from exc
        except (KeyError, ValueError) as exc:
            raise LLMClientError("Unexpected response from Replicate") from exc

    def generate_structured_notes(self, text: str) -> Dict[str, Any]:
        user_prompt = PROMPT_INSIGHTS_USER.format(raw_text=text)
        content = self._call(
            "openai/gpt-5-structured",
            [
                {"role": "system", "content": PROMPT_INSIGHTS_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
        )
        return json.loads(content)

    def render_note_markdown(self, insight: Dict[str, Any]) -> str:
        user_prompt = PROMPT_NOTE_USER.format(
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
                {"role": "system", "content": PROMPT_NOTE_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
        )

    def answer_from_context(
        self, query: str, fragments: List[Dict[str, str]]
    ) -> str:
        context_lines = []
        for idx, frag in enumerate(fragments, start=1):
            context_lines.append(
                f"{idx}. [{frag.get('title')}] {frag.get('snippet')} ({frag.get('url')})"
            )
        user_prompt = PROMPT_ANSWER_USER.format(
            query=query, context="\n".join(context_lines)
        )
        return self._call(
            "openai/gpt-5-nano",
            [
                {"role": "system", "content": PROMPT_ANSWER_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
        )
