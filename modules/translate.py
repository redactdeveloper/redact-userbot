import html

import aiohttp
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import providers
import owners
from config import AI_MODEL, PREFIXES

HELP = {
    "description": "Перевод текста через ИИ",
    "commands": {
        ".tr [lang] <text>": "перевести (по умолчанию ru; или реплай)",
    },
}


async def _translate(text: str, target: str) -> str:
    prompt = (
        f"Переведи следующий текст на язык '{target}'. "
        "Ответь только переводом, без кавычек и комментариев:\n\n"
        f"{text}"
    )
    messages = [{"role": "user", "content": prompt}]
    answer = await providers.chat(AI_MODEL, messages, timeout_s=60)
    return (answer or "").strip()


async def translate_handler(client: Client, message: Message):
    parts = (message.text or "").split(maxsplit=2)
    target = "ru"
    text = ""
    if len(parts) >= 2 and len(parts[1]) == 2 and parts[1].isalpha():
        target = parts[1].lower()
        text = parts[2] if len(parts) > 2 else ""
    elif len(parts) > 1:
        text = (message.text or "").split(maxsplit=1)[1]

    if not text and message.reply_to_message:
        text = (
            message.reply_to_message.text
            or message.reply_to_message.caption
            or ""
        )
    text = text.strip()

    if not text:
        await message.edit_text(
            "Использование: <code>.tr [lang] текст</code> или реплай",
            parse_mode=ParseMode.HTML,
        )
        return

    await message.edit_text("<i>перевожу...</i>", parse_mode=ParseMode.HTML)
    try:
        translated = await _translate(text, target)
    except Exception as e:
        await message.edit_text(
            f"<b>Ошибка:</b> <code>{html.escape(str(e))}</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    out = f"<b>→ {html.escape(target)}:</b>\n{html.escape(translated)}"
    await message.edit_text(out, parse_mode=ParseMode.HTML)


def register(app: Client):
    app.add_handler(
        MessageHandler(
            translate_handler,
            owners.auth & filters.command(["tr", "translate"], prefixes=PREFIXES),
        )
    )
