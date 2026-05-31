import html

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "Управление доступом к командам (whitelist)",
    "commands": {
        ".owner": "показать список",
        ".owner add <@user|reply|id>": "дать доступ",
        ".owner rm <@user|reply|id>": "забрать доступ",
    },
}


async def _resolve(client: Client, message: Message, arg: str) -> int | None:
    if arg:
        try:
            u = await client.get_users(arg)
            if isinstance(u, list):
                u = u[0] if u else None
            if u:
                return u.id
        except Exception:
            pass
        try:
            return int(arg)
        except ValueError:
            return None
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id
    return None


async def _show_list(client: Client, message: Message):
    ids = sorted(owners.get_owners())
    if not ids:
        await message.edit_text(
            "<i>Доступ: только ты</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    lines = [f"<b>Owners ({len(ids)}):</b>", ""]
    try:
        users = await client.get_users(ids)
        if not isinstance(users, list):
            users = [users]
    except Exception:
        users = []

    name_by_id = {
        u.id: (u.first_name or u.username or f"id{u.id}") for u in users
    }
    for uid in ids:
        name = name_by_id.get(uid, f"id{uid}")
        lines.append(f"<code>{uid}</code> — {html.escape(name)}")
    await message.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def owner_handler(client: Client, message: Message):
    parts = (message.text or "").split(maxsplit=2)

    if len(parts) == 1:
        await _show_list(client, message)
        return

    action = parts[1].lower()
    target_arg = parts[2].strip() if len(parts) > 2 else ""

    if action == "list":
        await _show_list(client, message)
        return

    if action not in ("add", "rm", "del", "remove"):
        await message.edit_text(
            "Использование: <code>.owner add|rm @user</code> или реплай",
            parse_mode=ParseMode.HTML,
        )
        return

    uid = await _resolve(client, message, target_arg)
    if not uid:
        await message.edit_text(
            "Не удалось найти пользователя",
            parse_mode=ParseMode.HTML,
        )
        return

    if action == "add":
        owners.add_owner(uid)
        await message.edit_text(
            f"<b>Owner добавлен:</b> <code>{uid}</code>",
            parse_mode=ParseMode.HTML,
        )
    else:
        owners.remove_owner(uid)
        await message.edit_text(
            f"<b>Owner удалён:</b> <code>{uid}</code>",
            parse_mode=ParseMode.HTML,
        )


def register(app: Client):
    app.add_handler(
        MessageHandler(
            owner_handler,
            owners.auth & filters.command("owner", prefixes=PREFIXES),
        )
    )
