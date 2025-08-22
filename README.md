# BaseKnowledge

## Зависимости
- Docker
- Docker Compose
- `REPLICATE_API_TOKEN`
- `TELEGRAM_BOT_TOKEN`
- Python-зависимости образа API: `fastapi`, `uvicorn[standard]`, `python-telegram-bot`,
  `replicate`, `requests`, `sqlalchemy`, `pydantic-settings`, `psycopg[binary]`,
  `pymilvus`, `alembic`

## Запуск через Docker Compose
1. Скопируйте `.env.example` в `.env` и заполните переменные.
2. Запустите сервисы командой:
   ```bash
   docker compose up -d --build
   ```
3. Настройте Telegram webhook:
   ```bash
   curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=https://<domain>/telegram/webhook/<secret>"
   ```

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

