import asyncio
import glob
import os
import platform
import shutil
import socket
import subprocess
import time

import psutil
from pyrogram import Client, filters
from pyrogram.enums import MessageEntityType, ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message, MessageEntity

import owners
from config import (
    INFO_IMAGE,
    PREFIXES,
    USERBOT_BRANCH,
    USERBOT_NAME,
    USERBOT_VERSION,
)

HELP = {
    "description": "Инфа о хостинге: OS, CPU, RAM, GPU, uptime, ping",
    "commands": {".info": "показать карточку"},
}


def _fmt_uptime(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}"


def _cpu_name() -> str:
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine() or "unknown"


def _fmt_mb(b: float) -> str:
    mb = b / (1024 * 1024)
    if mb >= 1024:
        return f"{mb / 1024:.2f} GB"
    return f"{mb:.1f} MB"


def _os_pretty() -> str:
    try:
        info = platform.freedesktop_os_release()
        return info.get("PRETTY_NAME") or info.get("NAME") or platform.system()
    except (OSError, AttributeError):
        return platform.system()


def _gpu_line() -> str | None:
    if not shutil.which("nvidia-smi"):
        return None
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=3,
        ).strip().splitlines()
    except (subprocess.SubprocessError, OSError):
        return None
    if not out:
        return None
    name, util, used, total = [x.strip() for x in out[0].split(",")]
    return f"{name} — {util}% · {used}/{total} MB"


def _utf16_len(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


def _build(sections: list[list[tuple[str, str, str | None]]]) -> tuple[str, list[MessageEntity]]:
    chunks: list[str] = []
    entities: list[MessageEntity] = []
    offset = 0

    def emit(s: str):
        nonlocal offset
        chunks.append(s)
        offset += _utf16_len(s)

    for i, section in enumerate(sections):
        if i > 0:
            emit("\n")
        block_start = offset
        for j, (label, value, style) in enumerate(section):
            if j > 0:
                emit("\n")
            label_text = f"{label}: "
            entities.append(
                MessageEntity(
                    type=MessageEntityType.BOLD,
                    offset=offset,
                    length=_utf16_len(label_text),
                )
            )
            emit(label_text)
            value_start = offset
            emit(value)
            if style == "code":
                entities.append(
                    MessageEntity(
                        type=MessageEntityType.CODE,
                        offset=value_start,
                        length=offset - value_start,
                    )
                )
        entities.append(
            MessageEntity(
                type=MessageEntityType.BLOCKQUOTE,
                offset=block_start,
                length=offset - block_start,
            )
        )

    return "".join(chunks), entities


def _resolve_image() -> str | None:
    if not INFO_IMAGE:
        return None
    if os.path.isfile(INFO_IMAGE):
        return INFO_IMAGE
    matches = glob.glob(INFO_IMAGE + ".*")
    return matches[0] if matches else None


async def info_handler(client: Client, message: Message):
    await message.edit_text("<i>собираю инфу...</i>", parse_mode=ParseMode.HTML)
    try:
        from modules.ping import measure_ping
        ping_ms = await measure_ping(client)
    except Exception:
        ping_ms = 0.0

    me = client.me or await client.get_me()
    name = me.first_name or me.username or "user"
    uptime = _fmt_uptime(time.time() - getattr(client, "start_time", time.time()))
    prefix = PREFIXES[0]

    psutil.cpu_percent(None)
    proc = psutil.Process(os.getpid())
    proc.cpu_percent(None)
    await asyncio.sleep(0.3)
    cpu_total = psutil.cpu_percent(None)
    cpu_own = proc.cpu_percent(None)
    cpu_logical = psutil.cpu_count(logical=True) or 0
    cpu_physical = psutil.cpu_count(logical=False) or cpu_logical
    cpu_model = _cpu_name()

    vm = psutil.virtual_memory()
    ram_used = _fmt_mb(vm.used)
    ram_total = _fmt_mb(vm.total)
    ram_pct = vm.percent

    os_pretty = _os_pretty()
    kernel = f"{platform.release()}-{platform.machine()}"
    host_user = os.environ.get("USER") or os.environ.get("LOGNAME") or "user"
    hostname = socket.gethostname()
    py_ver = platform.python_version()
    gpu = _gpu_line()

    sections: list[list[tuple[str, str, str | None]]] = [
        [
            ("Owner", name, None),
            ("Version", f"{USERBOT_VERSION} ({USERBOT_BRANCH})", None),
        ],
        [
            ("Prefix", prefix, "code"),
            ("Uptime", uptime, None),
            ("Ping", f"{ping_ms:.3f} ms", None),
        ],
        [
            ("CPU", cpu_model, "code"),
            (" ›", f"{cpu_logical}({cpu_physical}) core(-s), {cpu_total}% total — {cpu_own:.2f}%", None),
            ("RAM", f"{ram_used} / {ram_total} ({ram_pct}%)", None),
        ],
    ]
    if gpu:
        sections.append([("GPU", gpu, None)])
    sections.append(
        [
            ("Host", f"{host_user}@{hostname}", "code"),
            ("OS", os_pretty, "code"),
            ("Kernel", kernel, "code"),
            ("Python", py_ver, None),
            (USERBOT_NAME.capitalize(), USERBOT_VERSION, None),
        ]
    )

    text, entities = _build(sections)

    image = _resolve_image()
    if image:
        chat_id = message.chat.id
        reply_to = message.reply_to_message.id if message.reply_to_message else None
        try:
            await message.delete()
        except Exception:
            pass
        await client.send_photo(
            chat_id,
            photo=image,
            caption=text,
            caption_entities=entities,
            parse_mode=ParseMode.DISABLED,
            reply_to_message_id=reply_to,
        )
    else:
        await message.edit_text(
            text,
            entities=entities,
            parse_mode=ParseMode.DISABLED,
        )


def register(app: Client):
    app.add_handler(
        MessageHandler(
            info_handler,
            owners.auth & filters.command("info", prefixes=PREFIXES),
        )
    )
