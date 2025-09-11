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
    bot_api_token: str = Field(default="")
    public_url: str = Field(default="")
    telegram_webhook_secret: str = Field(default="")
    milvus_uri: str = Field(default="")
    postgres_uri: str = Field(
        # Default for in-container networking: use the Docker service name
        # and the project database set in docker-compose (.env provides defaults).
        default="postgresql+psycopg://postgres:postgres@postgres:5432/baseknowledge"
    )
    vault_dir: Path = Field(default=Path("/tmp/vault"))
    log_level: str = Field(default="INFO")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
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
