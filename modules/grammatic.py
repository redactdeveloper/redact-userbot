import html
import json
from pathlib import Path

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import providers
import owners
from config import ONLYSQ_MODEL, PREFIXES

HELP = {
    "description": "Автокоррекция грамматики в своих сообщениях",
    "commands": {
        ".grammatic": "переключить",
        ".grammatic on": "включить",
        ".grammatic off": "выключить",
    },
}

_STATE_FILE = Path(__file__).parent.parent / ".grammatic_state.json"
MIN_LEN = 3

SYSTEM_PROMPT = (
    "Ты — корректор орфографии и грамматики. "
    "Проверь текст пользователя. "
    "Если в тексте есть ошибки — верни ТОЛЬКО исправленный текст, без кавычек, без комментариев, без пояснений. "
    "Если ошибок нет — верни ровно одно слово: OK. "
    "Сохраняй исходный язык, стиль, эмодзи, ссылки и форматирование. "
    "Не меняй смысл, не перефразируй, не добавляй ничего от себя."
)


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


async def _check(text: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]
    try:
        answer = await providers.chat(ONLYSQ_MODEL, messages, timeout_s=30)
    except Exception:
        return "OK"
    return (answer or "").strip()


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

    status = "включена" if _state["enabled"] else "выключена"
    await message.edit_text(
        f"<b>Автокоррекция</b> {status}",
        parse_mode=ParseMode.HTML,
    )


async def auto_correct(client: Client, message: Message):
    if not _state.get("enabled"):
        return
    text = message.text
    if not text:
        return
    stripped = text.strip()
    if len(stripped) < MIN_LEN:
        return
    if any(stripped.startswith(p) for p in PREFIXES):
        return

    try:
        corrected = await _check(text)
    except Exception:
        return

    if not corrected:
        return
    if corrected.strip().upper() == "OK":
        return
    if corrected.strip() == text.strip():
        return

    try:
        await message.edit_text(corrected, parse_mode=ParseMode.DISABLED)
    except Exception:
        pass


def register(app: Client):
    app.add_handler(
        MessageHandler(
            toggle_handler,
            owners.auth & filters.command(["grammatic", "gram"], prefixes=PREFIXES),
        )
    )
    app.add_handler(
        MessageHandler(auto_correct, filters.me & filters.text),
        group=2,
    )
