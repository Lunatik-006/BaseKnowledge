"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the application."""

    replicate_api_token: str = Field(default="")
    telegram_bot_token: str = Field(default="")
    public_url: str = Field(default="")
    telegram_webhook_secret: str = Field(default="")
    milvus_uri: str = Field(default="")
    postgres_uri: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
    )
    vault_dir: Path = Field(default=Path("/tmp/vault"))

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Return application settings instance."""
    return Settings()


__all__ = ["Settings", "get_settings"]
