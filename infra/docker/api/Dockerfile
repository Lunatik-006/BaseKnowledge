FROM python:3.11-slim AS builder

ENV VENV_PATH=/opt/venv
ENV PATH="$VENV_PATH/bin:$PATH"

RUN python -m venv "$VENV_PATH" \
    && apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt requirements-api.txt ./
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt -r requirements-api.txt

FROM python:3.11-slim AS runtime

ENV VENV_PATH=/opt/venv
ENV PATH="$VENV_PATH/bin:$PATH"

# curl is used by the container healthcheck
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder "$VENV_PATH" "$VENV_PATH"
COPY libs ./libs
COPY apps/api ./apps/api

ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["python", "-m", "apps.api.main"]
