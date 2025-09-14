from __future__ import annotations

"""Application-wide logging configuration.

Provides a JSON formatter with a minimal, consistent set of fields:
- timestamp (UTC ISO8601), level, logger, service, environment, message
- Supports structured extras via `logger.info(msg, extra={...})` which are
  merged into the JSON.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from libs.core.settings import get_settings


class _JsonFormatter(logging.Formatter):
    """One-line JSON log formatter with stable keys and UTC timestamps."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        settings = get_settings()
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        base: Dict[str, Any] = {
            "timestamp": dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "service": getattr(settings, "service_name", "api"),
            "environment": getattr(settings, "environment", "development"),
            "message": record.getMessage(),
        }
        # Merge any structured extras (from `extra=`)
        for k, v in record.__dict__.items():
            if k in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
            }:
                continue
            # Don't overwrite base keys unless explicitly provided in extra
            if k not in base:
                base[k] = v
        if record.exc_info:
            etype = getattr(record.exc_info[0], "__name__", str(record.exc_info[0]))
            base.setdefault("error", {})
            base["error"] = {
                "class": etype,
                "message": str(record.getMessage())[:500],
            }
        try:
            return json.dumps(base, ensure_ascii=False)
        except Exception:
            # Fallback to a repr if something is not JSON-serializable
            for k, v in list(base.items()):
                try:
                    json.dumps({k: v})
                except Exception:
                    base[k] = repr(v)
            return json.dumps(base, ensure_ascii=False)


def setup_logging() -> None:
    """Configure root logger to output one-line JSON logs."""

    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


__all__ = ["setup_logging"]
