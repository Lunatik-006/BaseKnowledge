# Использование `openai/gpt-5-nano` и `openai/gpt-5-structured` в Replicate через Python

Этот гайд — практическое руководство с примерами кода для создания **кодового ассистента** на основе моделей GPT‑5 от Replicate, с акцентом на:
- **`openai/gpt-5-nano`** — самая быстрая и экономичная модель, идеально подходит для быстрых задач и коротких циклов.
- **`openai/gpt-5-structured`** — поддерживает _структурированный вывод_, _веб-поиск_ и _хуки для инструментов_ для надёжных интеграций.

Примеры используют официальный Python‑клиент **`replicate`**.

---

## 1) Предварительные требования и настройка

1. Create a Replicate account and generate an API token.
2. Install the Python client:
   ```bash
   pip install --upgrade replicate
   ```
3. Set the token (prefer `.env` + `python-dotenv` or OS env vars):
   ```bash
   # macOS / Linux
   export REPLICATE_API_TOKEN="r8_***********************************"

   # Windows (PowerShell)
   setx REPLICATE_API_TOKEN "r8_***********************************"
   ```

> Tip: You can also pass the token programmatically:
> ```python
> import replicate
> client = replicate.Client(api_token="r8_...")
> ```
> If you use the default `import replicate`, the client reads `REPLICATE_API_TOKEN` automatically.

---

## 2) Идентификаторы моделей и закрепление версий

Replicate models are addressed as `owner/model[:version]`. For deterministic builds, **pin versions** from the model’s **API tab**.

**Current example versions (replace with the latest from the API page):**
- `openai/gpt-5-nano:58d44e469eadc7281ff3d0f16a33cb10fdffbb9d0fd1d5f382f8d09207fdbc82`
- `openai/gpt-5-structured:f5f984727e451eb3615cda773d0001f5898a969c425594ba86d372134d22d3da`

> You can omit the version to float to the latest, but pinning is recommended for production repeatability.

---

## 3) Быстрый старт

### 3.1 `gpt-5-nano`: single‑turn code answer
```python
import replicate

MODEL = "openai/gpt-5-nano:58d44e469eadc7281ff3d0f16a33cb10fdffbb9d0fd1d5f382f8d09207fdbc82"

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

### 3.2 Streaming in the terminal (progressive print)
```python
import replicate, sys

MODEL = "openai/gpt-5-nano:58d44e46..."

iterator = replicate.run(
    MODEL,
    input={
        "prompt": "Explain how to write parametrized tests in pytest with an example.",
        "reasoning_effort": "minimal",
        "verbosity": "medium",
        "max_completion_tokens": 600,
    },
)

for chunk in iterator:
    sys.stdout.write(chunk)
    sys.stdout.flush()
```

### 3.3 Chat turn with `messages`
```python
import replicate

MODEL = "openai/gpt-5-nano:58d44e46..."

messages = [
    {"role": "system", "content": "You are a strict but helpful code reviewer."},
    {"role": "user", "content": "Refactor this Python snippet to be more idiomatic:\n\nfor i in range(0,len(xs)):\n    print(xs[i])"},
]

out = replicate.run(MODEL, input={
    "messages": messages,
    "reasoning_effort": "minimal",
    "verbosity": "low",
    "max_completion_tokens": 400,
})
print("".join(list(out)))
```

---

## 4) `gpt-5-structured`: надёжный JSON и инструменты для кодовых ассистентов

Use `gpt-5-structured` when you must **guarantee schema‑compliant JSON** for downstream automation (linters, planners, editors), or when you need **web search** and **tool definitions**.

### 4.1 Minimal JSON schema extraction
```python
import replicate, json

MODEL = "openai/gpt-5-structured:f5f98472..."

schema = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "language": {"type": "string", "enum": ["python", "javascript", "bash"]},
        "snippets": {
            "type": "array",
            "items": {"type": "string"}
        },
    },
    "required": ["summary", "language", "snippets"],
    "additionalProperties": False,
}

prompt = "Summarize how to read a text file line-by-line and give 2–3 code snippets in Python."

iterator = replicate.run(
    MODEL,
    input={
        "prompt": prompt,
        "json_schema": schema,
        "reasoning_effort": "minimal",
        "verbosity": "low",
        "max_output_tokens": 700,
    },
)

text = "".join(list(iterator))
data = json.loads(text)  # guaranteed to conform to json_schema on success
print(json.dumps(data, indent=2, ensure_ascii=False))
```

### 4.2 Simple string‑based schema (`simple_schema`)
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

### 4.3 Web search (prototype pattern)
```python
MODEL = "openai/gpt-5-structured:f5f98472..."

it = replicate.run(
    MODEL,
    input={
        "prompt": "Find the latest stable version of pytest and show a minimal install + first test example.",
        "enable_web_search": True,
        "verbosity": "medium",
        "max_output_tokens": 700,
    },
)

print("".join(list(it)))
```

> **Note:** Always validate/clean any URLs or CLI commands returned from web-search‑enabled generations.

### 4.4 Tooling hooks (concept)
`tools` allows exposing your own functions (e.g., file ops, unit-test runner). The exact schema is a JSON list of **tool definitions**. A common approach is:
1. Define a thin set of _safe_ tools (e.g., `run_tests`, `read_file`, `write_file`).
2. In your server, intercept tool calls from the model output, execute them sandboxed, and feed results back as the next turn.
3. Keep tools minimal and deterministic; log everything.

_Pseudocode stub (you still need to mirror your tool protocol in prompts):_
```python
tools = [
    {
        "name": "run_tests",
        "description": "Run `pytest -q` in the project and return stdout/stderr.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "read_file",
        "description": "Read a UTF‑8 text file relative to the project root.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    },
]

turn = replicate.run(
    "openai/gpt-5-structured:f5f98472...",
    input={
        "instructions": "You are a code‑assistant agent. Prefer small, reversible changes. Use tools only if necessary.",
        "input_item_list": [  # richer than 'messages'; can mix images, etc.
            {"role": "user", "content": [{"type": "text", "text": "Add a failing pytest for slugify, then make it pass."}]}
        ],
        "tools": tools,
        "verbosity": "low",
        "reasoning_effort": "minimal",
        "max_output_tokens": 900,
    },
)
print("".join(list(turn)))
```

---

## 5) Выбор параметров для рабочих процессов

- **`reasoning_effort`** (`minimal` → `high`): Start with `minimal` for coding; move up only for multi‑step planning.
- **`verbosity`** (`low` → `high`): For code, `low` gives tighter diffs/snippets; bump for tutorials.
- **Token limits**: If you increase `reasoning_effort`, also increase `max_completion_tokens` (nano) or `max_output_tokens` (structured) to avoid empty completions when the model spends tokens on reasoning.
- **`messages` vs `prompt` vs `input_item_list`**: Prefer `messages` for chat; `prompt` for single‑turn; `input_item_list` when mixing modalities or building agent loops.
- **Schema choice**: Use `json_schema` for nested objects; `simple_schema` for flat structures and lists.
- **Web search**: Treat as untrusted I/O. Parse, filter, and re‑verify with your own validators.

---

## 6) Справочные сниппеты

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

### gpt-5-structured

```python
import replicate

input = {
    "model": "gpt-5",
    "prompt": "Use the web to find a news article headline from today",
    "json_schema": {},
    "reasoning_effort": "low",
    "enable_web_search": True
}

output = replicate.run(
    "openai/gpt-5-structured",
    input=input
)

print(output)
#=> {"text":"Here’s a news headline from today, August 14, 20...
```

---

## 7) Полезные ссылки (open each model’s **API** tab for latest inputs/versions)

- Replicate Python quickstart & streaming
- Replicate API tokens & auth
- `openai/gpt-5-nano` (API & schema)
- `openai/gpt-5-structured` (API & schema)

> Always check the model **version** and **input params** in the API tab before deploying.

---

## 8) Схемы ввода/вывода и промпт‑конфиг

- Схема входа `gpt-5-nano`: `./gpt-5-nano-input-schema.json`
- Схема входа `gpt-5-structured`: `./gpt-5-structured-input-schema.json`
- Схема выхода моделей (общая): `./gpt-5-output-schema.json`
- Промпт‑конфиг (YAML): `../config/prompts.yaml`

Как код использует промпт‑конфиг:
- Класс `libs/llm/replicate_client.py:ReplicateLLMClient` загружает `prompts.yaml` при инициализации (по умолчанию `/app/config/prompts.yaml`, можно передать путь вручную).
- Доступ к строкам осуществляется через `_prompt(section, key)`, где `key` обычно `system` или `user`.
- Для каждой операции формируются `messages` и вызывается `replicate.run` с нужной моделью.
- При отсутствии файла/ключа выбрасывается `LLMClientError`.

Краткое соответствие «промпт = задача» (секция в YAML → метод):
- `insights` → извлечение инсайтов из текста → `generate_structured_notes()` (`gpt-5-structured`)
- `topics` → группировка инсайтов по темам → `group_topics()` (`gpt-5-structured`)
- `note` → генерация Markdown‑заметки из инсайта → `render_note_markdown()` (`gpt-5-structured`)
- `moc` → генерация MOC/оглавления → `generate_moc()` (`gpt-5-structured`)
- `autolink` → поиск связанных заметок → `find_autolinks()` (`gpt-5-structured`)
- `answer` → ответ на запрос по заданному контексту → `answer_from_context()` (`gpt-5-nano`)
