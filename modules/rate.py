import asyncio

import aiohttp
from pyrogram import Client
from pyrogram.errors import FloodWait

HELP = {
    "description": "Курс USD в last_name отключен",
    "commands": {},
}

URL = "https://www.cbr-xml-daily.ru/daily_json.js"
INTERVAL = 60 * 15
TEMPLATE = "${usd:.2f}₽"
ENABLED = False

_task: asyncio.Task | None = None


async def _fetch_usd() -> float | None:
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.get(URL) as r:
            r.raise_for_status()
            data = await r.json(content_type=None)
    return float(data["Valute"]["USD"]["Value"])


async def _loop(app: Client):
    while True:
        try:
            usd = await _fetch_usd()
            await app.update_profile(last_name=TEMPLATE.format(usd=usd))
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            continue
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[rate] ошибка: {e}")
        await asyncio.sleep(INTERVAL)


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
