import html

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "Показать ID чата/пользователя/сообщения",
    "commands": {".id": "показать (или от реплая)"},
}


async def id_handler(client: Client, message: Message):
    lines = [f"<b>Chat:</b> <code>{message.chat.id}</code>"]
    if message.chat.title:
        lines.append(f"<b>Title:</b> {html.escape(message.chat.title)}")

    if message.reply_to_message:
        r = message.reply_to_message
        if r.from_user:
            name = r.from_user.first_name or r.from_user.username or "?"
            lines.append(
                f"<b>User:</b> <code>{r.from_user.id}</code> ({html.escape(name)})"
            )
        elif r.sender_chat:
            lines.append(f"<b>Sender chat:</b> <code>{r.sender_chat.id}</code>")
        lines.append(f"<b>Message:</b> <code>{r.id}</code>")
    else:
        if message.from_user:
            lines.append(f"<b>Your ID:</b> <code>{message.from_user.id}</code>")
        lines.append(f"<b>Message:</b> <code>{message.id}</code>")

    await message.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)


def register(app: Client):
    app.add_handler(
        MessageHandler(
            id_handler,
            owners.auth & filters.command("id", prefixes=PREFIXES),
        )
    )
