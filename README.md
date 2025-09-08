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

## Зависимости
- Docker
- Docker Compose
- `REPLICATE_API_TOKEN` — токен для LLM из replicate.com
- `TELEGRAM_BOT_TOKEN` — токен Telegram‑бота
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
2. Соберите и запустите сервисы:
   ```bash
   docker compose up -d --build
   ```
   Milvus в `docker-compose.yml` использует встроенные Etcd, MinIO и Pulsar.
   Это исключает зависимость от внешних сервисов и предотвращает ошибки вида
   `find no available datacoord` при старте контейнера.

### Настройка Telegram webhook

```bash
curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=https://<domain>/telegram/webhook/<secret>"
```

### Минимально рекомендуемая конфигурация VM

- Ubuntu 24.04 LTS
- 2 vCPU
- 8 GB RAM
- 20 GB свободного места на диске

## Примеры запросов
### POST /ingest/text
```bash
curl -X POST http://localhost:8000/ingest/text \
  -H 'Content-Type: application/json' \
  -d '{"text": "Пример заметки"}'
```

### POST /search
```bash
curl -X POST http://localhost:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "что такое docker"}'
```

## План масштабирования
- Выделить воркеров для тяжёлой индексации и фоновых задач.
- Добавить ingest-эндпоинты `POST /ingest/video` и `POST /ingest/image` для новых типов данных.

## Тестирование и отладка
Подробные инструкции по установке зависимостей, запуску тестов и работе с Docker находятся в [TESTING.md](TESTING.md).
