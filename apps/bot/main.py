from __future__ import annotations

import asyncio
import os

from telegram.ext import Application


async def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    base_url = os.getenv("PUBLIC_URL")
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    if not token or not base_url:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or PUBLIC_URL")

    app = Application.builder().token(token).build()
    await app.bot.set_webhook(f"{base_url}/telegram/webhook/{secret}")


if __name__ == "__main__":
    asyncio.run(main())

