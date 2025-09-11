# Получение SSL-сертификата для mindweaver.online

Эта инструкция описывает выпуск и обновление сертификата Let's Encrypt для домена `mindweaver.online` с использованием текущей конфигурации `docker-compose.yml` и переменных окружения из `.env`.

## Подготовка

1. В файле `.env` укажите публичные адреса сервиса, например:
   ```env
   PUBLIC_URL=https://mindweaver.online
   ```
2. Убедитесь, что порты `80` и `443` вашего сервера открыты и направлены на хост с Docker.

## Получение сертификата

1. Запустите необходимые сервисы, включая `nginx`, чтобы обеспечить доступ к challenge:
   ```bash
   docker compose up -d nginx api miniapp
   ```
2. Выпустите сертификат при помощи контейнера `letsencrypt`:
   ```bash
   docker compose run --rm letsencrypt
   ```
   Сервис `letsencrypt` использует `certbot` с методом `webroot` и доменом `mindweaver.online`, заданным в `docker-compose.yml`.
3. Перезапустите `nginx`, чтобы он начал использовать полученные файлы сертификата:
   ```bash
   docker compose restart nginx
   ```

## Обновление сертификата

Раз в ~90 дней повторяйте:
```bash
docker compose run --rm letsencrypt renew
docker compose restart nginx
```
Файлы сертификатов хранятся в volume `certbot-etc` и автоматически переиспользуются `nginx` через путь `/etc/letsencrypt`.
