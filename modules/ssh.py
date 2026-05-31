import asyncio
import html
import time

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "Выполнить shell-команду на хосте userbot'а",
    "commands": {
        ".ssh <cmd>": "выполнить команду и показать вывод",
    },
}

TG_LIMIT = 3800
TIMEOUT = 60


async def ssh_handler(client: Client, message: Message):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.edit_text(
            "Использование: <code>.ssh команда</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    cmd = parts[1]
    await message.edit_text("<i>выполняю...</i>", parse_mode=ParseMode.HTML)

    start = time.perf_counter()
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except Exception as e:
        await message.edit_text(
            f"<b>Ошибка запуска:</b> <code>{html.escape(str(e))}</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    try:
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(), timeout=TIMEOUT
        )
    except asyncio.TimeoutError:
        try:
            proc.kill()
            await proc.wait()
        except Exception:
            pass
        await message.edit_text(
            f"<b>Таймаут {TIMEOUT}s</b> · процесс убит",
            parse_mode=ParseMode.HTML,
        )
        return

    elapsed = time.perf_counter() - start
    rc = proc.returncode
    out = (stdout_b or b"").decode("utf-8", errors="replace").rstrip()
    err = (stderr_b or b"").decode("utf-8", errors="replace").rstrip()

    body = out
    if err:
        body = f"{body}\n--- stderr ---\n{err}" if body else err
    if not body:
        body = "(no output)"

    if len(body) > TG_LIMIT:
        body = body[:TG_LIMIT] + "\n...[обрезано]"

    text = (
        f"<code>$ {html.escape(cmd)}</code>\n"
        f"<pre>{html.escape(body)}</pre>\n"
        f"<i>exit={rc} · {elapsed:.2f}s</i>"
    )
    await message.edit_text(text, parse_mode=ParseMode.HTML)


def register(app: Client):
    app.add_handler(
        MessageHandler(
            ssh_handler,
            owners.auth & filters.command(["ssh", "sh"], prefixes=PREFIXES),
        )
    )
