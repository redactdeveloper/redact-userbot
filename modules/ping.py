import random
import time

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.raw.functions import Ping
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "Замер MTProto-задержки до Telegram",
    "commands": {".ping": "pong + latency в ms"},
}


async def measure_ping(client: Client) -> float:
    start = time.perf_counter()
    await client.invoke(Ping(ping_id=random.randint(-(2**63), 2**63 - 1)))
    return (time.perf_counter() - start) * 1000


async def ping_handler(client: Client, message: Message):
    ms = await measure_ping(client)
    await message.edit_text(
        f"<b>Pong!</b> <code>{ms:.2f} ms</code>",
        parse_mode=ParseMode.HTML,
    )


def register(app: Client):
    app.add_handler(
        MessageHandler(
            ping_handler,
            owners.auth & filters.command("ping", prefixes=PREFIXES),
        )
    )
