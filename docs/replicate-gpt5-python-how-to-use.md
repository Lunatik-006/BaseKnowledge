# Using `openai/gpt-5-nano` and `openai/gpt-5-structured` on Replicate via Python

This guide is a hands‑on tutorial with code examples for building a **code assistant** based on GPT‑5 models from Replicate, with a focus on:

- **`openai/gpt-5-nano`** — the fastest and most cost‑efficient model, ideal for quick tasks and tight loops.
- **`openai/gpt-5-structured`** — supports _structured output_, _web search_, and _tool hooks_ for reliable integrations.

Examples use the official **`replicate`** Python client.

---

## 1) Prerequisites and setup

1. Create a Replicate account and generate an API token.
2. Install the Python client with `pip install replicate` or include `replicate` in your requirements file.
3. Set the token (prefer `.env` + `python-dotenv`, or OS environment variables).

---

## 2) Quick start

### 2.1 `gpt-5-nano`: single‑turn answer

```python
import replicate

MODEL = "openai/gpt-5-nano"

prompt = "Write a Python function `slugify(s: str) -> str` with tests using pytest."
out = replicate.run(
    MODEL,
    input={
        "prompt": prompt,
        # Alternative to prompt: pass chat-style "messages"
        # "messages": [{"role": "user", "content": prompt}],
        "reasoning_effort": "minimal",   # minimal | low | medium | high
        "verbosity": "low",               # low | medium | high
        "max_completion_tokens": 800,
    },
)

# Some models stream; gpt-5-nano returns an iterator of text chunks. Concatenate:
text = "".join(list(out)) if not isinstance(out, str) else out
print(text)
```

---

## 3) `gpt-5-structured`: robust JSON and tools for code assistants

Use `gpt-5-structured` when you must **guarantee schema‑compliant JSON** for downstream automation.

### 3.1 Minimal JSON schema extraction (via `response_format`)

```python
import json
import replicate

MODEL = "openai/gpt-5-structured"  # можно закрепить конкретную версию

response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "code_assistant_extract",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "summary":  {"type": "string"},
                "language": {"type": "string", "enum": ["python", "javascript", "bash"]},
                "snippets": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["summary", "language", "snippets"],
            "additionalProperties": False
        }
    }
}

prompt = "Summarize how to read a text file line-by-line and give 2–3 code snippets in Python."

out = replicate.run(
    MODEL,
    input={
        "instructions": "Return ONLY JSON that conforms to the schema.",
        "input_item_list": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt}
                ]
            }
        ],
        "response_format": response_format,
        "reasoning_effort": "minimal",
        "verbosity": "low",
        "max_output_tokens": 700
    },
)

# Универсальная распаковка результата в dict
def to_obj(x):
    if isinstance(x, dict):
        return x
    if isinstance(x, str):
        try:
            return json.loads(x)
        except Exception:
            return {"raw": x}
    if hasattr(x, "read"):  # FileOutput
        data = x.read()
        try:
            return json.loads(data.decode("utf-8"))
        except Exception:
            return {"bytes_len": len(data)}
    if isinstance(x, list):
        for item in x:
            v = to_obj(item)
            if v is not None:
                return v
    return {"output": x}

data = to_obj(out)
print(json.dumps(data, indent=2, ensure_ascii=False))
```

> Примечание: **не** передавай «голую» JSON Schema полем `json_schema` на верхнем уровне `input` — это приведёт к ошибкам вида `Unknown parameter: 'text.name'`. Используй `response_format.json_schema`.

### 3.2 Simple string‑based schema (`simple_schema`)

When you only need flat fields, you can define a lightweight format:

```python
MODEL = "openai/gpt-5-structured:f5f98472..."

# Fields: "title" (string), "ok" (boolean), "score" (number), "tags" (list[str])
simple_schema = [
    "title",
    "ok:bool",
    "score:number",
    "tags:list:str",
]

it = replicate.run(
    MODEL,
    input={
        "prompt": "Produce a short status object for code quality of a 200‑line module.",
        "simple_schema": simple_schema,
        "verbosity": "low",
    },
)
print("".join(list(it)))
```

> ℹ️ Если структура становится вложенной (объекты/объекты в массивах/enum и т.п.), вместо `simple_schema` переходи на полноценную JSON Schema **через** `response_format.json_schema` (см. пример в 3.1). Это избавляет от ошибок совместимости и даёт строгую валидацию.

---

## 4) Choosing parameters for workflows

- **`reasoning_effort`** (`minimal` → `high`): Use `minimal` for search; `low` for small tasks; `medium` for most tasks; and `high` for complex tasks with lots of context.
- **`verbosity`** (`low` → `high`): Use `low` for search and data‑grounded questions; increase for creative/explanatory tasks.
- **Token limits**: If you increase `reasoning_effort`, also increase `max_completion_tokens` (nano) or `max_output_tokens` (structured) to avoid empty completions when the model spends tokens on reasoning.
- **Schema choice**: Use `json_schema` for nested objects; `simple_schema` for flat structures and lists.

---

## 5) Reference snippets

### gpt-5-nano

```python
# The openai/gpt-5-nano model can stream output as it's running.
for event in replicate.stream(
    "openai/gpt-5-nano",
    input={
        "prompt": "Explain Bernoulli's principle",
        "image_input": [],
        "system_prompt": "You only know how to speak Russian ",
        "reasoning_effort": "medium",
        "max_completion_tokens": 4096
    },
):
    print(str(event), end="")
```

### gpt-5-structured — structured output (OpenAI Responses API compatible)

   *“`gpt-5-structured` выдаёт строго структурированный JSON через механизм **Structured Outputs** (OpenAI) — в Replicate это задаётся полем `response_format` с типом `json_schema`.”* 

```python
import json
import replicate

MODEL = "openai/gpt-5-structured"

response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "today_news_headline",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "headline": {"type": "string"},
                "source":   {"type": "string"},
                "url":      {"type": "string"}
            },
            "required": ["headline", "source", "url"],
            "additionalProperties": False
        }
    }
}

input_payload = {
    "instructions": "Use the web if available. Return ONLY JSON.",
    "input_item_list": [
        {"role": "user",
         "content": [{"type": "input_text",
                      "text": "Find one news headline from today and return headline/source/url."}]}
    ],
    "response_format": response_format,
    "reasoning_effort": "low",
    "verbosity": "low",
    "max_output_tokens": 600,
    # "enable_web_search": True  # если версия/права это поддерживают
}

out = replicate.run(MODEL, input=input_payload)

# печать как JSON-объекта
def to_obj(x):
    if isinstance(x, dict): return x
    if isinstance(x, str):
        try: return json.loads(x)
        except Exception: return {"raw": x}
    if hasattr(x, "read"):  # FileOutput
        data = x.read()
        try: return json.loads(data.decode("utf-8"))
        except Exception: return {"bytes_len": len(data)}
    if isinstance(x, list):
        for item in x:
            v = to_obj(item)
            if v is not None:
                return v
    return {"output": x}

print(json.dumps(to_obj(out), indent=2, ensure_ascii=False))
```

---

## 6) Useful links (open each model’s **API** tab for latest inputs/versions)

- Replicate Python quickstart & streaming
- Replicate API tokens & auth
- `openai/gpt-5-nano` (API & schema)
- `openai/gpt-5-structured` (API & schema)

> Always check the model **version** and **input parameters** in the API tab before deploying.

---

## 7) I/O schemas and prompt config

- Input schema for `gpt-5-nano`: `./gpt-5-nano-input-schema.json`
- Input schema for `gpt-5-structured`: `./gpt-5-structured-input-schema.json`
- Output schema (common): `./gpt-5-output-schema.json`
- Prompt config (YAML): `../config/prompts.yaml`

How the code uses the prompt config:

- The class `libs/llm/replicate_client.py:ReplicateLLMClient` loads `prompts.yaml` on initialization (defaults to `/app/config/prompts.yaml`; the path can be overridden).
- Access strings via `_prompt(section, key)`, where `key` is typically `system` or `user`.
- For each operation, build `messages` and call `replicate.run` with the required model.
- If the file/key is missing, an `LLMClientError` is raised.

Mapping “prompt = task” (YAML section → method):

- `insights` → extract insights from text → `generate_structured_notes()` (`gpt-5-structured`)
- `topics` → group insights by topics → `group_topics()` (`gpt-5-structured`)
- `note` → generate a Markdown note from an insight → `render_note_markdown()` (`gpt-5-structured`)
- `moc` → generate a MOC/table of contents → `generate_moc()` (`gpt-5-structured`)
- `autolink` → find related notes → `find_autolinks()` (`gpt-5-structured`)
- `answer` → answer a query given a specific context → `answer_from_context()` (`gpt-5-nano`)
