from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import owners
from config import PREFIXES
from modules.commands import commands_handler

HELP = {
    "description": "Алиас для списка модулей",
    "commands": {".help": "показать список"},
}


async def help_handler(client: Client, message: Message):
    await commands_handler(client, message)


def register(app: Client):
    app.add_handler(
        MessageHandler(
            help_handler,
            owners.auth & filters.command("help", prefixes=PREFIXES),
        ),
        group=-10,
    )
