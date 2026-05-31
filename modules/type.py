import asyncio

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "Анимированная печать текста",
    "commands": {".type <text>": "напечатать постепенно"},
}

CURSOR = "▮"
STEPS_MAX = 12
INTERVAL = 0.35


async def type_handler(client: Client, message: Message):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.edit_text(
            "Использование: <code>.type текст</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    text = parts[1]
    steps = min(STEPS_MAX, max(1, len(text)))
    for i in range(1, steps + 1):
        cut = max(1, int(len(text) * i / steps))
        try:
            await message.edit_text(
                text[:cut] + CURSOR,
                parse_mode=ParseMode.DISABLED,
            )
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
        except Exception:
            return
        await asyncio.sleep(INTERVAL)

    try:
        await message.edit_text(text, parse_mode=ParseMode.DISABLED)
    except Exception:
        pass


def register(app: Client):
    app.add_handler(
        MessageHandler(
            type_handler,
            owners.auth & filters.command("type", prefixes=PREFIXES),
        )
    )
