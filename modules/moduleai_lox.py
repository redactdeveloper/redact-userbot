import html
import owners
from config import PREFIXES
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

HELP = {
    "description": "Команда .lox — на «ку» отвечает «ку»",
    "commands": {".lox": "на ку отвечает ку"},
}


async def lox_handler(client: Client, message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        user_input = args[1].strip()
    else:
        user_input = ""

    if user_input.lower() == "ку":
        await message.edit_text("<b>ку</b>", parse_mode=ParseMode.HTML)
    else:
        escaped = html.escape(user_input) if user_input else ""
        if escaped:
            await message.edit_text(
                f"<b>Ты написал:</b> {escaped}\n<i>Напиши «ку» и получишь «ку» в ответ!</i>",
                parse_mode=ParseMode.HTML,
            )
        else:
            await message.edit_text(
                "<i>Напиши</i> <code>.lox ку</code> <i>и получишь «ку» в ответ!</i>",
                parse_mode=ParseMode.HTML,
            )


def register(app: Client):
    app.add_handler(
        MessageHandler(
            lox_handler,
            owners.auth & filters.command("lox", prefixes=PREFIXES),
        )
    )