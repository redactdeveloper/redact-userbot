import json
import os
import sys
from pathlib import Path

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "Перезапуск userbot'а",
    "commands": {".restart": "полный рестарт процесса"},
}

_STATE_FILE = Path(__file__).parent.parent / ".restart_state.json"


async def restart_handler(client: Client, message: Message):
    await message.edit_text(
        "<i>Перезапускаюсь...</i>",
        parse_mode=ParseMode.HTML,
    )
    _STATE_FILE.write_text(
        json.dumps({"chat_id": message.chat.id, "msg_id": message.id})
    )
    try:
        await client.stop()
    except Exception:
        pass
    os.execv(sys.executable, [sys.executable] + sys.argv)


async def on_start(app: Client):
    if not _STATE_FILE.exists():
        return
    try:
        data = json.loads(_STATE_FILE.read_text())
        _STATE_FILE.unlink()
        await app.edit_message_text(
            data["chat_id"],
            data["msg_id"],
            "<b>Перезапущен.</b>",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


def register(app: Client):
    app.add_handler(
        MessageHandler(
            restart_handler,
            owners.auth & filters.command("restart", prefixes=PREFIXES),
        )
    )
