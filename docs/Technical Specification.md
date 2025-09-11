# Technical Specification → TODO (v2.1)

Ниже — перечень задач/требований по областям с отметкой статуса и кратким комментарием по текущему состоянию репозитория.

# Technical Specification → TODO (v1.1)

Ниже — перечень задач/требований по областям с отметкой статуса и кратким комментарием по текущему состоянию репозитория.

## 0) Цели
- [x] Принимать разные тексты → Obsidian-заметки с автоссылками и MOC. Комментарий: реализовано пайплайном IngestText + LLM (libs/usecases/ingest_text.py, libs/llm/*).
- [x] Поиск (RAG) с LLM-ответом. Комментарий: реализовано (libs/usecases/search.py, libs/rag/vector_index.py).
- [x] Низкое трение: бот, Mini App, ZIP. Комментарий: есть бот (apps/bot), Mini App (apps/miniapp), экспорт /export/zip.

## 1) Архитектура и сервисы
- [x] FastAPI-сервис (api). Комментарий: эндпоинты ingest/search/notes/export/webhook/health в apps/api/main.py.
- [x] Mini App (Next.js). Комментарий: список/просмотр/поиск, интеграция с API через /api (apps/miniapp).
- [x] Telegram Bot. Комментарий: polling, режимы One-to-One/Curate, буферизация, ссылки (apps/bot/main.py).
- [x] PostgreSQL. Комментарий: метаданные хранятся через SQLAlchemy (libs/db/*).
- [x] Milvus (vector store). Комментарий: libs/rag/vector_index.py, создание/валидация коллекции chunks.
- [ ] Выделенный worker/очередь. Комментарий: не реализовано, всё синхронно в API/боте.
- [ ] **W1:** Добавить use-case `build_course` (libs/usecases/build_course.py): вход — `user_id`, опц. `note_ids`, `target_level` {beginner|intermediate|advanced}, `tone` {pragmatic|motivational|charismatic}, `lang` {ru|en}; выход — структура курса (модули/уроки), запись артефактов в vault. Комментарий: сервисный класс + оркестрация LLM/кластеризации.
- [ ] **W1:** Модуль генерации mind-map (libs/storage/markmap.py) → `90_Artifacts/Course_Mindmap.md` (fenced-код для markmap). Комментарий: детерминированная сборка из outline.
- [ ] **W1:** Пакетировщик артефактов (libs/storage/export_kit.py) — сбор `Course_Outlines.md`, `Checklists.md`, `Workbook.md`, `Quiz_Bank.md`, `Content_Calendar_14d.md` и размещение в `90_Artifacts/`. Комментарий: переиспользовать существующий ZIP-экспорт.

## 2) Данные и хранилища
- [x] Vault на ФС для Markdown. Комментарий: libs/storage/notes_storage.py (YAML-фронтматтер, кросс-ссылки, ZIP).
- [x] Автоинициализация/доведение схемы БД. Комментарий: init_db() добавляет недостающие колонки/индексы (libs/db/database.py).
- [x] Таблицы users/notes/chunks. Комментарий: см. модели в libs/db/models.py.
- [ ] Коллекция notes_meta в Milvus. Комментарий: интерфейс зарезервирован, по умолчанию не создаётся/не используется.
- [ ] **W1:** Структура vault для курса: создать/гарантировать наличие `00_Overview.md`, каталога `01_Modules/*`, каталога `90_Artifacts/*`, файла `99_Metadata/project.json`. Комментарий: расширить NotesStorage (идемпотентные операции).
- [ ] **W1:** Индекс источников `90_Artifacts/Sources_Index.md` (агрегация `source_url`, `author`, `dt`, `channel` из `notes`). Комментарий: использовать уже существующие поля модели notes.
- [ ] **W1:** Расширить модель `users` JSON-полем `prefs` (target_level/tone/lang); init_db добавит колонку при старте. Комментарий: хранить пользовательские настройки для генерации.

## 3) LLM и эмбеддинги (Replicate)
- [x] Извлечение инсайтов (gpt-5-structured). Комментарий: generate_structured_notes().
- [x] Группировка по темам. Комментарий: group_topics() + запись topic_id в метаданные.
- [x] Рендеринг заметки Markdown. Комментарий: render_note_markdown() (включая кандидатов «См. также»).
- [x] Автоссылки/«См. также». Комментарий: LLM даёт кандидатов; дополнительно NotesStorage пересобирает ссылки по тэгам.
- [x] Генерация MOC. Комментарий: generate_moc() → 00_MOC/topics_index.md.
- [x] Эмбеддинги через Replicate. Комментарий: libs/llm/embeddings_provider.py (батчи/кэш/валидация dim).
- [x] VectorIndex (Milvus). Комментарий: ensure schema, upsert_chunks() и search().
- [ ] **W1:** Реализовать `generate_course_outline()` (модули/уроки) на основе имеющихся эмбеддингов/`group_topics()` + эвристики размеров: 3–8 модулей, в каждом 3–6 уроков. Комментарий: контролируемый токен-лимит, детерминизм.
- [ ] **W1:** `generate_learning_outcomes(module)` (3–5 outcomes) и `extract_keywords(module)` (ключевые термины) с привязкой к источникам. Комментарий: только из контента.
- [ ] **W1:** Слой стиля текста (`tone`, `target_level`, `lang`) — пост-процессинг названий и описаний без изменения структуры. Комментарий: параметризация промптов.
- [ ] **W1:** Кэширование LLM-вызовов (libs/llm/cache.py) с ключом {prompt-hash, model, params}. Комментарий: снижение затрат.

## 4) API и эндпоинты
- [x] POST /ingest/text. Комментарий: создаёт заметки, индексирует чанки, 201 с данными.
- [ ] POST /ingest/video. Комментарий: зарезервировано (501 Not Implemented).
- [ ] POST /ingest/image. Комментарий: зарезервировано (501 Not Implemented).
- [x] POST /search. Комментарий: RAG-поиск, answer_md + items.
- [x] GET /notes, GET /notes/{id}. Комментарий: список и содержимое заметок из vault.
- [x] GET /export/zip. Комментарий: экспорт всего vault.
- [x] GET /health. Комментарий: health-проверка контейнера API.
- [x] POST /telegram/webhook/{secret}. Комментарий: валидация TELEGRAM_WEBHOOK_SECRET, разбиение длинных сообщений.
- [ ] **W1:** POST `/ops/build_course` (только для сервисов с `X-Bot-Api-Token`): вход `{note_ids?: string[], target_level, tone, lang}`; выход — JSON с кратким outline и путями артефактов. Комментарий: вызывает `build_course`.
- [ ] **W1:** GET `/export/kit` — скачать ZIP с артефактами курса (`90_Artifacts/*` + `00_Overview.md`). Комментарий: переиспользовать существующий ZIP-механизм.
- [ ] **W1:** Расширить /ingest/text: если передан `source_url`, извлечь контент сервер-сайд (встроенный фетчер) и сохранить поля `source_url`, `author`, `dt`, `channel`. Комментарий: доп. слой нормализации.

## 5) Telegram Bot
- [x] /start, /mode (переключатель). Комментарий: RU/EN сообщения, inline-кнопка «Process now».
- [x] Режим Curate: буферизация 60s, дедуп по хешу. Комментарий: сбор и последующая отправка объединённого текста в API.
- [x] Обработка ошибок/ответов API. Комментарий: различение 4xx/5xx, developer info.
- [x] Ссылки на Mini App и ZIP. Комментарий: строятся из PUBLIC_URL.
- [ ] **W1:** Команда `/add` — принимает текст или URL и вызывает `POST /ingest/text` (поля: `text?`, `source_url?`, `channel='telegram'`). Комментарий: верификация/ответные статусы.
- [ ] **W1:** Команда `/list` — показывает последние N заметок (заголовки/даты) через `GET /notes`. Комментарий: пагинация.
- [ ] **W1:** Команда `/reset` — очищает буфер текущей сессии Curate (не удаляет БД). Комментарий: подтверждение.
- [ ] **W1:** Команда `/build_course` — вызывает `POST /ops/build_course`, по завершении отвечает сводкой (кол-во модулей/уроков) и инлайн-кнопками: «📦 Скачать KIT» (GET /export/kit), «🔎 Открыть в Mini App». Комментарий: обработка ошибок/таймаут.
- [ ] **W1:** Команда `/settings` — установка `target_level`, `tone`, `lang` (сохранение в `users.prefs`). Комментарий: валидация значений.

## 6) Mini App (Next.js)
- [x] Страницы /, /search, /notes/[id]. Комментарий: список, просмотр, поиск, ReactMarkdown.
- [x] Аутентификация: X-Telegram-Init-Data. Комментарий: прокидывается из Telegram WebApp (apps/miniapp/lib/telegram.ts, lib/api.ts).
- [x] Бандл и рантайм. Комментарий: Dockerfile, переменная PUBLIC_URL учитывается при билде.
- [~] Локализация RU/EN. Комментарий: базовые строки в UI — EN; бот — RU/EN; полноценной i18n нет.
- [ ] **W1:** Кнопка/ссылка «📦 Download Course Kit» на страницах просмотра заметок/списка — ссылка на `GET /export/kit`. Комментарий: учитывать PUBLIC_URL.
- [ ] **W1:** Просмотр артефактов: страница `/artifacts` (список файлов из `90_Artifacts/*`, ссылки на скачивание). Комментарий: простая read-only.

## 7) Безопасность и доступ
- [x] Проверка initData (HMAC) для Mini App. Комментарий: current_user() в apps/api/main.py.
- [x] Сервисный доступ по X-Bot-Api-Token. Комментарий: позволяет боту/скриптам вызывать API без initData.
- [ ] Квоты/лимиты. Комментарий: не реализованы; при росте — добавить rate-limit/квоты в БД.
- [ ] **W1:** Ограничить `/ops/build_course` по `X-Bot-Api-Token` + привязка к `user_id` из заголовка/тела. Комментарий: 403 при отсутствии токена/несоответствии.

## 8) CI/CD и деплой
- [x] CI: pytest + lint Mini App. Комментарий: job test в .github/workflows/cicd.yml.
- [x] CD: сборка/пуш образов в GHCR. Комментарий: job build-and-push для api, bot, miniapp.
- [x] Deploy: SSH на сервер и deploy.sh. Комментарий: job deploy (ветка main).
- [x] Compose на сервере с образами GHCR. Комментарий: docker-compose.yml (переменные GHCR_NAMESPACE, IMAGE_TAG).
- [x] Nginx + TLS (certbot). Комментарий: конфиги в infra/docker/nginx, инструкция SSL_CERTIFICATE.md.
- [ ] **W1:** Обновить образы API/бота: добавить зависимости контент-экстракции (см. ниже), прокинуть новые env при билде. Комментарий: lock-файлы/кэш.
- [ ] **W1:** Автотесты/линты должны запускаться для новых модулей (`build_course`, `export_kit`, bot-команды).

## 9) Логирование и наблюдаемость
- [x] Единый формат логов. Комментарий: libs/logging.py (формат в стиле Milvus).
- [ ] Метрики/трейсинг. Комментарий: отсутствуют; кандидаты — Prometheus/OpenTelemetry.
- [ ] **W1:** Тайминги пайплайна: логировать `ingest_total_ms`, `build_course_total_ms`, счётчик LLM-вызовов/токенов. Комментарий: единый кореляционный `request_id`.

## 10) Тестирование
- [x] Unit/Integration тесты (pytest). Комментарий: стаб/mock внешних зависимостей (Milvus/Replicate/Telegram) в tests/.
- [ ] E2E (бот + Mini App). Комментарий: не покрыто.
- [ ] **W1:** Unit-тесты на `generate_course_outline`, `generate_learning_outcomes`, `markmap` (mock LLM).
- [ ] **W1:** Интеграционные тесты: `POST /ops/build_course` → запись артефактов; `GET /export/kit` → корректный ZIP.
- [ ] **W1:** Тесты бота: `/add` (текст/URL), `/build_course`, `/settings` — мок API.

## 11) Документация
- [x] README с актуальным состоянием. Комментарий: обновлён, включает структуру, API, CI/CD.
- [x] DEPLOYMENT.md, SSL_CERTIFICATE.md. Комментарий: детализируют деплой и выпуск TLS.
- [ ] **W1:** Документировать JSON-контракты `/ops/build_course`, структуру `90_Artifacts/*`, ключи `users.prefs` в README + inline docstring.

## 12) Будущее и зарезервировано
- [ ] /ingest/video, /ingest/image (OCR/ASR через Replicate/OpenAI). Комментарий: эндпоинты есть (501), нужна реализация.
- [ ] Вынос индексации в worker/очередь. Комментарий: снижает нагрузку на API.
- [ ] Хранение vault в S3/облаке (или синхронизация). Комментарий: опционально.
- [ ] Расширение Mini App (темы/MOC, фильтры, i18n). Комментарий: UI улучшения.

---

### Примечания по зависимостям (W1)
- [ ] **API:** добавить `youtube_transcript_api`, `trafilatura` для `source_url`-ингеста (в Dockerfile/requirements). Комментарий: фичи — YT-расшифровка и извлечение текста веб-страниц.
- [ ] **Бот:** приём URL, но обработку контента делаем на стороне API через расширенный `/ingest/text`.

### АСА (Acceptance / DoD) для W1
- [ ] `/add` принимает текст и URL, заметки создаются с заполненными полями `source_url/author/dt/channel`.
- [ ] `/build_course` создаёт outline (≥3 модуля, ≥3 урока/модуль) и артефакты в `90_Artifacts/*`.
- [ ] `/export/kit` отдаёт валидный ZIP со всеми артефактами + `00_Overview.md`.
- [ ] Markmap файл корректно открывается, ссылки внутри vault рабочие.
- [ ] Логи содержат тайминги пайплайна и счётчики LLM-вызовов.
