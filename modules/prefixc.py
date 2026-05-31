import html
import json
import re
from pathlib import Path

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "Дополнительные команды для любых модулей",
    "commands": {
        ".prefixc <module> <.alias>": "добавить алиас, пример: .prefixc weather .w",
        ".prefixc list": "список алиасов",
        ".prefixc del <.alias>": "удалить алиас",
        ".prefixc clear": "удалить все алиасы",
    },
}

_STATE_FILE = Path(__file__).parent.parent / ".prefixc_aliases.json"
_COMMAND_RE = re.compile(r"^[^\s]+$")


def _load() -> dict[str, str]:
    if not _STATE_FILE.exists():
        return {}
    try:
        data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}


def _save() -> None:
    _STATE_FILE.write_text(
        json.dumps(_aliases, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _strip_prefix(command: str) -> str:
    command = command.strip()
    if command and command[0] in PREFIXES:
        command = command[1:]
    return command.strip()


def _with_default_prefix(command: str) -> str:
    command = command.strip()
    if command and command[0] in PREFIXES:
        return command
    return f"{PREFIXES[0]}{command}"


def _parse_message_command(text: str) -> tuple[str, str] | None:
    text = text or ""
    if not text or text[0] not in PREFIXES:
        return None
    first, sep, rest = text.partition(" ")
    command = _strip_prefix(first).lower()
    return command, (rest if sep else "")


_aliases: dict[str, str] = _load()


async def prefixc_handler(client: Client, message: Message):
    parts = (message.text or "").split()
    if len(parts) == 1 or (len(parts) > 1 and parts[1].lower() == "list"):
        if not _aliases:
            await message.edit_text(
                "<i>Алиасов нет</i>",
                parse_mode=ParseMode.HTML,
            )
            return
        lines = ["<b>Алиасы команд:</b>", ""]
        for alias, target in sorted(_aliases.items()):
            lines.append(
                f"<code>{html.escape(_with_default_prefix(alias))}</code> → "
                f"<code>{html.escape(_with_default_prefix(target))}</code>"
            )
        await message.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)
        return

    sub = parts[1].lower()
    if sub in ("del", "rm", "remove"):
        if len(parts) < 3:
            await message.edit_text(
                "Укажи алиас: <code>.prefixc del .c</code>",
                parse_mode=ParseMode.HTML,
            )
            return
        alias = _strip_prefix(parts[2]).lower()
        if alias not in _aliases:
            await message.edit_text(
                f"Алиас <code>{html.escape(_with_default_prefix(alias))}</code> не найден",
                parse_mode=ParseMode.HTML,
            )
            return
        target = _aliases.pop(alias)
        _save()
        await message.edit_text(
            f"Удалено: <code>{html.escape(_with_default_prefix(alias))}</code> → "
            f"<code>{html.escape(_with_default_prefix(target))}</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    if sub == "clear":
        _aliases.clear()
        _save()
        await message.edit_text("Все алиасы удалены.")
        return

    if len(parts) < 3:
        await message.edit_text(
            "Использование: <code>.prefixc &lt;module&gt; &lt;.alias&gt;</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    target = _strip_prefix(parts[1]).lower()
    alias = _strip_prefix(parts[2]).lower()

    if not target or not alias or not _COMMAND_RE.match(target) or not _COMMAND_RE.match(alias):
        await message.edit_text(
            "Команды должны быть без пробелов: <code>.prefixc weather .w</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    if target == "prefixc":
        await message.edit_text("Для <code>.prefixc</code> алиас не нужен.", parse_mode=ParseMode.HTML)
        return
    if alias in ("prefixc", target):
        await message.edit_text("Такой алиас бессмысленный.", parse_mode=ParseMode.HTML)
        return

    _aliases[alias] = target
    _save()
    await message.edit_text(
        f"Добавлено: <code>{html.escape(_with_default_prefix(alias))}</code> → "
        f"<code>{html.escape(_with_default_prefix(target))}</code>",
        parse_mode=ParseMode.HTML,
    )


async def alias_router(client: Client, message: Message):
    parsed = _parse_message_command(message.text or "")
    if not parsed:
        return

    command, rest = parsed
    target = _aliases.get(command)
    if not target:
        return

    prefix = (message.text or ".")[0]
    rewritten = f"{prefix}{target}"
    if rest:
        rewritten += f" {rest}"

    message.text = rewritten
    message.command = [target, *rest.split()] if rest else [target]


def register(app: Client):
    app.add_handler(
        MessageHandler(
            alias_router,
            owners.auth & filters.text,
        ),
        group=-100,
    )
    app.add_handler(
        MessageHandler(
            prefixc_handler,
            owners.auth & filters.command("prefixc", prefixes=PREFIXES),
        )
    )
