import html
import os
import time
from pathlib import Path

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "Скачать медиа из реплая на сервер",
    "commands": {".download": "скачать (реплай на медиа)"},
}

DOWNLOADS_DIR = Path(__file__).parent.parent / "downloads"


def _fmt_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


async def download_handler(client: Client, message: Message):
    r = message.reply_to_message
    if not r or not r.media:
        await message.edit_text(
            "Нужен реплай на медиа",
            parse_mode=ParseMode.HTML,
        )
        return

    DOWNLOADS_DIR.mkdir(exist_ok=True)
    await message.edit_text("<i>скачиваю...</i>", parse_mode=ParseMode.HTML)
    start = time.perf_counter()
    try:
        path = await r.download(file_name=str(DOWNLOADS_DIR) + "/")
    except Exception as e:
        await message.edit_text(
            f"<b>Ошибка:</b> <code>{html.escape(str(e))}</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    elapsed = time.perf_counter() - start
    size = os.path.getsize(path)
    await message.edit_text(
        "<b>Скачано</b>\n"
        f"<b>Path:</b> <code>{html.escape(str(path))}</code>\n"
        f"<b>Size:</b> {_fmt_size(size)}\n"
        f"<b>Time:</b> {elapsed:.2f}s",
        parse_mode=ParseMode.HTML,
    )


def register(app: Client):
    app.add_handler(
        MessageHandler(
            download_handler,
            owners.auth & filters.command(["download", "dl"], prefixes=PREFIXES),
        )
    )
