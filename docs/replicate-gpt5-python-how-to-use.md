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

### 3.1 Minimal JSON schema extraction
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
