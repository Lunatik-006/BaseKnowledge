from __future__ import annotations

"""Application-wide logging configuration."""

import logging
from datetime import datetime, timezone

from libs.core.settings import get_settings


class _MilvusFormatter(logging.Formatter):
    """Formatter matching Milvus-style log lines."""

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        tz = dt.strftime("%z")
        tz = f"{tz[:3]}:{tz[3:]}"
        return dt.strftime("%Y/%m/%d %H:%M:%S") + f".{int(dt.microsecond / 1000):03d} {tz}"


def setup_logging() -> None:
    """Configure root logger using settings.LOG_LEVEL."""

    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(_MilvusFormatter("[%(asctime)s] [%(levelname)s] %(message)s"))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


__all__ = ["setup_logging"]
