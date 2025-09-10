"""Telegram bot entry point.

Implements basic /start and /mode commands, message buffering in Curate mode
and forwarding of collected text to the API as described in the technical
specification (sections 5 and 9).
"""

from __future__ import annotations

import asyncio
import hashlib
from typing import List, Optional, Tuple

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from libs.core.settings import get_settings
from libs.logging import setup_logging


# ---------------------------------------------------------------------------
# Localisation helpers

MESSAGES = {
    "start": {
        "en": "Send me a message or forward posts – I will create notes.",
        "ru": "Отправь сообщение или перешли посты — я создам заметки.",
    },
    "open_app": {"en": "Open Mini App", "ru": "Открыть Mini App"},
    "mode_one": {"en": "Mode: One-to-One", "ru": "Режим: Один к одному"},
    "mode_curate": {
        "en": "Mode: Curate. Messages are buffered for 60s.",
        "ru": "Режим: Curate. Сообщения копятся 60 секунд.",
    },
    "buffered": {
        "en": "Saved. Send more or press 'Process now'.",
        "ru": "Сохранил. Пришли ещё или нажми «Обработать сейчас».",
    },
    "process_now": {"en": "Process now", "ru": "Обработать сейчас"},
    "processing": {"en": "Processing…", "ru": "Обработка…"},
    "done": {"en": "Notes created:", "ru": "Созданные заметки:"},
    "zip": {"en": "Download ZIP", "ru": "Скачать ZIP"},
    "error": {"en": "Error: {error}", "ru": "Ошибка: {error}"},
    "service_unavailable": {
        "en": "Service temporarily unavailable",
        "ru": "Сервис временно недоступен",
    },
    "request_rejected": {"en": "Request rejected", "ru": "Запрос отклонён"},
    "dev_info": {
        "en": "info for developers: {info}",
        "ru": "инфо для разработчика: {info}",
    },
    "no_text": {"en": "Text is empty", "ru": "Текст пуст"},
    "no_notes": {"en": "No notes created", "ru": "Заметки не созданы"},
}


def _get_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Return user language (ru/en)."""

    if "lang" in context.user_data:
        return context.user_data["lang"]
    code = (update.effective_user.language_code or "en").lower()
    lang = "ru" if code.startswith("ru") else "en"
    context.user_data["lang"] = lang
    return lang


# ---------------------------------------------------------------------------
# API interaction


async def ingest(text: str) -> Tuple[List[dict], Optional[dict]]:
    """Send text to the API and return list of created notes."""

    settings = get_settings()
    url = f"{settings.public_url}/ingest/text"
    token = settings.bot_api_token
    headers = {"X-Bot-Api-Token": token} if token else None
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json={"text": text}, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:  # pragma: no cover - network errors
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return [], {"status": status, "message": str(exc)}
    data = response.json()
    return data.get("notes", []), None


# ---------------------------------------------------------------------------
# Bot handlers


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""

    lang = _get_lang(update, context)
    settings = get_settings()
    keyboard = None
    if settings.public_url:
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        MESSAGES["open_app"][lang], url=f"{settings.public_url}/miniapp"
                    )
                ]
            ]
        )
    await update.message.reply_text(MESSAGES["start"][lang], reply_markup=keyboard)


async def mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle between one-to-one and Curate modes."""

    lang = _get_lang(update, context)
    current = context.user_data.get("mode", "one")
    new_mode = "curate" if current != "curate" else "one"
    context.user_data["mode"] = new_mode
    await update.message.reply_text(MESSAGES[f"mode_{new_mode}"][lang])


async def process_now_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process buffered messages immediately."""

    await update.callback_query.answer()
    lang = _get_lang(update, context)
    task = context.user_data.get("timer")
    if task:
        task.cancel()
        context.user_data["timer"] = None
    await _flush_buffer(update.effective_chat.id, context, lang)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text or forwarded messages."""

    lang = _get_lang(update, context)
    text = update.message.text
    if not text:
        await update.message.reply_text(MESSAGES["no_text"][lang])
        return

    mode = context.user_data.get("mode", "one")
    if mode == "curate":
        hashes = context.user_data.setdefault("hashes", set())
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest in hashes:
            return
        hashes.add(digest)
        buffer = context.user_data.setdefault("buffer", [])
        buffer.append(text)
        task = context.user_data.get("timer")
        if task:
            task.cancel()
        chat_id = update.effective_chat.id
        task = context.application.create_task(_schedule_flush(chat_id, context, lang))
        context.user_data["timer"] = task
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(MESSAGES["process_now"][lang], callback_data="process")]]
        )
        await update.message.reply_text(MESSAGES["buffered"][lang], reply_markup=keyboard)
    else:
        await _process_text([text], update.effective_chat.id, context, lang)


async def _schedule_flush(chat_id: int, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """Schedule automatic processing after timeout."""

    try:
        await asyncio.sleep(60)
        await _flush_buffer(chat_id, context, lang)
    except asyncio.CancelledError:  # pragma: no cover - timer cancelled
        pass


async def _flush_buffer(chat_id: int, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    buffer = context.user_data.get("buffer", [])
    if not buffer:
        await context.bot.send_message(chat_id, MESSAGES["no_text"][lang])
        return
    context.user_data["buffer"] = []
    context.user_data.get("hashes", set()).clear()
    context.user_data["timer"] = None
    await _process_text(buffer, chat_id, context, lang)


async def _process_text(
    texts: List[str], chat_id: int, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    text = "\n\n".join(texts)
    await context.bot.send_message(chat_id, MESSAGES["processing"][lang])
    try:
        notes, error = await ingest(text)
        if error:
            status = error.get("status")
            message = error.get("message")
            if status and 500 <= status < 600:
                user_msg = MESSAGES["service_unavailable"][lang]
            elif status and 400 <= status < 500:
                user_msg = MESSAGES["request_rejected"][lang]
            else:
                user_msg = MESSAGES["error"][lang].format(error=message)
            dev_info = MESSAGES["dev_info"][lang].format(
                info=f"ingest service: {status} {message}"
            )
            await context.bot.send_message(chat_id, f"{user_msg}\n{dev_info}")
            return
        if notes:
            settings = get_settings()
            if settings.public_url:
                lines = [
                    f"- [{n['title']}]({settings.public_url}/miniapp?note={n['id']})"
                    for n in notes
                ]
                lines.append(
                    f"{MESSAGES['zip'][lang]}: {settings.public_url}/export/zip"
                )
            else:
                lines = [f"- {n['title']}" for n in notes]
            reply = MESSAGES["done"][lang] + "\n" + "\n".join(lines)
        else:
            reply = MESSAGES["no_notes"][lang]
        await context.bot.send_message(
            chat_id, reply, disable_web_page_preview=True
        )
    except Exception as exc:  # pragma: no cover - network errors
        user_msg = MESSAGES["error"][lang].format(error=exc)
        dev_info = MESSAGES["dev_info"][lang].format(info="bot: _process_text")
        await context.bot.send_message(chat_id, f"{user_msg}\n{dev_info}")


# ---------------------------------------------------------------------------
# Main entry


def main() -> None:
    """Run the Telegram bot."""

    settings = get_settings()
    token = settings.telegram_bot_token
    if not token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mode", mode))
    app.add_handler(CallbackQueryHandler(process_now_cb, pattern="^process$"))
    # Separate handler for forwarded text messages
    app.add_handler(
        MessageHandler(filters.TEXT & filters.FORWARDED, handle_text)
    )
    # And for regular text messages
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.FORWARDED, handle_text)
    )

    # ``run_polling`` handles initialization, starting and graceful shutdown,
    # so we don't need to access the updater directly.
    app.run_polling()


if __name__ == "__main__":
    setup_logging()
    main()

