from __future__ import annotations

import sys

import requests

from libs.core.settings import get_settings


def main() -> None:
    settings = get_settings()
    token = settings.telegram_bot_token
    if not token:
        print("Missing TELEGRAM_BOT_TOKEN", file=sys.stderr)
        sys.exit(1)

    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
        if resp.ok:
            sys.exit(0)
    except Exception as exc:  # pragma: no cover - network errors
        print(exc, file=sys.stderr)

    sys.exit(1)


if __name__ == "__main__":
    main()
