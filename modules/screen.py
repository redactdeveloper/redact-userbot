import asyncio
import html
import os
import shutil
import tempfile
from typing import Callable

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "Скриншот хоста userbot'а",
    "commands": {".screen": "сделать скрин и отправить файлом"},
}


CmdBuilder = Callable[[str], list[str]]

CANDIDATES: list[tuple[str, CmdBuilder]] = [
    ("grimblast", lambda p: ["grimblast", "save", "screen", p]),
    ("hyprshot", lambda p: ["hyprshot", "-m", "output", "-o", os.path.dirname(p), "-f", os.path.basename(p), "-s"]),
    ("grim", lambda p: ["grim", p]),
    ("wayshot", lambda p: ["wayshot", "-f", p]),
    ("scrot", lambda p: ["scrot", "-z", "-o", p]),
    ("gnome-screenshot", lambda p: ["gnome-screenshot", "-f", p]),
    ("spectacle", lambda p: ["spectacle", "-b", "-n", "-o", p]),
    ("maim", lambda p: ["maim", p]),
]


def _ensure_env() -> dict:
    env = os.environ.copy()
    runtime_dir = env.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    if os.path.isdir(runtime_dir):
        env.setdefault("XDG_RUNTIME_DIR", runtime_dir)
        if not env.get("WAYLAND_DISPLAY"):
            try:
                for name in sorted(os.listdir(runtime_dir)):
                    if name.startswith("wayland-") and not name.endswith(".lock"):
                        env["WAYLAND_DISPLAY"] = name
                        break
            except OSError:
                pass
    if not env.get("DISPLAY"):
        env.setdefault("DISPLAY", ":0")
    return env


def _available() -> list[tuple[str, CmdBuilder]]:
    return [(n, b) for n, b in CANDIDATES if shutil.which(n)]


async def _take(path: str) -> tuple[bool, str]:
    avail = _available()
    if not avail:
        return False, (
            "нет инструментов. поставь что-то из: grim, grimblast, "
            "hyprshot, scrot, gnome-screenshot, maim"
        )

    env = _ensure_env()
    errors: list[str] = []
    for name, builder in avail:
        cmd = builder(path)
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
        except FileNotFoundError:
            errors.append(f"{name}: not found")
            continue
        try:
            _, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=8)
        except asyncio.TimeoutError:
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
            errors.append(f"{name}: timeout")
            continue
        if proc.returncode == 0 and os.path.isfile(path) and os.path.getsize(path) > 0:
            return True, name
        msg = (stderr_b or b"").decode("utf-8", errors="replace").strip()
        msg = msg.replace("\n", " ")[:100]
        errors.append(f"{name}: {msg or f'rc={proc.returncode}'}")
        try:
            if os.path.exists(path):
                os.unlink(path)
        except Exception:
            pass

    return False, " · ".join(errors)


async def screen_handler(client: Client, message: Message):
    await message.edit_text("<i>делаю скрин...</i>", parse_mode=ParseMode.HTML)

    fd, path = tempfile.mkstemp(suffix=".png", prefix="screen_")
    os.close(fd)
    try:
        os.unlink(path)
    except Exception:
        pass

    ok, info = await _take(path)
    if not ok:
        await message.edit_text(
            f"<b>Не удалось:</b> <code>{html.escape(info)}</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    chat_id = message.chat.id
    reply_to = message.reply_to_message.id if message.reply_to_message else None
    try:
        await message.delete()
    except Exception:
        pass

    try:
        await client.send_document(
            chat_id,
            document=path,
            caption=f"screen · {info}",
            reply_to_message_id=reply_to,
        )
    except Exception as e:
        try:
            await client.send_message(
                chat_id,
                f"<b>Ошибка отправки:</b> <code>{html.escape(str(e))}</code>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


def register(app: Client):
    app.add_handler(
        MessageHandler(
            screen_handler,
            owners.auth & filters.command("screen", prefixes=PREFIXES),
        )
    )
