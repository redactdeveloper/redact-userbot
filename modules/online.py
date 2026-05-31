import asyncio
import json
from pathlib import Path

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.raw.functions.account import UpdateStatus
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "Постоянный онлайн-статус",
    "commands": {
        ".online": "переключить",
        ".online on": "включить",
        ".online off": "выключить",
    },
}

INTERVAL = 50
_STATE_FILE = Path(__file__).parent.parent / ".online_state.json"

_task: asyncio.Task | None = None


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text())
        except Exception:
            pass
    return {"enabled": False}


def _save_state(state: dict):
    _STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


_state = _load_state()


async def _loop(app: Client):
    while True:
        try:
            await app.invoke(UpdateStatus(offline=False))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[online] ошибка: {e}")
        try:
            await asyncio.sleep(INTERVAL)
        except asyncio.CancelledError:
            raise


def _start(app: Client):
    global _task
    if _task and not _task.done():
        return
    _task = asyncio.create_task(_loop(app))


async def _stop_task():
    global _task
    if _task and not _task.done():
        _task.cancel()
        try:
            await _task
        except (asyncio.CancelledError, Exception):
            pass
    _task = None


async def toggle_handler(client: Client, message: Message):
    parts = (message.text or "").split(maxsplit=1)
    arg = parts[1].strip().lower() if len(parts) > 1 else ""

    if arg == "on":
        _state["enabled"] = True
    elif arg == "off":
        _state["enabled"] = False
    else:
        _state["enabled"] = not _state.get("enabled", False)
    _save_state(_state)

    if _state["enabled"]:
        _start(client)
        text = "<b>Online:</b> включён"
    else:
        await _stop_task()
        try:
            await client.invoke(UpdateStatus(offline=True))
        except Exception:
            pass
        text = "<b>Online:</b> выключен"

    await message.edit_text(text, parse_mode=ParseMode.HTML)


def register(app: Client):
    app.add_handler(
        MessageHandler(
            toggle_handler,
            owners.auth & filters.command("online", prefixes=PREFIXES),
        )
    )


async def on_start(app: Client):
    if _state.get("enabled"):
        _start(app)


async def on_stop(app: Client):
    await _stop_task()
