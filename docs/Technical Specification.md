# Technical Specification → TODO (v1.1)

Ниже — перечень задач/требований по областям с отметкой статуса и кратким комментарием по текущему состоянию репозитория.

## 0) Цели
- [x] Принимать разные тексты → Obsidian‑заметки с автоссылками и MOC. Комментарий: реализовано пайплайном IngestText + LLM (libs/usecases/ingest_text.py, libs/llm/*).
- [x] Поиск (RAG) с LLM‑ответом. Комментарий: реализовано (libs/usecases/search.py, libs/rag/vector_index.py).
- [x] Низкое трение: бот, Mini App, ZIP. Комментарий: есть бот (apps/bot), Mini App (apps/miniapp), экспорт /export/zip.

## 1) Архитектура и сервисы
- [x] FastAPI‑сервис (api). Комментарий: эндпоинты ingest/search/notes/export/webhook/health в apps/api/main.py.
- [x] Mini App (Next.js). Комментарий: список/просмотр/поиск, интеграция с API через /api (apps/miniapp).
- [x] Telegram Bot. Комментарий: polling, режимы One‑to‑One/Curate, буферизация, ссылки (apps/bot/main.py).
- [x] PostgreSQL. Комментарий: метаданные хранятся через SQLAlchemy (libs/db/*).
- [x] Milvus (vector store). Комментарий: libs/rag/vector_index.py, создание/валидация коллекции chunks.
- [ ] Выделенный worker/очередь. Комментарий: не реализовано, всё синхронно в API/боте.

## 2) Данные и хранилища
- [x] Vault на ФС для Markdown. Комментарий: libs/storage/notes_storage.py (YAML‑фронтматтер, кросс‑ссылки, ZIP).
- [x] Автоинициализация/доведение схемы БД. Комментарий: init_db() добавляет недостающие колонки/индексы (libs/db/database.py).
- [x] Таблицы users/notes/chunks. Комментарий: см. модели в libs/db/models.py.
- [ ] Коллекция notes_meta в Milvus. Комментарий: интерфейс зарезервирован, по умолчанию не создаётся/не используется.

## 3) LLM и эмбеддинги (Replicate)
- [x] Извлечение инсайтов (gpt‑5‑structured). Комментарий: generate_structured_notes().
- [x] Группировка по темам. Комментарий: group_topics() + запись topic_id в метаданные.
- [x] Рендеринг заметки Markdown. Комментарий: render_note_markdown() (включая кандидатов «См. также»).
- [x] Автоссылки/«См. также». Комментарий: LLM даёт кандидатов; дополнительно NotesStorage пересобирает ссылки по тэгам.
- [x] Генерация MOC. Комментарий: generate_moc() → 00_MOC/topics_index.md.
- [x] Эмбеддинги через Replicate. Комментарий: libs/llm/embeddings_provider.py (батчи/кэш/валидация dim).
- [x] VectorIndex (Milvus). Комментарий: ensure schema, upsert_chunks() и search().

## 4) API и эндпоинты
- [x] POST /ingest/text. Комментарий: создаёт заметки, индексирует чанки, 201 с данными.
- [ ] POST /ingest/video. Комментарий: зарезервировано (501 Not Implemented).
- [ ] POST /ingest/image. Комментарий: зарезервировано (501 Not Implemented).
- [x] POST /search. Комментарий: RAG‑поиск, answer_md + items.
- [x] GET /notes, GET /notes/{id}. Комментарий: список и содержимое заметок из vault.
- [x] GET /export/zip. Комментарий: экспорт всего vault.
- [x] GET /health. Комментарий: health‑проверка контейнера API.
- [x] POST /telegram/webhook/{secret}. Комментарий: валидация TELEGRAM_WEBHOOK_SECRET, разбиение длинных сообщений.

## 5) Telegram Bot
- [x] /start, /mode (переключатель). Комментарий: RU/EN сообщения, inline‑кнопка «Process now».
- [x] Режим Curate: буферизация 60s, дедуп по хешу. Комментарий: сбор и последующая отправка объединённого текста в API.
- [x] Обработка ошибок/ответов API. Комментарий: различение 4xx/5xx, developer info.
- [x] Ссылки на Mini App и ZIP. Комментарий: строятся из PUBLIC_URL.

## 6) Mini App (Next.js)
- [x] Страницы /, /search, /notes/[id]. Комментарий: список, просмотр, поиск, ReactMarkdown.
- [x] Аутентификация: X‑Telegram‑Init‑Data. Комментарий: прокидывается из Telegram WebApp (apps/miniapp/lib/telegram.ts, lib/api.ts).
- [x] Бандл и рантайм. Комментарий: Dockerfile, переменная PUBLIC_URL учитывается при билде.
- [~] Локализация RU/EN. Комментарий: базовые строки в UI — EN; бот — RU/EN; полноценной i18n нет.

## 7) Безопасность и доступ
- [x] Проверка initData (HMAC) для Mini App. Комментарий: current_user() в apps/api/main.py.
- [x] Сервисный доступ по X‑Bot‑Api‑Token. Комментарий: позволяет боту/скриптам вызывать API без initData.
- [ ] Квоты/лимиты. Комментарий: не реализованы; при росте — добавить rate‑limit/квоты в БД.

## 8) CI/CD и деплой
- [x] CI: pytest + lint Mini App. Комментарий: job test в .github/workflows/cicd.yml.
- [x] CD: сборка/пуш образов в GHCR. Комментарий: job build-and-push для api, bot, miniapp.
- [x] Deploy: SSH на сервер и deploy.sh. Комментарий: job deploy (ветка main).
- [x] Compose на сервере с образами GHCR. Комментарий: docker-compose.yml (переменные GHCR_NAMESPACE, IMAGE_TAG).
- [x] Nginx + TLS (certbot). Комментарий: конфиги в infra/docker/nginx, инструкция SSL_CERTIFICATE.md.

## 9) Логирование и наблюдаемость
- [x] Единый формат логов. Комментарий: libs/logging.py (формат в стиле Milvus).
- [ ] Метрики/трейсинг. Комментарий: отсутствуют; кандидаты — Prometheus/OpenTelemetry.

## 10) Тестирование
- [x] Unit/Integration тесты (pytest). Комментарий: стаб/mock внешних зависимостей (Milvus/Replicate/Telegram) в tests/.
- [ ] E2E (бот + Mini App). Комментарий: не покрыто.

## 11) Документация
- [x] README с актуальным состоянием. Комментарий: обновлён, включает структуру, API, CI/CD.
- [x] DEPLOYMENT.md, SSL_CERTIFICATE.md. Комментарий: детализируют деплой и выпуск TLS.

## 12) Будущее и зарезервировано
- [ ] /ingest/video, /ingest/image (OCR/ASR через Replicate/OpenAI). Комментарий: эндпоинты есть (501), нужна реализация.
- [ ] Вынос индексации в worker/очередь. Комментарий: снижает нагрузку на API.
- [ ] Хранение vault в S3/облаке (или синхронизация). Комментарий: опционально.
- [ ] Расширение Mini App (темы/MOC, фильтры, i18n). Комментарий: UI улучшения.

—

Примечания по соответствию коду:
- Авторитетные места: apps/api/main.py, libs/usecases/*, libs/llm/*, libs/rag/*, libs/db/*, libs/storage/*.
- CI/CD: .github/workflows/cicd.yml, deploy.sh, docker-compose.yml, infra/docker/*.
- Переменные окружения: .env.example (см. также libs/core/settings.py).

