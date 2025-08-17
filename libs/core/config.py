"""Application configuration loaded via Pydantic settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings pulled from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


__all__ = ["Settings"]
