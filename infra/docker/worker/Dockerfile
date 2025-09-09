FROM python:3.11-slim

WORKDIR /app
COPY libs ./libs
COPY apps/bot ./apps/bot

RUN pip install --no-cache-dir python-telegram-bot requests

ENV PYTHONPATH=/app
CMD ["python", "apps/bot/main.py"]
