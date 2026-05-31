import asyncio

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "Удалить сообщения",
    "commands": {
        ".purge": "от реплая до текущего",
        ".purge <N>": "последние N сообщений",
    },
}


async def purge_handler(client: Client, message: Message):
    ids: list[int] = []
    chat_id = message.chat.id

    if message.reply_to_message:
        start_id = message.reply_to_message.id
        end_id = message.id
        ids = list(range(start_id, end_id + 1))
    else:
        parts = (message.text or "").split(maxsplit=1)
        try:
            n = int(parts[1]) if len(parts) > 1 else 1
        except ValueError:
            await message.edit_text(
                "Использование: <code>.purge N</code> или реплай",
                parse_mode=ParseMode.HTML,
            )
            return
        async for m in client.get_chat_history(chat_id, limit=n + 1):
            ids.append(m.id)

    for i in range(0, len(ids), 100):
        chunk = ids[i : i + 100]
        while True:
            try:
                await client.delete_messages(chat_id, chunk)
                break
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
            except Exception:
                break


def register(app: Client):
    app.add_handler(
        MessageHandler(
            purge_handler,
            owners.auth & filters.command("purge", prefixes=PREFIXES),
        )
    )
