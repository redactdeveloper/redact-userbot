import asyncio

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "ASCII-анимация загрузки с прогресс-баром",
    "commands": {".dance": "запустить"},
}

FRAMES = [
    "(>'-')>",
    "<('-'<)",
    "^('-')^",
    "<('-'<)",
]

STEPS = 14
INTERVAL = 0.45
BAR_WIDTH = 12


def _bar(progress: float) -> str:
    filled = int(progress * BAR_WIDTH)
    return "[" + "#" * filled + "-" * (BAR_WIDTH - filled) + "]"


async def dance_handler(client: Client, message: Message):
    for i in range(STEPS + 1):
        progress = i / STEPS
        frame = FRAMES[i % len(FRAMES)]
        text = f"{frame}  {_bar(progress)} {int(progress * 100):3d}%"
        try:
            await message.edit_text(text, parse_mode=ParseMode.DISABLED)
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
        except Exception:
            return
        if i < STEPS:
            await asyncio.sleep(INTERVAL)

    try:
        await message.edit_text(
            "(^_^)v  done!",
            parse_mode=ParseMode.DISABLED,
        )
    except Exception:
        pass


def register(app: Client):
    app.add_handler(
        MessageHandler(
            dance_handler,
            owners.auth & filters.command("dance", prefixes=PREFIXES),
        )
    )
