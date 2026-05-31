import asyncio

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "Быстрая рассылка одного сообщения N раз",
    "commands": {".spam <N> <text>": "отправить N копий текста"},
}

MAX_COUNT = 200
INTERVAL = 0.08


async def spam_handler(client: Client, message: Message):
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.edit_text(
            "Использование: <code>.spam N текст</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    try:
        count = int(parts[1])
    except ValueError:
        await message.edit_text(
            "Первый аргумент должен быть числом",
            parse_mode=ParseMode.HTML,
        )
        return

    count = max(1, min(count, MAX_COUNT))
    text = parts[2]
    chat_id = message.chat.id

    try:
        await message.delete()
    except Exception:
        pass

    for _ in range(count):
        while True:
            try:
                await client.send_message(
                    chat_id, text, parse_mode=ParseMode.DISABLED
                )
                break
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
            except Exception:
                return
        await asyncio.sleep(INTERVAL)


def register(app: Client):
    app.add_handler(
        MessageHandler(
            spam_handler,
            owners.auth & filters.command("spam", prefixes=PREFIXES),
        )
    )
