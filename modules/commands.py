import sys

from pyrogram import Client, filters
from pyrogram.enums import MessageEntityType, ParseMode
from pyrogram.errors import FloodWait
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message, MessageEntity

import owners
from config import PREFIXES

HELP = {
    "description": "Список всех модулей и команд",
    "commands": {".modules": "показать список"},
}

MAX_MSG_CHARS = 3500
EXPAND_THRESHOLD = 180

_EXPANDABLE_BQ = getattr(
    MessageEntityType, "EXPANDABLE_BLOCKQUOTE", MessageEntityType.BLOCKQUOTE
)


def _utf16_len(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


def _collect() -> list[tuple[str, str, dict[str, str]]]:
    result = []
    for full_name in sorted(sys.modules):
        if not full_name.startswith("modules."):
            continue
        short = full_name.split(".", 1)[1]
        if not short or "." in short:
            continue
        mod = sys.modules[full_name]
        help_data = getattr(mod, "HELP", None)
        desc = "—"
        cmds: dict[str, str] = {}
        if isinstance(help_data, dict):
            desc = help_data.get("description") or desc
            cmds = help_data.get("commands") or {}
        result.append((short, desc, cmds))
    return result


def _module_text_len(mod: tuple[str, str, dict[str, str]]) -> int:
    name, desc, cmds = mod
    total = len(name) + 3 + len(desc)
    if cmds:
        for cmd, cdesc in cmds.items():
            total += 4 + len(cmd) + 3 + len(cdesc)
    else:
        total += 4 + len("(фоновый)")
    return total


def _build(
    modules_info: list[tuple[str, str, dict[str, str]]],
    header_text: str | None,
) -> tuple[str, list[MessageEntity]]:
    chunks: list[str] = []
    entities: list[MessageEntity] = []
    offset = 0

    def emit(s: str):
        nonlocal offset
        chunks.append(s)
        offset += _utf16_len(s)

    def bold(s: str):
        entities.append(
            MessageEntity(
                type=MessageEntityType.BOLD, offset=offset, length=_utf16_len(s)
            )
        )
        emit(s)

    if header_text:
        bold(header_text)
        emit("\n")

    for i, mod in enumerate(modules_info):
        name, desc, cmds = mod
        if i > 0 or header_text:
            emit("\n")
        block_start = offset
        bold(name)
        emit(" — ")
        emit(desc)

        if cmds:
            for cmd, cdesc in cmds.items():
                emit("\n   ")
                emit(cmd)
                emit(" — ")
                emit(cdesc)
        else:
            emit("\n   ")
            emit("(фоновый)")

        bq_type = (
            _EXPANDABLE_BQ
            if _module_text_len(mod) >= EXPAND_THRESHOLD
            else MessageEntityType.BLOCKQUOTE
        )
        entities.append(
            MessageEntity(
                type=bq_type,
                offset=block_start,
                length=offset - block_start,
            )
        )

    return "".join(chunks), entities


def _batch(
    modules_info: list[tuple[str, str, dict[str, str]]],
) -> list[list[tuple[str, str, dict[str, str]]]]:
    batches: list[list] = [[]]
    current_chars = 0
    header_chars = len(f"Модули ({len(modules_info)}):") + 2
    budget = MAX_MSG_CHARS - header_chars
    for mod in modules_info:
        mod_chars = _module_text_len(mod) + 2
        if batches[-1] and current_chars + mod_chars > budget:
            batches.append([])
            current_chars = 0
            budget = MAX_MSG_CHARS
        batches[-1].append(mod)
        current_chars += mod_chars
    return batches


async def commands_handler(client: Client, message: Message):
    modules_info = _collect()
    total = len(modules_info)
    batch = _batch(modules_info)[0]
    hidden = total - len(batch)
    header = f"Модули ({total})"
    if hidden > 0:
        header += f", показано {len(batch)}"
    header += ":"
    text, entities = _build(batch, header)
    if hidden > 0:
        text += f"\n\n...ещё {hidden}. Используй конкретную команду модуля."

    try:
        await message.edit_text(
            text,
            entities=entities,
            parse_mode=ParseMode.DISABLED,
        )
    except FloodWait as e:
        print(f"[commands] flood wait: {e.value}s", flush=True)


def register(app: Client):
    app.add_handler(
        MessageHandler(
            commands_handler,
            owners.auth & filters.command("modules", prefixes=PREFIXES),
        )
    )
