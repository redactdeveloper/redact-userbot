import html
import time

from pyrogram import Client, filters
from pyrogram.enums import ChatType, ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "AFK режим с автоответом на упоминания/личку",
    "commands": {
        ".afk [причина]": "включить",
        ".unafk": "выключить",
    },
}

REPLY_COOLDOWN = 300

_state = {"enabled": False, "since": 0.0, "reason": ""}
_replied: dict[int, float] = {}


def _fmt_duration(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}ч {m}м"
    if m:
        return f"{m}м"
    return f"{s}с"


async def afk_on(client: Client, message: Message):
    parts = (message.text or "").split(maxsplit=1)
    reason = parts[1].strip() if len(parts) > 1 else ""
    _state["enabled"] = True
    _state["since"] = time.time()
    _state["reason"] = reason
    _replied.clear()
    text = "<b>AFK:</b> включён"
    if reason:
        text += f"\n<b>Причина:</b> {html.escape(reason)}"
    await message.edit_text(text, parse_mode=ParseMode.HTML)


async def afk_off(client: Client, message: Message):
    if not _state["enabled"]:
        await message.edit_text("AFK не активен", parse_mode=ParseMode.HTML)
        return
    elapsed = _fmt_duration(time.time() - _state["since"])
    _state["enabled"] = False
    _state["reason"] = ""
    _replied.clear()
    await message.edit_text(
        f"<b>AFK:</b> выключен (был: {elapsed})",
        parse_mode=ParseMode.HTML,
    )


async def afk_responder(client: Client, message: Message):
    if not _state["enabled"]:
        return
    if message.outgoing:
        return
    if message.from_user and message.from_user.is_self:
        return
    if message.from_user and message.from_user.is_bot:
        return

    me_id = client.me.id if client.me else 0
    if message.chat.type != ChatType.PRIVATE:
        mentioned = bool(message.mentioned)
        if not mentioned and message.reply_to_message:
            ru = message.reply_to_message.from_user
            if ru and ru.id == me_id:
                mentioned = True
        if not mentioned:
            return

    now = time.time()
    last = _replied.get(message.chat.id, 0)
    if now - last < REPLY_COOLDOWN:
        return
    _replied[message.chat.id] = now

    elapsed = _fmt_duration(now - _state["since"])
    text = f"<i>Сейчас AFK ({elapsed})"
    if _state["reason"]:
        text += f"\nПричина: {html.escape(_state['reason'])}"
    text += "</i>"
    try:
        await message.reply_text(text, parse_mode=ParseMode.HTML, quote=True)
    except Exception:
        pass


def register(app: Client):
    app.add_handler(
        MessageHandler(
            afk_on,
            owners.auth & filters.command("afk", prefixes=PREFIXES),
        )
    )
    app.add_handler(
        MessageHandler(
            afk_off,
            owners.auth & filters.command("unafk", prefixes=PREFIXES),
        )
    )
    app.add_handler(
        MessageHandler(afk_responder, filters.incoming),
        group=1,
    )
