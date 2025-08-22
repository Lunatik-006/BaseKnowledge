from __future__ import annotations

import asyncio

from telegram.ext import Application

from libs.core.settings import get_settings


async def main() -> None:
    settings = get_settings()
    token = settings.telegram_bot_token
    base_url = settings.public_url
    secret = settings.telegram_webhook_secret
    if not token or not base_url:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or PUBLIC_URL")

    app = Application.builder().token(token).build()
    await app.bot.set_webhook(f"{base_url}/telegram/webhook/{secret}")


if __name__ == "__main__":
    asyncio.run(main())

