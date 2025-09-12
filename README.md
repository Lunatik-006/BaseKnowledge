# BaseKnowledge

BaseKnowledge — сервис для структурирования личных заметок и поиска знаний. Он индексирует текст, сохраняет заметки и предоставляет API и Telegram‑бота для быстрого поиска.

## Возможности
- ingest текстовых заметок через REST и Telegram‑бота;
- поиск по базе знаний с использованием векторного индекса;
- экспорт сохранённых заметок в архив.

## Структура репозитория
- `apps/api` — FastAPI‑приложение с REST‑эндпоинтами;
- `apps/bot` — Telegram‑бот для отправки заметок;
- `apps/miniapp` — клиентское мини‑приложение;
- `libs` — общие библиотеки и сервисы.

## Структура базы данных
Сервис использует PostgreSQL. При запуске API структура БД автоматически создаётся и дополняется.

- **users** — пользователи
  - `id` — строковый первичный ключ;
  - `telegram_id` — уникальный идентификатор Telegram;
  - `created_at` — время создания записи.
- **notes** — заметки
  - `id` — строковый первичный ключ;
  - `title` — заголовок заметки;
  - `tags` — массив строк;
  - `topic_id` — опциональный идентификатор темы;
  - `created_at` — время создания;
  - `file_path` — путь к Markdown‑файлу;
  - `source_url` — исходный URL;
  - `author` — автор заметки;
  - `dt` — дата исходного материала;
  - `channel` — источник (например, Telegram).
- **chunks** — фрагменты заметок
  - `id` — строковый первичный ключ;
  - `note_id` — внешний ключ на `notes.id`;
  - `pos` — порядковый номер фрагмента;
  - `anchor` — опциональный якорь внутри заметки.

## Зависимости
- Docker
- Docker Compose
- `REPLICATE_API_TOKEN` — токен для LLM из replicate.com
- `TELEGRAM_BOT_TOKEN` — токен Telegram‑бота
- `BOT_API_TOKEN` — сервисный токен для запросов от бота
- `LOG_LEVEL` — уровень логирования (например, DEBUG, INFO, WARNING, ERROR)
- Python-зависимости образа API: `fastapi`, `uvicorn[standard]`, `python-telegram-bot`, `replicate`, `requests`, `sqlalchemy`, `pydantic-settings`, `psycopg[binary]`, `pymilvus`, `alembic`

## Развёртывание на Ubuntu 24.04 через Docker Compose

### Установка Docker и Docker Compose

1. Обновите индекс пакетов и установите зависимости:
   ```bash
   sudo apt update
   sudo apt install -y ca-certificates curl gnupg
   ```
2. Добавьте официальный репозиторий Docker:
   ```bash
   sudo install -m 0755 -d /etc/apt/keyrings
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
   echo \
     "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
     $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | \
     sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   ```
3. Установите Docker Engine и Docker Compose:
   ```bash
   sudo apt update
   sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   ```
4. Добавьте пользователя в группу `docker`:
   ```bash
   sudo usermod -aG docker $USER
   newgrp docker
   ```

### Конфигурация окружения и запуск

1. Скопируйте `.env.example` в `.env` и заполните переменные:
   ```bash
   cp .env.example .env
   nano .env
   ```
2. При необходимости отредактируйте `config/prompts.yaml`. Этот файл будет смонтирован в контейнер API по пути `/app/config/prompts.yaml`.
3. Соберите и запустите сервисы:
   ```bash
   docker compose up -d --build
   ```
   Milvus v2.6.1 в `docker-compose.yml` использует встроенные Etcd, MinIO и
   очередь сообщений RocksMQ по умолчанию. Переменные окружения
   `ETCD_USE_EMBEDDED` и `MINIO_USE_EMBEDDED` исключают зависимость от
   внешних сервисов и предотвращают ошибки вида `find no available
   datacoord` при старте контейнера.

### Настройка логирования

Все сервисы выводят логи в формате `[YYYY/MM/DD HH:MM:SS.mmm +00:00] [LEVEL] message`.
Уровень логирования задаётся переменной окружения `LOG_LEVEL`.
Добавьте её в `.env` или передайте при запуске Docker Compose:

```bash
LOG_LEVEL=DEBUG docker compose up
```

## Создание таблиц вручную

Если хотите заранее создать таблицы в базе (без ожидания автосоздания схемы на старте API), выполните один из вариантов ниже.

Вариант A: через контейнер `postgres` (docker compose)

```bash
docker compose exec -T postgres bash -lc 'cat <<'\''SQL'\'' | \
  psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-baseknowledge}" -v ON_ERROR_STOP=1
-- Основные таблицы
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  telegram_id INTEGER UNIQUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notes (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  tags TEXT[] DEFAULT ARRAY[]::TEXT[],
  topic_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  file_path TEXT NOT NULL,
  source_url TEXT,
  author TEXT,
  dt TIMESTAMPTZ,
  channel TEXT
);

CREATE TABLE IF NOT EXISTS chunks (
  id TEXT PRIMARY KEY,
  note_id TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
  pos INTEGER NOT NULL,
  anchor TEXT
);

-- Рекомендуемые индексы
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE schemaname = current_schema() AND indexname = 'ix_chunks_note_pos'
  ) THEN
    CREATE INDEX ix_chunks_note_pos ON chunks (note_id, pos);
  END IF;
END $$;
SQL'
```

После создания таблиц можно запускать весь стек (`docker compose up -d`). Если в будущем в моделях появятся новые поля, API на старте добавит недостающие колонки автоматически.

## Настройка БД (drop‑in)

По умолчанию `docker-compose.yml` поднимает контейнер `postgres` и создаёт базу с именем из `POSTGRES_DB` при первом запуске. Авто‑создание самой базы в коде удалено: теперь код лишь гарантирует наличие схемы (таблиц/колонок) в уже существующей базе при старте API.

Если используете встроенный `postgres`:

- Убедитесь, что в `.env` заданы:
  - `POSTGRES_USER=postgres`
  - `POSTGRES_PASSWORD=postgres`
  - `POSTGRES_DB=baseknowledge`

- Поднимите сервис БД:

  ```bash
  docker compose up -d postgres
  ```

- Создайте БД (идемпотентно: создаст, только если её нет):

  ```bash
  docker compose exec -T postgres bash -lc '
    psql -U "${POSTGRES_USER:-postgres}" -tAc "SELECT 1 FROM pg_database WHERE datname = ''${POSTGRES_DB:-baseknowledge}''" | grep -q 1 \
    || psql -U "${POSTGRES_USER:-postgres}" -c "CREATE DATABASE \"${POSTGRES_DB:-baseknowledge}\";"
  '
  ```

- Запустите остальные сервисы:

  ```bash
  docker compose up -d
  ```

API на старте выполнит проверку и создаст недостающие таблицы/колонки в этой базе.

Проверка:

- `curl -f http://localhost:8000/health` (или через Nginx: `https://<домен>/api/health`)
- Авторизация сервисным токеном (должна вернуть JSON с `telegram_id: 0`):

  ```bash
  curl -s -H "X-Bot-Api-Token: $BOT_API_TOKEN" http://localhost:8000/auth/telegram
  ```

После этого запускайте контейнеры. API сам доведёт схему до нужного состояния.

После этого `docker compose logs` покажет единообразные сообщения.

### Ручной запуск Postgres «с нуля» (чтобы сработал init-скрипт)

В репозитории добавлен init-скрипт (`infra/docker/postgres/initdb/01-create-db.sh`),
который при первом старте пустого тома создаёт базу c именем из `POSTGRES_DB`.
Скрипты в `/docker-entrypoint-initdb.d` выполняются только при ИНИЦИАЛИЗАЦИИ
данных (когда каталог данных пуст). Если у вас ранее создавался том и база не
создалась автоматически, запустите Postgres «с нуля»:

```bash
# Остановить сервисы и удалить тома (включая postgres_data)
docker compose down -v

# Поднять только Postgres и дождаться его готовности
docker compose up -d postgres
docker compose ps

# (необязательно) проверить, что база создана init-скриптом
docker compose exec -T postgres bash -lc \
  'psql -U "${POSTGRES_USER:-postgres}" -tAc 
   "SELECT 1 FROM pg_database WHERE datname = ''${POSTGRES_DB:-baseknowledge}''"'

# Запустить остальные сервисы
docker compose up -d
```

Примечания:
- Имя базы берётся из `.env` (`POSTGRES_DB`).
- В API строка подключения теперь формируется из `.env` (см. .env.example),
  поэтому имя БД единообразно во всех сервисах. Можно задать и целиком
  `POSTGRES_URI` — он перекроет сборку URI из компонент.

### Настройка Telegram webhook

```bash
curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=https://<domain>/telegram/webhook/<secret>"
```

### Минимально рекомендуемая конфигурация VM

- Ubuntu 24.04 LTS
- 2 vCPU
- 8 GB RAM
- 20 GB свободного места на диске

## План масштабирования
- Выделить воркеров для тяжёлой индексации и фоновых задач.
- Добавить ingest-эндпоинты `POST /ingest/video` и `POST /ingest/image` для новых типов данных.

## Тестирование и отладка
Подробные инструкции по установке зависимостей, запуску тестов и работе с Docker находятся в [TESTING.md](TESTING.md).

## Пайплайн - наглядно

```mermaid
graph TD
  %% ==== Пользователь и источники ====
  U[Пользователь] -->|пересылает посты / длинный текст| TB[Telegram Bot]
  U -.->|открывает| MA[Mini App (Telegram WebApp)]

  %% ==== Бот: приём и буферизация ====
  subgraph TG[Telegram слой]
    TB -->|режим One-to-One / Curate| BUF[Буфер сессии\n(склейка сообщений, таймаут)]
    TB -->|вебхук| API[/FastAPI: /telegram/webhook/…/]
  end

  BUF -->|готово к обработке| API

  %% ==== Бэкенд: Ingest ====
  subgraph BE[Backend (FastAPI)]
    API -->|/ingest/text\n(raw text + meta)| UC[UseCase: IngestText]
    UC -->|prompt 8.1 → JSON инсайтов| LLM1[(Replicate → openai/gpt-5-structured)]
    LLM1 --> INS[Insights JSON]

    %% Генерация заметок
    INS -->|по каждому insight| LLM2[(Replicate → gpt-5-structured)]
    LLM2 --> MD[Markdown с YAML\nObsidian-нативно]

    %% Хранилище заметок
    MD --> FS[(Файловая система\nvault/…/*.md)]
    MD -->|метаданные| PG[(PostgreSQL\nusers/notes/chunks_meta)]

    %% Индексация
    MD --> CHK[Чанкинг 200–500 симв.\nзаголовки/абзацы]
    CHK --> EMB[(Replicate → BGE-M3\nэмбеддинги)]
    EMB --> MIL[(Milvus\nколлекция chunks)]
    CHK -->|anchor/pos| PG
  end

  %% ==== Mini App: просмотр и экспорт ====
  subgraph UI[Mini App (Next.js WebApp)]
    MA -->|/notes, /notes/{id}| API
    API -->|md + meta| VIEW[Рендер Markdown\n(YAML, «Тезисы», «См. также»)]
    MA -->|Download| ZIP[/FastAPI: /export/zip/]
    MA -->|Open in Obsidian| OURI[obsidian://advanced-uri…]
  end

  FS -->|ZIP| ZIP
  VIEW --> REL[«См. также»\n(вики-ссылки)]
  REL --> VIEW

  %% ==== Поиск (RAG) ====
  subgraph SRCH[Поиск]
    MA -->|/search (query)| API
    API --> QEMB[(Replicate → BGE-M3\nэмбеддинг запроса)]
    QEMB -->|top-K| MIL
    MIL --> TOPK[Top-K сниппетов\n(note_id, snippet, url)]
    TOPK --> LLM3[(Replicate → openai/gpt-5-nano)]
    LLM3 --> ANSW[Markdown-ответ\nТОЛЬКО из CONTEXT + «См. также»]
    ANSW --> MA
  end

  %% ==== Обновление MOC / связей ====
  INS -->|опц. группировка| MOC[MOC (карта содержания)]
  MOC --> FS

  %% ==== Будущее (зарезервировано) ====
  subgraph FUTURE[Будущее (зарезервировано в API)]
    YT[YouTube/Видео] -.->|/ingest/video| API
    IMG[Фото с текстом] -.->|/ingest/image (OCR)| API
  end
```

## Документация (docs)
- Гайд по Replicate API: `docs/replicate-gpt5-python-how-to-use.md` (ссылки на схемы входа/выхода и промпт‑конфиг)
- Схемы моделей:
  - `docs/gpt-5-nano-input-schema.json`
  - `docs/gpt-5-structured-input-schema.json`
  - `docs/gpt-5-output-schema.json`
- Техническая спецификация: `docs/Technical Specification.md`
- Деплой: `docs/DEPLOYMENT.md`
- TLS/сертификат: `docs/SSL_CERTIFICATE.md`
