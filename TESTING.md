# Руководство по тестированию и отладке

Этот документ описывает процесс подготовки среды, запуска тестов и отладки проекта **BaseKnowledge**.

## Установка зависимостей
1. Создайте виртуальное окружение и активируйте его:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Установите необходимые пакеты (совпадает с зависимостями из Dockerfile):
   ```bash
   pip install fastapi uvicorn[standard] python-telegram-bot replicate \
       requests sqlalchemy pydantic-settings "psycopg[binary]" pymilvus==2.6.1 alembic pytest
   ```

## Переменные окружения
1. Скопируйте файл `.env.example` в `.env`:
   ```bash
   cp .env.example .env
   ```
2. Заполните значения в следующем порядке:
   1. `TELEGRAM_BOT_TOKEN`
   2. `REPLICATE_API_TOKEN`
   3. `MILVUS_URI`
   4. `POSTGRES_URI`
   5. `VAULT_DIR`
   6. `NEXT_PUBLIC_API_URL`

## Запуск юнит‑тестов и проверка формата
Запустите `pytest` из корня репозитория:
```bash
pytest
```
`pytest` выполняет юнит‑тесты и проверяет соответствие кода ожидаемому формату.

## Запуск Docker Compose и API
1. Соберите и запустите контейнеры:
   ```bash
   docker compose up -d --build
   ```
2. Остановите контейнеры:
   ```bash
   docker compose down
   ```
3. Локальный запуск API без Docker:
   ```bash
   uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Логирование и отладка
- Просмотр логов всех сервисов:
  ```bash
  docker compose logs -f
  ```
- Просмотр логов конкретного сервиса (например, API):
  ```bash
  docker compose logs -f api
  ```
- Для подробных логов при локальном запуске используйте флаг `--log-level debug`:
  ```bash
  uvicorn apps.api.main:app --log-level debug
  ```
- В тестах можно выводить дополнительную информацию через `pytest -vv` или `print`/`logging`.

