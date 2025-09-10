# CI/CD — Автоматическое развертывание на сервере (GitHub Actions)

Этот документ описывает полный процесс настройки сервера и репозитория GitHub для автоматического развертывания BaseKnowledge после каждого `git push` в ветку `main`.

## Обзор пайплайна
- CI (job `test`): устанавливает Python-зависимости, запускает `pytest` и линт для MiniApp.
- CD (job `build-and-push`): собирает Docker-образы (`api`, `bot`, `miniapp`) и пушит их в GHCR (`ghcr.io`).
- Deploy (job `deploy`): по SSH выполняет на сервере `deploy.sh` — авторизация в GHCR, `docker compose pull`, `docker compose up -d`, обновление репозитория.

Стек:
- Рантаймы образов `api`/`bot` — многоступенчатые Dockerfile на базе `python:3.11-slim`.
- Образы публикуются в `ghcr.io/<ORG_OR_USER>/baseknowledge-{api,bot,miniapp}`.
- Сервер тянет готовые образы (не билдит локально).

## Требования к серверу
Подойдет Ubuntu 22.04/24.04. Нужны:

- Docker Engine + Docker Compose Plugin:
  - `apt-get update && apt-get install -y ca-certificates curl gnupg`
  - Установить Docker по инструкции из docs.docker.com (официальные репозитории).
- Открытые порты: `80`, `443`, `5432` (если нужен внешний доступ к PostgreSQL — обычно не требуется), `19530`, `9091`, `2379` для Milvus (по необходимости внешнего доступа).
- Домен и DNS-запись на сервер (для Nginx + Let's Encrypt).
- Git (для обновления репозитория на сервере).

## Размещение проекта на сервере (однократно)
1. Подключитесь по SSH и выполните:
   - `sudo usermod -aG docker <your_user>` и перелогиньтесь (чтобы запускать Docker без `sudo`).
   - `mkdir -p /root && cd /root`
   - `git clone https://github.com/<ORG_OR_USER>/BaseKnowledge.git` (или через SSH) в `/root/BaseKnowledge`.
2. Создайте файл `/root/BaseKnowledge/.env`:

   Обязательные переменные:
   - `GHCR_NAMESPACE=<ORG_OR_USER>` — владелец GHCR (совпадает с `github.repository_owner`).
   - `IMAGE_TAG=latest` — тег образов для pull (по умолчанию latest для `main`).
   - `REPLICATE_API_TOKEN=...`
   - `TELEGRAM_BOT_TOKEN=...`
   - `BOT_API_TOKEN=...` — сервис-токен для API-бэкдора из бота.
   - `POSTGRES_USER=postgres`
   - `POSTGRES_PASSWORD=postgres`
   - `POSTGRES_DB=baseknowledge`
   - `LOG_LEVEL=INFO`

   Необязательные (при необходимости):
  - `PUBLIC_URL=https://your.domain` (публичный адрес сайта; API будет доступен по `${PUBLIC_URL}/api`)
   - `TELEGRAM_WEBHOOK_SECRET=...`
   - `MILVUS_URI=http://milvus:19530` (используется по умолчанию внутри контейнеров)

3. Первичная проверка локально на сервере (опционально):
   - `docker compose -f /root/BaseKnowledge/docker-compose.yml pull` (потребуется GHCR доступ; см. следующий раздел)
   - `docker compose -f /root/BaseKnowledge/docker-compose.yml up -d`

## Доступ к GHCR на сервере
Для pull из GHCR нужен токен с правом `read:packages`.

- Создайте в GitHub Personal Access Token (classic) с `read:packages`.
- В репозитории GitHub добавьте secrets:
  - `GHCR_USERNAME` — ваш GitHub логин/организация
  - `GHCR_TOKEN` — PAT с `read:packages`

Скрипт `deploy.sh` на сервере автоматически выполнит `docker login ghcr.io` с этими cred'ами, переданными из Actions.

## Настройка GitHub Secrets
В настройках репозитория добавьте secrets:

- Для пуша образов в GHCR (используется стандартный `${{ secrets.GITHUB_TOKEN }}` — дополнительных не требуется).
- Для деплоя по SSH:
  - `SSH_HOST` — IP/домен сервера
  - `SSH_USER` — пользователь (например, `root`)
  - `SSH_PORT` — порт SSH (по умолчанию `22`)
  - `SSH_KEY` — приватный ключ в формате PEM (соответствующий открытому ключу в `~/.ssh/authorized_keys` сервера)
- Для MiniApp build:
  - `PUBLIC_URL` — публичный URL сайта (например, `https://your.domain`). Клиент обращается к API по адресу `${PUBLIC_URL}/api`.
- Для pull на сервере:
  - `GHCR_USERNAME`, `GHCR_TOKEN` — см. раздел выше

## Поток деплоя после `git push`
1. GitHub Actions запускает workflow `.github/workflows/cicd.yml`.
2. Job `test`:
   - Устанавливает Python deps для API и `aiosqlite` только для тестов.
   - Запускает `pytest` и проверку MiniApp (npm ci + lint).
3. Job `build-and-push`:
   - Собирает Docker-образы `api`, `bot`, `miniapp` из Dockerfile.
   - Публикует в `ghcr.io/<ORG_OR_USER>/baseknowledge-{api,bot,miniapp}:latest` и `:{sha-short}`.
4. Job `deploy` (только для `main`):
   - Подключается по SSH к серверу и запускает `/root/BaseKnowledge/deploy.sh`.
   - Скрипт обновляет git-репозиторий, логинится в GHCR, делает `docker compose pull` и `up -d`.

## Telegram и Webhook
- `TELEGRAM_BOT_TOKEN` обязателен для бота и API-обработчика `/telegram/webhook/{secret}`.
- Опционально задайте `TELEGRAM_WEBHOOK_SECRET` и настройте webhook у Bot API на `https://your.domain/api/telegram/webhook/<secret>` (проксируется через Nginx из `infra/docker/nginx/default.conf`).

## Проверка после деплоя
- API: `curl -f http://<server>:8000/health` или `https://<domain>/health` (если настроен TLS и прокси)
- Bot: логи `docker logs <bot_container>`
- MiniApp: откройте `https://<domain>`

## Частые проблемы
- Нет доступа к GHCR: проверьте `GHCR_USERNAME/GHCR_TOKEN` и права `read:packages`.
- Секреты не заданы: job `deploy` не сможет подключиться по SSH.
- На сервере не обновляется compose-файл: убедитесь, что репозиторий корректно клонирован в `/root/BaseKnowledge` и `deploy.sh` имеет права на git-команды.

## Структура и соответствие
- Dockerfile `infra/docker/api/Dockerfile` и `infra/docker/worker/Dockerfile` — многоступенчатые билды без базового образа.
- `docker-compose.yml` использует образы из GHCR для `api` и `bot`, что соответствует идее централизованного билда в CI и быстрого обновления на сервере.
- `deploy.sh` обновляет репозиторий и применяет конфигурацию без ручных шагов.

Готово: после push в `main` CI соберёт и опубликует образы, а CD обновит сервер автоматически.
