# Получение SSL-сертификата для mindweaver.online

Эта инструкция описывает выпуск и обновление сертификата Let's Encrypt для домена `mindweaver.online` с использованием текущей конфигурации `docker-compose.yml` и переменных окружения из `.env`.

## Подготовка

1. В файле `.env` укажите публичные адреса сервиса, например:
   ```env
   PUBLIC_URL=https://mindweaver.online
   ```
2. Убедитесь, что порты `80` и `443` вашего сервера открыты и направлены на хост с Docker.

## Получение сертификата

Сценарии отличаются в зависимости от того, есть ли уже файлы сертификата в volume `certbot-etc`.

### A) Первый выпуск или после `docker compose down -v` (сертификатов нет)

При отсутствии сертификата HTTPS-конфиг Nginx не стартует. Используйте временный http-only конфиг и оверрайд compose:

```bash
# 1) Запустить nginx в http-only режиме (только порт 80)
docker compose -f docker-compose.yml -f infra/docker/nginx/http-only.override.yml up -d nginx

# 1.1) Убедиться, что порт 80 доступен извне (важно для Let's Encrypt)
# На сервере:
curl -I http://localhost/.well-known/acme-challenge/ping || true
# С другой машины/сети (или через онлайн-проверку):
# curl -I http://mindweaver.online/.well-known/acme-challenge/ping

# 2) Выпустить сертификат (webroot-челлендж через общий volume certbot-web)
docker compose -f docker-compose.yml -f infra/docker/nginx/http-only.override.yml run --rm letsencrypt

# 3) Перезапустить nginx с обычным https-конфигом
docker compose up -d nginx
```

### B) Пере-выпуск/обновление (сертификаты существуют)

Когда volume `certbot-etc` сохранён, nginx стартует в https сразу. Для обновления:

```bash
docker compose run --rm letsencrypt renew
docker compose restart nginx
```

## Обновление сертификата

Раз в ~90 дней повторяйте:
```bash
docker compose run --rm letsencrypt renew
docker compose restart nginx
```
Файлы сертификатов хранятся в volume `certbot-etc` и автоматически переиспользуются `nginx` через путь `/etc/letsencrypt`.
