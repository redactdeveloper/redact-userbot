import asyncio
from datetime import datetime

from pyrogram import Client
from pyrogram.errors import FloodWait

from config import BIO_INTERVAL, BIO_TEMPLATE, BIO_TIME_FORMAT

HELP = {
    "description": "Автообновление био отключено",
    "commands": {},
}

ENABLED = False

_task: asyncio.Task | None = None


async def _loop(app: Client):
    while True:
        bio = BIO_TEMPLATE.format(ts=datetime.now().strftime(BIO_TIME_FORMAT))
        try:
            await app.update_profile(bio=bio)
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            continue
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[bio] ошибка: {e}")
        await asyncio.sleep(BIO_INTERVAL)


def register(app: Client):
    pass


async def on_start(app: Client):
    global _task
    if not ENABLED:
        return
    _task = asyncio.create_task(_loop(app))


async def on_stop(app: Client):
    global _task
    if _task and not _task.done():
        _task.cancel()
        try:
            await _task
        except (asyncio.CancelledError, Exception):
            pass
    _task = None
