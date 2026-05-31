import html
import json
import time
from collections import OrderedDict
from pathlib import Path

from pyrogram import Client, filters
from pyrogram.enums import ChatType, ParseMode
from pyrogram.handlers import DeletedMessagesHandler, MessageHandler
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "Лог удалённых сообщений из личек (все типы медиа)",
    "commands": {
        ".logdelete": "переключить (on/off)",
        ".logdelete here": "слать лог в текущий чат",
        ".logdelete me": "слать в Saved Messages",
    },
}


MEDIA_TYPES = [
    ("sticker", "стикер"),
    ("photo", "фото"),
    ("video", "видео"),
    ("voice", "голосовое"),
    ("video_note", "кружок"),
    ("animation", "гифка"),
    ("audio", "аудио"),
    ("document", "документ"),
]

_STATE_FILE = Path(__file__).parent.parent / ".logdelete_state.json"
CACHE_SIZE = 10000
MAX_TEXT_LEN = 1500


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text())
        except Exception:
            pass
    return {"enabled": False, "target": "me"}


def _save_state(state: dict):
    _STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


_state = _load_state()
_cache: "OrderedDict[tuple[int, int], dict]" = OrderedDict()


def _cache_put(chat_id: int, msg_id: int, entry: dict):
    key = (chat_id, msg_id)
    if key in _cache:
        _cache.move_to_end(key)
    _cache[key] = entry
    while len(_cache) > CACHE_SIZE:
        _cache.popitem(last=False)


def _cache_get(chat_id: int, msg_id: int) -> dict | None:
    return _cache.get((chat_id, msg_id))


async def toggle_handler(client: Client, message: Message):
    parts = (message.text or "").split(maxsplit=1)
    arg = parts[1].strip().lower() if len(parts) > 1 else ""

    if arg == "here":
        _state["target"] = message.chat.id
        _save_state(_state)
        await message.edit_text(
            f"<b>Лог будет идти сюда</b>\n<code>{message.chat.id}</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    if arg == "me":
        _state["target"] = "me"
        _save_state(_state)
        await message.edit_text(
            "<b>Лог будет в Saved Messages</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    if arg == "on":
        _state["enabled"] = True
    elif arg == "off":
        _state["enabled"] = False
    else:
        _state["enabled"] = not _state.get("enabled", False)
    _save_state(_state)

    status = "включён" if _state["enabled"] else "выключен"
    target = _state.get("target", "me")
    await message.edit_text(
        f"<b>Log delete {status}</b>\n<b>Цель:</b> <code>{target}</code>",
        parse_mode=ParseMode.HTML,
    )


async def capture_handler(client: Client, message: Message):
    if not _state.get("enabled"):
        return
    if message.chat.type != ChatType.PRIVATE:
        return

    media_type = None
    media_extra = ""
    for attr, label in MEDIA_TYPES:
        obj = getattr(message, attr, None)
        if obj:
            media_type = label
            if attr == "sticker":
                media_extra = obj.emoji or ""
            break

    text = message.text or message.caption or ""
    if not text and not media_type:
        return

    from_id = None
    name = "?"
    if message.from_user:
        from_id = message.from_user.id
        name = (
            message.from_user.first_name
            or message.from_user.username
            or f"id{from_id}"
        )
    elif message.sender_chat:
        from_id = message.sender_chat.id
        name = message.sender_chat.title or f"chat{from_id}"

    _cache_put(
        message.chat.id,
        message.id,
        {
            "text": text,
            "media_type": media_type,
            "media_extra": media_extra,
            "from_id": from_id,
            "from_name": name,
            "chat_id": message.chat.id,
            "chat_title": message.chat.title or "",
            "chat_username": message.chat.username or "",
            "date": message.date.timestamp() if message.date else time.time(),
        },
    )


async def delete_handler(client: Client, messages):
    if not _state.get("enabled"):
        return
    target = _state.get("target", "me")

    for m in messages:
        chat_id = m.chat.id if m.chat else 0
        entry = _cache_get(chat_id, m.id)
        if not entry:
            continue

        chat_label = (
            entry["chat_title"]
            or entry["chat_username"]
            or entry["from_name"]
            or f"id{entry['chat_id']}"
        )

        lines = [
            f"<b>Удалено в ЛС с</b> {html.escape(chat_label)}",
        ]
        from_line = f"<b>От:</b> {html.escape(entry['from_name'])}"
        if entry["from_id"]:
            from_line += f" · <code>{entry['from_id']}</code>"
        lines.append(from_line)

        if entry.get("media_type"):
            media_line = f"<b>Тип:</b> {html.escape(entry['media_type'])}"
            if entry.get("media_extra"):
                media_line += f" {html.escape(entry['media_extra'])}"
            lines.append(media_line)

        if entry["text"]:
            text = entry["text"][:MAX_TEXT_LEN]
            label = "Подпись" if entry.get("media_type") else "Текст"
            lines.append(
                f"<b>{label}:</b>\n<blockquote>{html.escape(text)}</blockquote>"
            )

        out = "\n".join(lines)
        try:
            await client.send_message(target, out, parse_mode=ParseMode.HTML)
        except Exception as e:
            print(f"[logdelete] send error: {e}")

        _cache.pop((chat_id, m.id), None)


def register(app: Client):
    app.add_handler(
        MessageHandler(
            toggle_handler,
            owners.auth & filters.command("logdelete", prefixes=PREFIXES),
        )
    )
    app.add_handler(
        MessageHandler(capture_handler, filters.private),
        group=5,
    )
    app.add_handler(DeletedMessagesHandler(delete_handler), group=5)
