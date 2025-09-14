"""Telegram bot entry point.
Implements /start, /mode and /help, Curate mode buffering, and forwarding of
collected text to the API as described in the technical specification.
Adds:
- persistent reply keyboard with command buttons and Mini App button (WebApp)
- chat menu button configured to open the Mini App inside Telegram
"""
from __future__ import annotations
import asyncio
import hashlib
from typing import List, Optional, Tuple
import httpx
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
    WebAppInfo,
    BotCommand,
    MenuButtonWebApp,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from libs.core.settings import get_settings
from libs.core.i18n import I18n
from libs.logging import setup_logging
# ---------------------------------------------------------------------------
# Localisation helpers
def L(lang: str, key: str) -> str:
    """Translate a key using YAML i18n with a built-in fallback.

    If YAML files are missing in the runtime image, fall back to
    the bundled MESSAGES dictionary to avoid leaking raw keys.
    """
    val = I18n(lang).t(key)
    if val != key:
        return val
    # YAML missing or key absent — use in-file fallback if available
    msg = MESSAGES.get(key)
    if msg:
        return msg.get(lang) or msg.get("en") or next(iter(msg.values()), key)
    return key
MESSAGES = {
    "start": {
        "en": (
            "Hi! I can turn your messages and forwarded posts into structured notes.\n"
            "- Type or forward text to create notes\n"
            "- Use /mode to switch One-to-One vs Curate (batch 60s)\n"
            "- Tap the Mini App to browse notes, search, and export ZIP"
        ),
        "ru": (
            "Привет! Я превращаю ваши сообщения и пересланные посты в структурированные заметки.\n"
            "- Напишите или перешлите текст, чтобы создать заметки\n"
            "- Используйте /mode для переключения режимов One-to-One и Curate (пакет 60с)\n"
            "- Откройте Mini App, чтобы просматривать, искать и выгружать ZIP"
        ),
    },
    "help": {
        "en": (
            "Commands:\n"
            "/start — welcome and menu\n"
            "/mode — toggle One-to-One vs Curate (buffers 60s)\n"
            "/help — this help\n\n"
            "Tips: In Curate mode messages are deduplicated and processed together."
        ),
        "ru": (
            "Команды:\n"
            "/start — приветствие и меню\n"
            "/mode — переключение режимов One-to-One и Curate (буфер 60с)\n"
            "/help — эта справка\n\n"
            "Подсказка: в режиме Curate сообщения дедуплицируются и обрабатываются вместе."
        ),
    },
    "open_app": {"en": "Open Mini App", "ru": "Открыть Mini App"},
    "mode_one": {"en": "Mode: One-to-One", "ru": "Режим: One-to-One"},
    "mode_curate": {
        "en": "Mode: Curate. Messages are buffered for 60s.",
        "ru": "Режим: Curate. Сообщения буферизуются 60 секунд.",
    },
    "buffered": {
        "en": "Saved. Send more or press 'Process now'.",
        "ru": "Сохранено. Отправьте ещё или нажмите ‘Обработать сейчас’.",
    },
    "process_now": {"en": "Process now", "ru": "Обработать сейчас"},
    "processing": {"en": "Processing…", "ru": "Обрабатываю…"},
    "done": {"en": "Notes created:", "ru": "Заметки созданы:"},
    "zip": {"en": "Download ZIP", "ru": "Скачать ZIP"},
    "error": {"en": "Error: {error}", "ru": "Ошибка: {error}"},
    "service_unavailable": {
        "en": "Service temporarily unavailable",
        "ru": "Сервис временно недоступен",
    },
    "request_rejected": {"en": "Request rejected", "ru": "Запрос отклонён"},
    "dev_info": {
        "en": "info for developers: {info}",
        "ru": "информация для разработчиков: {info}",
    },
    "no_text": {"en": "Text is empty", "ru": "Текст пуст"},
    "no_notes": {"en": "No notes created", "ru": "Заметки не созданы"},
}

# Fallbacks for Block 2 keys if YAML is missing
MESSAGES.update({
    "create_project_name_prompt": {
        "en": "Enter a project name (e.g., ‘Focus Sprint #1’).",
        "ru": "Введите название проекта (например, ‘Фокус‑спринт #1’).",
    },
    "create_project_confirm": {
        "en": "Create project ‘{name}’?",
        "ru": "Создать проект «{name}»?",
    },
    "create_project_created": {
        "en": "Project ‘{name}’ created.",
        "ru": "Проект «{name}» создан.",
    },
    "project_howto": {
        "en": "How to work in a project:\n- Add 5–10 materials (text, images, audio, video)\n- We’ll analyze them and outline a draft structure\n- Later, you can build a knowledge base and a course",
        "ru": "Как работать в проекте:\n- Добавьте 5–10 материалов (текст, изображения, аудио, видео)\n- Мы проанализируем их и соберём черновую структуру\n- Далее сможете собрать базу знаний и курс",
    },
    "add_materials_btn": {"en": "Add materials", "ru": "Добавить материалы"},
    "create_project_btn": {"en": "Create project", "ru": "Создать проект"},
    "default_project_name": {"en": "Default", "ru": "По умолчанию"},
    "action_cancelled": {"en": "Cancelled.", "ru": "Отменено."},
    "yes": {"en": "Yes", "ru": "Да"},
    "no": {"en": "No", "ru": "Нет"},
    "cancel": {"en": "Cancel", "ru": "Отмена"},
    "done": {"en": "Done", "ru": "Готово"},
    "empty_state_text": {
        "en": "Empty project. Add 5–10 materials to draft your course.",
        "ru": "Пустой проект. Добавьте 5–10 материалов для черновой структуры курса.",
    },
    "open_project_choose": {"en": "Open a project:", "ru": "Откройте проект:"},
    "open_project_empty": {"en": "No projects yet. Create a new one.", "ru": "Проектов нет. Создайте новый."},
    "open_project_open_btn": {"en": "Open ‘{name}’", "ru": "Открыть «{name}»"},
    "open_project_opened": {"en": "Project ‘{name}’ opened!", "ru": "Проект «{name}» открыт!"},
    "add_materials_choose_type": {"en": "Choose material type:", "ru": "Выберите тип материалов:"},
    "mat_type_text": {"en": "Text", "ru": "Текст"},
    "mat_type_image": {"en": "Image", "ru": "Изображение"},
    "mat_type_audio": {"en": "Audio/Voice", "ru": "Аудио/Голос"},
    "mat_type_video": {"en": "Video/Link", "ru": "Видео/Ссылка"},
    "add_text_instructions": {
        "en": "Send up to 10 text messages. Press ‘Done’ when finished.",
        "ru": "Отправьте до 10 текстовых сообщений. Нажмите «Готово», когда закончите.",
    },
    "add_image_instructions": {"en": "Send photos with text you want to capture (OCR soon).", "ru": "Отправляйте фото с текстом (OCR скоро подключим)."},
    "add_audio_instructions": {"en": "Send audio/voice messages (we’ll transcribe soon).", "ru": "Отправляйте аудио/голос (скоро расшифровка)."},
    "add_video_instructions": {"en": "Send a YouTube link (we’ll fetch content soon).", "ru": "Отправьте ссылку на YouTube (скоро заберём контент)."},
    "materials_saved_more": {"en": "Saved. Send more or press ‘Done’.", "ru": "Сохранено. Отправляйте ещё или нажмите «Готово»."},
    "materials_limit_reached": {"en": "Limit reached (10 items). Press ‘Done’.", "ru": "Достигнут лимит (10 единиц). Нажмите «Готово»."},
    "use_add_materials_first": {"en": "Use /add_materials to choose a type first.", "ru": "Сначала выберите тип через /add_materials."},
    "processing_short": {"en": "Processing…", "ru": "Обрабатываем…"},
    "not_implemented_yet": {"en": "Feature not implemented yet. Coming soon.", "ru": "Функция ещё не реализована. Скоро появится."},
    "coming_soon_image": {"en": "Got a photo. Image OCR ingestion coming soon.", "ru": "Изображение получено. OCR‑загрузка скоро появится."},
    "coming_soon_audio": {"en": "Got audio/voice. Transcription coming soon.", "ru": "Аудио/голос получены. Транскрибация скоро появится."},
    "coming_soon_video": {"en": "Got a video item. Video link ingestion coming soon.", "ru": "Видео получено. Загрузка по ссылке скоро появится."},
    "status_empty": {"en": "Empty", "ru": "Пусто"},
    "status_loading": {"en": "Loading", "ru": "Загрузка"},
    "status_warning": {"en": "Warning", "ru": "Предупреждение"},
    "status_error": {"en": "Error", "ru": "Ошибка"},
    "status_success": {"en": "Success", "ru": "Готово"},
    "my_data_text": {"en": "Open the Mini App to browse your materials.", "ru": "Откройте Mini App, чтобы просмотреть материалы."},
})
def _get_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Return user language (ru/en)."""
    if "lang" in context.user_data:
        return context.user_data["lang"]
    code = (update.effective_user.language_code or "en").lower()
    lang = "ru" if code.startswith("ru") else "en"
    context.user_data["lang"] = lang
    return lang
def _build_reply_keyboard(lang: str, webapp_url: str | None) -> ReplyKeyboardMarkup | None:
    """Build a persistent reply keyboard with command shortcuts and Mini App."""
    rows = [[KeyboardButton("/mode"), KeyboardButton("/help")]]
    if webapp_url:
        rows.append(
            [
                KeyboardButton(
                    text=L(lang, 'open_app'), web_app=WebAppInfo(url=webapp_url)
                )
            ]
        )
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)
# ---------------------------------------------------------------------------
# API interaction
async def ingest(text: str) -> Tuple[List[dict], Optional[dict]]:
    """Send text to the API and return list of created notes."""
    settings = get_settings()
    url = f"{settings.public_url}/api/ingest/text"
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

async def _set_lang_via_api(telegram_id: int, lang: str) -> None:
    settings = get_settings()
    if not settings.public_url:
        return
    token = settings.bot_api_token
    if not token:
        return
    url = f"{settings.public_url}/api/bot/user/lang"
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json={"telegram_id": telegram_id, "lang": lang}, headers={"X-Bot-Api-Token": token}, timeout=5)
        except Exception:
            pass

async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _get_lang(update, context)
    # RU+EN combined prompt
    i_en, i_ru = I18n('en'), I18n('ru')
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(i_en.t('lang_en'), callback_data='setlang:en'), InlineKeyboardButton(i_ru.t('lang_ru'), callback_data='setlang:ru')]])
    prompt = (
        f"{i_en.t('choose_language_title')} / {i_ru.t('choose_language_title')}\n"
        f"{i_en.t('choose_language_note')}\n{i_ru.t('choose_language_note')}"
    )
    await update.message.reply_text(prompt, reply_markup=keyboard)
async def setlang_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    data = q.data or ''
    if not data.startswith('setlang:'):
        return
    new_lang = data.split(':',1)[1]
    await _set_lang_via_api(update.effective_user.id, new_lang)
    context.user_data['lang'] = new_lang
    i = I18n(new_lang)
    try:
        await q.edit_message_text(i.t('lang_set_ru') if new_lang=='ru' else i.t('lang_set_en'))
    except Exception:
        await q.message.reply_text(i.t('lang_set_ru') if new_lang=='ru' else i.t('lang_set_en'))
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    lang = _get_lang(update, context)
    settings = get_settings()
    webapp_url = f"{settings.public_url}/miniapp?lang={lang}" if settings.public_url else None
    # Inline keyboard with a native WebApp button (opens inside Telegram)
    inline_keyboard = None
    if webapp_url:
        inline_keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        L(lang, 'open_app'), web_app=WebAppInfo(url=webapp_url)
                    )
                ]
            ]
        )
    # Persistent reply keyboard with commands and Mini App button
    reply_keyboard = _build_reply_keyboard(lang, webapp_url)
    await update.message.reply_text(
        L(lang, 'start'), reply_markup=reply_keyboard or inline_keyboard
    )
    # Offer language selection right after /start (RU+EN combined)
    i_en, i_ru = I18n('en'), I18n('ru')
    lang_keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(i_en.t('lang_en'), callback_data='setlang:en'),
                InlineKeyboardButton(i_ru.t('lang_ru'), callback_data='setlang:ru'),
            ]
        ]
    )
    await update.message.reply_text(
        f"{i_en.t('choose_language_title')} / {i_ru.t('choose_language_title')}\n"
        f"{i_en.t('choose_language_note')}\n{i_ru.t('choose_language_note')}",
        reply_markup=lang_keyboard,
    )
    # If both are available, add an extra message with inline button for convenience
    if reply_keyboard and inline_keyboard:
        await update.message.reply_text(L(lang, 'open_app'), reply_markup=inline_keyboard)
async def mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle between one-to-one and Curate mode."""
    lang = _get_lang(update, context)
    mode = context.user_data.get("mode", "one")
    if mode == "curate":
        context.user_data["mode"] = "one"
        await update.message.reply_text(L(lang, 'mode_one'))
    else:
        context.user_data["mode"] = "curate"
        await update.message.reply_text(L(lang, 'mode_curate'))
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help and commands list."""
    lang = _get_lang(update, context)
    await update.message.reply_text(L(lang, 'help'))
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
        await update.message.reply_text(L(lang, 'no_text'))
        return
    # Project name capture flow for /create_project
    if context.user_data.get('awaiting_project_name'):
        name = text.strip()
        context.user_data['pending_project_name'] = name
        context.user_data['awaiting_project_name'] = False
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(L(lang, 'yes'), callback_data='cproj:confirm'), InlineKeyboardButton(L(lang, 'cancel'), callback_data='cproj:cancel')]
        ])
        await update.message.reply_text(L(lang, 'create_project_confirm').format(name=name), reply_markup=kb)
        return
    # Materials collection flow (text)
    if context.user_data.get('collecting_materials') and context.user_data.get('material_type') == 'text':
        buf = context.user_data.setdefault('materials_text_buffer', [])
        if len(buf) >= 10:
            await update.message.reply_text(L(lang, 'materials_limit_reached'))
            return
        buf.append(text)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(L(lang, 'done'), callback_data='addm:done'), InlineKeyboardButton(L(lang, 'cancel'), callback_data='addm:cancel')]
        ])
        await update.message.reply_text(L(lang, 'materials_saved_more'), reply_markup=kb)
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
            [[InlineKeyboardButton(L(lang, 'process_now'), callback_data="process")]]
        )
        await update.message.reply_text(L(lang, 'buffered'), reply_markup=keyboard)
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
        await context.bot.send_message(chat_id, L(lang, 'no_text'))
        return
    context.user_data["buffer"] = []
    context.user_data.get("hashes", set()).clear()
    context.user_data["timer"] = None
    await _process_text(buffer, chat_id, context, lang)
async def _process_text(
    texts: List[str], chat_id: int, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    text = "\n\n".join(texts)
    await context.bot.send_message(chat_id, L(lang, 'processing'))
    try:
        notes, error = await ingest(text)
        if error:
            status = error.get("status")
            message = error.get("message")
            if status and 500 <= status < 600:
                user_msg = L(lang, 'service_unavailable')
            elif status and 400 <= status < 500:
                user_msg = L(lang, 'request_rejected')
            else:
                user_msg = L(lang, 'error').format(error=message)
            dev_info = L(lang, 'dev_info').format(
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
                # ZIP export is an API endpoint exposed via /api
                lines.append(f"{L(lang, 'zip')}: {settings.public_url}/api/export/zip")
            else:
                lines = [f"- {n['title']}" for n in notes]
            reply = L(lang, 'done') + "\n" + "\n".join(lines)
        else:
            reply = L(lang, 'no_notes')
        await context.bot.send_message(
            chat_id, reply, disable_web_page_preview=True
        )
    except Exception as exc:  # pragma: no cover - network errors
        user_msg = L(lang, 'error').format(error=exc)
        dev_info = L(lang, 'dev_info').format(info="bot: _process_text")
        await context.bot.send_message(chat_id, f"{user_msg}\n{dev_info}")
# ---------------------------------------------------------------------------
# Block 2: Projects and Materials UI helpers and handlers

STATUS_EMOJI = {
    'empty': '🗒️',
    'loading': '⏳',
    'warning': '⚠️',
    'error': '❌',
    'success': '✅',
}


async def _get_ui_state_via_api(telegram_id: int) -> dict | None:
    settings = get_settings()
    if not settings.public_url:
        return None
    token = settings.bot_api_token
    if not token:
        return None
    url = f"{settings.public_url}/api/bot/user/ui_state"
    params = {"telegram_id": telegram_id}
    headers = {"X-Bot-Api-Token": token}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, headers=headers, timeout=5)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None


async def _send_status(chat_id: int, context: ContextTypes.DEFAULT_TYPE, lang: str, kind: str, text: str) -> None:
    label = L(lang, f'status_{kind}')
    emoji = STATUS_EMOJI.get(kind, '')
    message = f"{emoji} {label} {text}".strip()
    await context.bot.send_message(chat_id, message)


# /create_project ------------------------------------------------------------
async def create_project_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _get_lang(update, context)
    context.user_data['awaiting_project_name'] = True
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(L(lang, 'cancel'), callback_data='cproj:cancel')]])
    await update.message.reply_text(L(lang, 'create_project_name_prompt'), reply_markup=kb)


async def cproj_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    lang = context.user_data.get('lang', 'en')
    data = q.data or ''
    if data == 'cproj:start':
        context.user_data['awaiting_project_name'] = True
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(L(lang, 'cancel'), callback_data='cproj:cancel')]])
        await q.message.reply_text(L(lang, 'create_project_name_prompt'), reply_markup=kb)
        return
    if data.endswith(':cancel'):
        context.user_data.pop('awaiting_project_name', None)
        context.user_data.pop('pending_project_name', None)
        await q.message.reply_text(L(lang, 'action_cancelled'))
        return
    if data.endswith(':confirm'):
        name = context.user_data.get('pending_project_name') or L(lang, 'default_project_name')
        context.user_data['current_project'] = name
        try:
            await _update_ui_state_via_api(q.from_user.id, current_project=name, last_screen='project_created')
        except Exception:
            pass
        btn = InlineKeyboardMarkup([[InlineKeyboardButton(L(lang, 'add_materials_btn'), callback_data='addm:open')]])
        await q.message.reply_text(L(lang, 'create_project_created').format(name=name))
        await q.message.reply_text(L(lang, 'project_howto'), reply_markup=btn)
        return


# ES0 and /open_project ------------------------------------------------------
async def open_project_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _get_lang(update, context)
    chat_id = update.effective_chat.id
    state = await _get_ui_state_via_api(update.effective_user.id)
    current = (state or {}).get('current_project') or context.user_data.get('current_project')
    if current:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(L(lang, 'open_project_open_btn').format(name=current), callback_data='openp:current')]])
        await update.message.reply_text(L(lang, 'open_project_choose'), reply_markup=kb)
    else:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(L(lang, 'create_project_btn'), callback_data='cproj:start')]])
        await context.bot.send_message(chat_id, L(lang, 'open_project_empty'), reply_markup=kb)


async def openp_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    lang = context.user_data.get('lang', 'en')
    name = context.user_data.get('current_project') or L(lang, 'default_project_name')
    try:
        await _update_ui_state_via_api(q.from_user.id, current_project=name, last_screen='project_opened')
    except Exception:
        pass
    await q.message.reply_text(L(lang, 'open_project_opened').format(name=name))
    # ES0 empty state CTA
    btn = InlineKeyboardMarkup([[InlineKeyboardButton(L(lang, 'add_materials_btn'), callback_data='addm:open')]])
    await q.message.reply_text(L(lang, 'empty_state_text'), reply_markup=btn)


# /add_materials -------------------------------------------------------------
async def add_materials_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _get_lang(update, context)
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(L(lang, 'mat_type_text'), callback_data='addm:type:text'),
            InlineKeyboardButton(L(lang, 'mat_type_image'), callback_data='addm:type:image'),
        ],
        [
            InlineKeyboardButton(L(lang, 'mat_type_audio'), callback_data='addm:type:audio'),
            InlineKeyboardButton(L(lang, 'mat_type_video'), callback_data='addm:type:video'),
        ],
        [InlineKeyboardButton(L(lang, 'cancel'), callback_data='addm:cancel')],
    ])
    await update.message.reply_text(L(lang, 'add_materials_choose_type'), reply_markup=kb)


async def addm_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    lang = context.user_data.get('lang', 'en')
    data = q.data or ''
    if data == 'addm:open':
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(L(lang, 'mat_type_text'), callback_data='addm:type:text'),
                InlineKeyboardButton(L(lang, 'mat_type_image'), callback_data='addm:type:image'),
            ],
            [
                InlineKeyboardButton(L(lang, 'mat_type_audio'), callback_data='addm:type:audio'),
                InlineKeyboardButton(L(lang, 'mat_type_video'), callback_data='addm:type:video'),
            ],
            [InlineKeyboardButton(L(lang, 'cancel'), callback_data='addm:cancel')],
        ])
        await q.message.reply_text(L(lang, 'add_materials_choose_type'), reply_markup=kb)
        return
    if data.endswith(':cancel'):
        context.user_data.pop('collecting_materials', None)
        context.user_data.pop('material_type', None)
        context.user_data.pop('materials_text_buffer', None)
        await q.message.reply_text(L(lang, 'action_cancelled'))
        return
    if data.endswith(':done'):
        if context.user_data.get('material_type') == 'text':
            texts = context.user_data.get('materials_text_buffer') or []
            context.user_data['materials_text_buffer'] = []
            context.user_data['collecting_materials'] = False
            await _send_status(q.message.chat_id, context, lang, 'loading', L(lang, 'processing_short'))
            if texts:
                await _process_text(texts, q.message.chat_id, context, lang)
            else:
                await q.message.reply_text(L(lang, 'no_text'))
        else:
            await q.message.reply_text(L(lang, 'not_implemented_yet'))
        return
    if data.startswith('addm:type:'):
        kind = data.split(':', 2)[2]
        context.user_data['collecting_materials'] = True
        context.user_data['material_type'] = kind
        if kind == 'text':
            await q.message.reply_text(L(lang, 'add_text_instructions'))
        elif kind == 'image':
            await q.message.reply_text(L(lang, 'add_image_instructions'))
        elif kind == 'audio':
            await q.message.reply_text(L(lang, 'add_audio_instructions'))
        elif kind == 'video':
            await q.message.reply_text(L(lang, 'add_video_instructions'))
        return


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _get_lang(update, context)
    if context.user_data.get('collecting_materials') and context.user_data.get('material_type') == 'image':
        await update.message.reply_text(L(lang, 'coming_soon_image'))
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(L(lang, 'done'), callback_data='addm:done'), InlineKeyboardButton(L(lang, 'cancel'), callback_data='addm:cancel')]])
        await update.message.reply_text(L(lang, 'materials_saved_more'), reply_markup=kb)
    else:
        await update.message.reply_text(L(lang, 'use_add_materials_first'))


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _get_lang(update, context)
    if context.user_data.get('collecting_materials') and context.user_data.get('material_type') == 'audio':
        await update.message.reply_text(L(lang, 'coming_soon_audio'))
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(L(lang, 'done'), callback_data='addm:done'), InlineKeyboardButton(L(lang, 'cancel'), callback_data='addm:cancel')]])
        await update.message.reply_text(L(lang, 'materials_saved_more'), reply_markup=kb)
    else:
        await update.message.reply_text(L(lang, 'use_add_materials_first'))


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _get_lang(update, context)
    if context.user_data.get('collecting_materials') and context.user_data.get('material_type') == 'video':
        await update.message.reply_text(L(lang, 'coming_soon_video'))
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(L(lang, 'done'), callback_data='addm:done'), InlineKeyboardButton(L(lang, 'cancel'), callback_data='addm:cancel')]])
        await update.message.reply_text(L(lang, 'materials_saved_more'), reply_markup=kb)
    else:
        await update.message.reply_text(L(lang, 'use_add_materials_first'))


# /my_data -------------------------------------------------------------------
async def my_data_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _get_lang(update, context)
    settings = get_settings()
    if settings.public_url:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(L('en', 'open_app'), web_app=WebAppInfo(url=f"{settings.public_url}/miniapp"))]])
    else:
        kb = None
    await update.message.reply_text(L(lang, 'my_data_text'), reply_markup=kb)

# ---------------------------------------------------------------------------
# Main entry
def main() -> None:
    """Run the Telegram bot."""
    settings = get_settings()
    token = settings.telegram_bot_token
    if not token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")
    async def _post_init(app: Application) -> None:
        # Register bot commands in EN and RU
        en_cmds = [
            BotCommand("start", "Welcome and menu"),
            BotCommand("mode", "Toggle One-to-One/Curate"),
            BotCommand("help", "Usage and features"),
        
            BotCommand("lang", "Choose language"),
        ]
        ru_cmds = [
            BotCommand("start", "Старт и меню"),
            BotCommand("mode", "Переключение One-to-One/Curate"),
            BotCommand("help", "Справка и команды"),
        
            BotCommand("lang", "Выбор языка"),
        ]
        await app.bot.set_my_commands(en_cmds)
        await app.bot.set_my_commands(ru_cmds, language_code="ru")
        # Extend commands set with more actions
        extended_en = en_cmds + [
            BotCommand("menu", "Actions and commands"),
            BotCommand("settings", "Configure language/level/tone"),
            BotCommand("create_project", "Create a new project"),
            BotCommand("open_project", "Open an existing project"),
            BotCommand("add_materials", "Add materials"),
            BotCommand("my_data", "Your materials (alpha)"),
        ]
        extended_ru = ru_cmds + [
            BotCommand("menu", "Действия и команды"),
            BotCommand("settings", "Язык/уровень/тональность"),
            BotCommand("create_project", "Создать проект"),
            BotCommand("open_project", "Открыть проект"),
            BotCommand("add_materials", "Добавить материалы"),
            BotCommand("my_data", "Мои данные (alpha)"),
        ]
        await app.bot.set_my_commands(extended_en)
        await app.bot.set_my_commands(extended_ru, language_code="ru")
        # Set the Telegram chat menu button to open the Mini App (native WebApp)
        if settings.public_url:
            await app.bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text=L("en", "open_app"),
                    web_app=WebAppInfo(url=f"{settings.public_url}/miniapp"),
                )
            )
    app = Application.builder().token(token).post_init(_post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mode", mode))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("lang", lang_cmd))
    app.add_handler(CallbackQueryHandler(setlang_cb, pattern="^setlang:(en|ru)$"))
    app.add_handler(CallbackQueryHandler(process_now_cb, pattern="^process$"))
    # Block 2 commands
    app.add_handler(CommandHandler("create_project", create_project_cmd))
    app.add_handler(CommandHandler("open_project", open_project_cmd))
    app.add_handler(CommandHandler("add_materials", add_materials_cmd))
    app.add_handler(CommandHandler("my_data", my_data_cmd))
    # Block 2 callbacks
    app.add_handler(CallbackQueryHandler(cproj_cb, pattern="^cproj:(start|confirm|cancel)$"))
    app.add_handler(CallbackQueryHandler(addm_cb, pattern="^addm:(open|type:(text|image|audio|video)|done|cancel)$"))
    app.add_handler(CallbackQueryHandler(openp_cb, pattern="^openp:(current)$"))
    # Separate handler for forwarded text messages
    app.add_handler(
        MessageHandler(filters.TEXT & filters.FORWARDED, handle_text)
    )
    # And for regular text messages
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.FORWARDED, handle_text)
    )
    # Media handlers for materials
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE, handle_audio))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.run_polling()
if __name__ == "__main__":
    setup_logging()
    main()

