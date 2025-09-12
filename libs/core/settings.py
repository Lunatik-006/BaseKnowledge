"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_postgres_uri_from_env() -> str:
    """Build Postgres URI from component env vars if POSTGRES_URI is not set.

    Keeps a single source of truth for DB name via .env variables
    (POSTGRES_USER/PASSWORD/HOST/PORT/DB). If POSTGRES_URI is provided, it
    will override this default.
    """
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "baseknowledge")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


class Settings(BaseSettings):
    """Runtime settings for the application."""

    replicate_api_token: str = Field(default="")
    telegram_bot_token: str = Field(default="")
    bot_api_token: str = Field(default="")
    public_url: str = Field(default="")
    telegram_webhook_secret: str = Field(default="")
    milvus_uri: str = Field(default="")
    # Embeddings configuration
    embeddings_model: str = Field(default="nomic-ai/nomic-embed-text-v1.5")
    embedding_dim: int = Field(default=768)
    # Optional direct URI override (env: POSTGRES_URI). If not set, a default
    # is assembled from POSTGRES_USER/PASSWORD/HOST/PORT/DB.
    postgres_uri: str = Field(default_factory=_default_postgres_uri_from_env)
    vault_dir: Path = Field(default=Path("/tmp/vault"))
    log_level: str = Field(default="INFO")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # Be lenient with env var names (e.g., POSTGRES_URI vs postgres_uri)
        case_sensitive=False,
        # Allow environment variables that don't have a matching field.
        # This makes the settings more robust when extra variables are
        # present in the environment (e.g. PUBLIC_URL used by miniapp build).
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return application settings instance."""
    return Settings()


__all__ = ["Settings", "get_settings"]
