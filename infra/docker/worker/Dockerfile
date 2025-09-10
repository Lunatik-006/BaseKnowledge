FROM python:3.11-slim

WORKDIR /app

COPY requirements-worker.txt ./
RUN pip install --no-cache-dir -r requirements-worker.txt

COPY libs ./libs
COPY apps/bot ./apps/bot

ENV PYTHONPATH=/app
CMD ["python", "apps/bot/main.py"]
