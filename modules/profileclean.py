from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "Очистка био и фамилии профиля",
    "commands": {".profileclean": "очистить bio и last_name"},
}


async def profileclean_handler(client: Client, message: Message):
    await client.update_profile(last_name="", bio="")
    await message.edit_text(
        "<b>Профиль очищен:</b> bio и last_name пустые",
        parse_mode=ParseMode.HTML,
    )


def register(app: Client):
    app.add_handler(
        MessageHandler(
            profileclean_handler,
            owners.auth & filters.command("profileclean", prefixes=PREFIXES),
        )
    )
