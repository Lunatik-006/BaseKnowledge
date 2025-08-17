from dataclasses import dataclass
import os


@dataclass
class Settings:
    """Application settings loaded from environment variables."""
    replicate_api_token: str = os.getenv("REPLICATE_API_TOKEN", "")


def get_settings() -> Settings:
    """Return application settings instance."""
    return Settings()
