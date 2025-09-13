from __future__ import annotations

from pathlib import Path
from typing import Dict

import yaml


class I18n:
    """Simple YAML-backed i18n loader with fallback to English."""

    def __init__(self, lang: str, base_dir: Path | None = None) -> None:
        self.lang = (lang or 'en').lower()
        self.base_dir = base_dir or Path('config/i18n')
        self._cache: Dict[str, str] = {}
        self._fallback: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        def _read(path: Path) -> Dict[str, str]:
            if not path.exists():
                return {}
            with path.open('r', encoding='utf-8') as fh:
                data = yaml.safe_load(fh) or {}
                if not isinstance(data, dict):
                    return {}
                return {str(k): str(v) for k, v in data.items()}

        self._fallback = _read(self.base_dir / 'messages.en.yaml')
        if self.lang == 'en':
            self._cache = self._fallback
        else:
            self._cache = _read(self.base_dir / f'messages.{self.lang}.yaml')

    def t(self, key: str) -> str:
        return self._cache.get(key) or self._fallback.get(key) or key


__all__ = ["I18n"]
