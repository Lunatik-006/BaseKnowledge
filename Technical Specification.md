```markdown
# ТЗ (v1.1) — Telegram Bot + Mini App → Obsidian-заметки + Поиск (RAG)

**Стек:**
- **Платформа:** Telegram Bot + **Telegram Mini App (WebApp)**  
  > Примечание: Mini App — это веб-клиент (HTML/JS) внутри Telegram. **Полностью на Python Mini App сделать нельзя**, поэтому фронтенд — **Next.js**; бэкенд — **Python (FastAPI)**.
- **LLM через Replicate:**  
  - Разбиение/генерация заметок — `openai/gpt-5-structured`  
  - Поиск/ответ из контекста — `openai/gpt-5-nano`
  - Эмбеддинги — `BGE-M3` (или `bge-small`) через Replicate
- **Векторное хранилище:** Milvus (standalone, Docker)
- **Реляционная БД:** PostgreSQL (метаданные, пользователи, квоты и т. п.)
- **OS/Infra:** Ubuntu + Docker/Compose
- **Файлы заметок:** локальная файловая система (без S3)

---

## 0) Цели

1) Принимать **любые тексты** (короткие посты и длинные простыни/подборки) → получать **структурированные Obsidian-заметки** (Markdown с YAML), **автоссылки** и MOC.  
2) Давать **поиск по базе** заметок (RAG): векторный поиск → компактная LLM-сшивка ответа.  
3) **Минимум трения**: «переслал боту → получил заметки и/или ZIP» + **Mini App** для просмотра.

---

## 1) Нефункциональные требования

- Контейнеризация: Docker Compose.
- Конфигурация: `.env` (секреты и токены через переменные окружения).
- Кросс-языковая поддержка (RU/EN) на уровне LLM и эмбеддингов.
- Простая масштабируемость: вынести индексацию в воркеры/очереди при росте.

---

## 2) Архитектура (высокоуровнево)

**Сервисы:**
- `api` — FastAPI: REST, Telegram webhook, RAG-поиск.
- `miniapp` — Next.js: UI просмотра заметок, поиск, «Open in Obsidian».
- `milvus` — векторный индекс (коллекции `chunks`/`notes_meta`).
- `postgres` — метаданные/пользователи/сессии/квоты.
- (опц.) `worker` — фоновые задачи (позже).

**Пайплайн ingest → notes:**
```

raw text → LLM (structured insights) → генерация .md → сохранение на FS
↓
чанкинг → эмбеддинги → Milvus.upsert

```

**Пайплайн search:**
```

query → embed → Milvus.search (top-k) → сшивка ответа (gpt-5-nano) → answer.md

```

---

## 3) Структура проекта (ООП-ориентированно, кратко)

```

monorepo/
├─ apps/
│   ├─ api/        # FastAPI: роуты: ingest, notes, search, export, telegram webhook
│   ├─ miniapp/    # Next.js: список, просмотр, поиск, «open in obsidian», zip
│   └─ bot/        # (опц.) тонкий слой, можно инлайнить в api
├─ libs/
│   ├─ core/       # доменные сущности (DTO), ошибки, конфиг
│   ├─ llm/        # абстракция LLM + Replicate клиент (5-structured / 5-nano)
│   ├─ rag/        # эмбеддинги, чанкинг, Milvus индекс, конструктор ответа
│   ├─ db/         # PostgreSQL (SQLAlchemy/psycopg), модели и репозитории
│   └─ storage/    # FS-операции: запись/чтение .md, экспорт ZIP
├─ infra/
│   ├─ docker/     # Dockerfiles, docker-compose.yml
│   └─ scripts/    # утилиты импорта/экспорта, миграции индекса
├─ tests/          # unit/integration (минимально)
├─ .env.example
└─ README.md

```

**Основные классы/интерфейсы (без кода):**
- `LLMClient` (интерфейс): `generate_structured_notes`, `render_note_markdown`, `answer_from_context`
- `EmbeddingsProvider`: `embed_texts(list[str]) -> list[list[float]]`
- `VectorIndex` (Milvus): `upsert_chunks`, `search(query_vec, k)`
- `NotesStorage` (FS): `save_note`, `read_note`, `export_zip`
- UseCases: `IngestText`, `Search`

---

## 4) Данные и схемы

### PostgreSQL (минимум)
- `users` (id, telegram_id, created_at)
- `notes` (id, title, tags[], topic_id?, created_at, file_path, source_url?, author?, dt?, channel?)
- `chunks` (id, note_id → notes.id, pos, anchor?)  
  > Текст чанков и эмбеддинги **не** в Postgres — текст хранится на FS, эмбеддинги в Milvus.

### Milvus
- `chunks`:  
  - `chunk_id` (pk), `note_id` (string), `pos` (int), `text` (string), `embedding` (float_vector, dim=768)
  - Индекс: HNSW (`M=16`, `efConstruction=200`), search params `ef=64`  
- `notes_meta` (опц.): `note_id`/`title` для быстрых «см. также».

### Файловая система
- Vault:
```

vault/
00\_MOC/topics\_index.md
10\_Notes/<slug>.md

```
- Формат .md: YAML (title, created, tags, source_*, topic_id), тело (summary, Тезисы, Применение, Источники, См. также).

---

## 5) REST API (кратко)

- `POST /ingest/text` — `{text, source_url?, author?, dt?, channel?}` → `{notes:[{id,title,content}]}`
- `GET /notes` — список заметок  
- `GET /notes/{id}` — содержимое (md/мета)  
- `POST /search` — `{query, k?}` → `{answer_md, items:[{id,title,url,snippet}]}`  
- `GET /export/zip` — архив vault  
- `POST /telegram/webhook/<secret>` — приём апдейтов

---

## 6) Telegram Bot + Mini App

**Бот:**
- Команды: `/start`, `/mode` (1:1 или группировать), `/zip`
- Поток: пересылка сообщений → буферизация → `/ingest/text` → ссылки/кнопки

**Mini App (Next.js):**
- Страницы: список заметок, просмотр, поиск
- Кнопки: «Download ZIP» (→ `/export/zip`), «Open in Obsidian» (`obsidian://...`)
- Auth: Telegram WebApp init data (подпись проверять на бэкенде)

---

## 7) Пайплайны

### Ingest (универсальный: и короткие посты, и длинные тексты)
1) **Normalized input:** склеить/очистить базово (опционально).
2) **LLM (5-structured) → insights JSON** (см. промпты ниже).
3) Для каждого insight: **LLM (5-structured) → Markdown** (YAML+тело) → сохранить на FS.
4) **Chunking**:  
 - Короткие посты: 1 чанк (или 1–2 по заголовкам).  
 - Длинные: по заголовкам/абзацам, 200–500 символов на чанк.
5) **Embeddings** (`BGE-M3`) → `Milvus.upsert`.

### Search (RAG)
1) `embed(query)` → `Milvus.search(k=30)`  
2) отбор 5–8 релевантных сниппетов (+ ссылки)  
3) **LLM (5-nano)** → «ответ только из CONTEXT» (см. промпты)  
4) вернуть `answer_md` + список

---

## 8) Промпты (расширенные, готовые)

> **Правила общие:**  
> - На JSON-шаге **возвращать ТОЛЬКО JSON** (никаких комментариев).  
> - На Markdown-шаге **возвращать ТОЛЬКО один Markdown-документ**.  
> - RU/EN — распознавать автоматически, сохранять оригинальные термины.  
> - Не выдумывать факты; при неопределённости — явно помечать.

### 8.1. Разбиение на инсайты (короткие посты и длинные тексты)
**system (5-structured)**  
```

Ты — редактор знаний. Выделяй "чистое знание" из входного текста разной длины:
— короткие посты: 1–3 компактных insights;
— длинные тексты: 5–30 insights, объединённых по смыслу.
Каждый insight — атомная единица знания (1 мысль/правило/шаг).
Удаляй рекламу/воду, сохраняй важные caveats.

Строго верни JSON по схеме:
{
"insights": \[
{
"id": "i-<uuid-like>",
"title": "≤80 символов",
"summary": "1–3 предложения сути",
"bullets": \["атомный тезис 1", "атомный тезис 2", "..."],
"tags": \["до 5 коротких тегов"],
"confidence": 0.0..1.0
}
]
}
Никаких комментариев вне JSON.

```

**user**  
```

Текст:
<<<
{{RAW\_TEXT}}

> > >

Метаданные (опц): source\_url={{URL}}, author={{AUTHOR}}, dt={{DATETIME}}, channel={{CHANNEL}}
Задача: верни JSON по схеме. Если текста мало — верни 1–2 insights.

```

### 8.2. Тематическая группировка (опционально на MVP)
**system (5-structured)**  
```

Ты — куратор. Сгруппируй список инсайтов по 10–30 темам.
Верни JSON:
{
"topics":\[
{"topic\_id":"t-<id>","title":"название темы","desc":"1–2 предложения",
"insight\_ids":\["i-1","i-2","..."]}
],
"orphans":\["i-..."]
}
Без комментариев вне JSON.

```

**user**  
```

Инсайты (id, title, summary):
<<<
{{LIST\_OF\_INSIGHTS}}

> > >

Сгруппируй и верни JSON.

```

### 8.3. Генерация Obsidian-заметки из инсайта
**system (5-structured)**  
```

Ты — генератор Obsidian-заметок. Верни ровно ОДИН Markdown-документ.
Требования:

* YAML: title, created (ISO), tags\[], source\_url?, source\_author?, source\_dt?, topic\_id?
* Тело:

  * 3–5 предложений описания (суть из summary)
  * Раздел "Тезисы": маркдаун-список из bullets (каждый — 1 факт/правило)
  * (опц) "Применение": когда и как использовать
  * "Источники": список ссылок (если есть source\_url)
  * (опц) "См. также": до 5 \[\[Заголовок]] из предоставленного списка candidates
    Никаких комментариев вне Markdown.
    Строго сохраняй смысл, не выдумывай факты.

```

**user**  
```

Данные:
title="{{INSIGHT.title}}"
summary="{{INSIGHT.summary}}"
bullets={{INSIGHT.bullets}}
tags={{INSIGHT.tags}}
meta: source\_url={{URL}}, source\_author={{AUTHOR}}, source\_dt={{DATETIME}}, topic\_id={{TOPIC\_ID}}
Кандидаты для "См. также": {{CANDIDATE\_TITLES\_JSON\_ARRAY}}
Сгенерируй один Markdown.

```

### 8.4. MOC (карта содержания) по темам (опционально)
**system (5-structured)**  
```

Ты — редактор MOC. Верни один Markdown с оглавлением по темам.
Для каждой темы: "## {{title}}" и список "- \[\[NoteTitle]] — 1 строка описания".
Без комментариев вне Markdown.

```

**user**  
```

Темы и заметки:
{{TOPICS\_JSON}}
Сгенерируй один Markdown MOC.

```

### 8.5. Автолинки «См. также» (если нет эмбеддингов)
**system (5-structured)**  
```

Ты — помощник связей. По заголовку/summary текущей заметки выбери до 5 релевантных из списка кандидатов.
Верни JSON: {"related\_titles":\["...", "..."]} без комментариев.

```

**user**  
```

Текущая заметка: title="{{CUR\_TITLE}}", summary="{{CUR\_SUMMARY}}"
Кандидаты: {{ALL\_TITLES\_JSON\_ARRAY}}
Верни JSON.

```

### 8.6. Ответ в поиске (RAG, 5-nano)
**system (5-nano)**  
```

Ты — ассистент базы заметок. Отвечай ТОЛЬКО по CONTEXT (список фрагментов).
Если ответа нет — скажи "не нашёл в базе".
В конце дай раздел "См. также" со списком до 5 заметок (title → ссылка).
Верни Markdown.

```

**user**  
```

QUERY: {{user\_query}}
CONTEXT:

1. \[{{note\_title}}] {{snippet}} ({{url}})
2. ...
   Сформируй краткий, точный ответ только из CONTEXT.

```

---

## 9) Критерии готовности (DoD)

- `docker compose up -d --build` поднимает `api`, `miniapp`, `milvus`, `postgres`.
- `POST /ingest/text`:
  - **Короткий пост** → создаётся 1 заметка (или 1–2 при наличии явных подтем).
  - **Длинный ввод** (≥ 5k символов) → создаётся 5–30 заметок по смысловым инсайтам.
  - Заметки на FS (Markdown+YAML), проиндексированы в Milvus (chunking:
    - короткие: 1–2 чанка;  
    - длинные: 200–500 символов на чанк).
- `POST /search` возвращает осмысленный `answer_md` с «См. также».
- Mini App отображает список заметок, просмотр, поиск, «Download ZIP», «Open in Obsidian».
- Бот обрабатывает пересланные сообщения: 1) короткие — сразу заметка, 2) длинные — набор заметок.
- **Критерий разбиения:** при длинном вводе итоговые инсайты/заметки должны быть:
  - атомарными (1 основная мысль/правило на заметку),
  - самодостаточными (читабельны отдельно),
  - связанными («См. также» присутствует там, где есть тематическая близость).

---

## 10) Предусмотреть удобное масштабирование для новых функций в будущем

- **Планируется** интеграция **транскрибации видео** и **чтения текста с фото (OCR)**, обе задачи — через **OpenAI модели** по **Replicate API**.  
- В API зарезервировать эндпоинты `POST /ingest/video` и `POST /ingest/image` (без реализации сейчас).

---

## 11) Развёртывание (кратко)

- Заполнить `.env` (TELEGRAM_BOT_TOKEN, REPLICATE_API_TOKEN, MILVUS_URI, PG creds, VAULT_DIR).
- `docker compose up -d --build`
- Настроить Telegram webhook: `https://<domain>/telegram/webhook/<secret>`

---

## 12) Заметки по выбору технологий

- **Mini App:** по требованиям Telegram это WebApp (HTML/JS).   
- **PostgreSQL:** использовать для пользователей/метаданных/сессий. Текст заметок — на FS.  
- **Milvus:** только векторы/поиск. Индекс HNSW на MVP.

---
```
