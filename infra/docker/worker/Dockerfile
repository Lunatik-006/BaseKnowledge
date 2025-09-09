FROM python:3.11-slim

WORKDIR /app
COPY libs ./libs
COPY apps/bot ./apps/bot

# Install dependencies required by the bot.
RUN pip install --no-cache-dir \
    python-telegram-bot \
    requests \
    pydantic==2.11.7 \
    pydantic-settings==2.10.1

ENV PYTHONPATH=/app
CMD ["python", "apps/bot/main.py"]
