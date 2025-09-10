# Настройка SSL для mindweaver.online

Инструкция описывает получение и автоматическое обновление сертификатов Let's Encrypt для домена **mindweaver.online** в инфраструктуре, построенной на `docker-compose`.

## 1. Предварительные требования
- Домен `mindweaver.online` (и при необходимости поддомены `api.mindweaver.online`, `www.mindweaver.online`) указывает на публичный IP сервера.
- На сервере установлен Docker и docker-compose.
- В проекте уже есть сервисы `api` (порт 8000) и `miniapp` (порт 3000), описанные в `docker-compose.yml`.

## 2. Добавление сервисов `nginx` и `certbot`
Дополните `docker-compose.yml` следующими сервисами и общими томами:

```yaml
services:
  nginx:
    image: nginx:alpine
    volumes:
      - ./infra/nginx/conf.d:/etc/nginx/conf.d:ro
      - certbot-etc:/etc/letsencrypt
      - certbot-var:/var/lib/letsencrypt
      - certbot-www:/var/www/certbot
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - api
      - miniapp

  certbot:
    image: certbot/certbot
    volumes:
      - certbot-etc:/etc/letsencrypt
      - certbot-var:/var/lib/letsencrypt
      - certbot-www:/var/www/certbot
    entrypoint: >-
      /bin/sh -c "trap exit TERM; while :; do certbot renew; sleep 12h & wait \$${!}; done"

volumes:
  certbot-etc:
  certbot-var:
  certbot-www:
```

## 3. Конфигурация Nginx
Создайте файл `infra/nginx/conf.d/mindweaver.conf` со следующим содержимым:

```nginx
server {
    listen 80;
    server_name mindweaver.online api.mindweaver.online;
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name mindweaver.online;

    ssl_certificate /etc/letsencrypt/live/mindweaver.online/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mindweaver.online/privkey.pem;

    location / {
        proxy_pass http://miniapp:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}

server {
    listen 443 ssl;
    server_name api.mindweaver.online;

    ssl_certificate /etc/letsencrypt/live/api.mindweaver.online/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.mindweaver.online/privkey.pem;

    location / {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 4. Получение сертификатов
1. Запустите контейнер Nginx:
   ```bash
   docker compose up -d nginx
   ```
2. Выпустите сертификаты для доменов:
   ```bash
   docker compose run --rm certbot certonly --webroot -w /var/www/certbot \
     -d mindweaver.online -d api.mindweaver.online
   ```
3. Перезагрузите Nginx, чтобы он подхватил новые сертификаты:
   ```bash
   docker compose exec nginx nginx -s reload
   ```

## 5. Проверка
Откройте в браузере `https://mindweaver.online` и `https://api.mindweaver.online`. Сертификаты должны быть выданы Let's Encrypt и отмечены как действительные.

## 6. Автоматическое обновление
Контейнер `certbot` запускает `certbot renew` каждые 12 часов. Сертификаты обновятся автоматически, Nginx необходимо перезагрузить:
```bash
docker compose exec nginx nginx -s reload
```
Рекомендуется настроить cron или systemd timer, чтобы выполнять эту команду раз в день после потенциального обновления.

## 7. Диагностика
- Логи Nginx: `docker compose logs nginx`
- Логи Certbot: `docker compose logs certbot`
- Проверка конфигурации: `docker compose exec nginx nginx -t`

Следуя этим шагам, вы настроите HTTPS для домена mindweaver.online, используя инфраструктуру проекта на основе docker-compose.
