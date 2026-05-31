import asyncio
import html
import json
from pathlib import Path

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "Периодическая отправка сообщения в чат",
    "commands": {
        ".automsg <link> <text> <interval>": "добавить (интервал: 10s/10m/10h/10d)",
        ".automsg list": "список активных",
        ".automsg stop <id>": "остановить задание",
        ".automsg stop all": "остановить все",
    },
}

_STATE_FILE = Path(__file__).parent.parent / ".automsg_state.json"
MIN_INTERVAL = 10
_tasks: dict[int, asyncio.Task] = {}
_app: Client | None = None


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text())
        except Exception:
            pass
    return {"jobs": [], "next_id": 1}


def _save_state(state: dict):
    _STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


_state = _load_state()


def _parse_interval(s: str) -> int:
    s = s.strip().lower()
    if not s:
        raise ValueError("пустой интервал")
    unit = s[-1]
    mult = {"s": 1, "m": 60, "h": 3600, "d": 86400}.get(unit)
    if mult is None:
        raise ValueError(f"неизвестная единица: {unit}")
    try:
        num = int(s[:-1])
    except ValueError:
        raise ValueError(f"плохое число: {s[:-1]}")
    if num <= 0:
        raise ValueError("интервал должен быть > 0")
    return num * mult


def _fmt_interval(seconds: int) -> str:
    if seconds % 86400 == 0:
        return f"{seconds // 86400}d"
    if seconds % 3600 == 0:
        return f"{seconds // 3600}h"
    if seconds % 60 == 0:
        return f"{seconds // 60}m"
    return f"{seconds}s"


def _parse_chat(link: str) -> str | int:
    link = link.strip()
    for prefix in ("https://t.me/", "http://t.me/", "t.me/", "@"):
        if link.startswith(prefix):
            link = link[len(prefix):]
            break
    try:
        return int(link)
    except ValueError:
        return link


async def _job_loop(job: dict):
    chat = _parse_chat(job["chat"])
    text = job["message"]
    interval = int(job["interval"])
    while True:
        try:
            if _app is None:
                return
            while True:
                try:
                    await _app.send_message(
                        chat, text, parse_mode=ParseMode.DISABLED
                    )
                    break
                except FloodWait as e:
                    await asyncio.sleep(e.value + 1)
                except Exception as e:
                    print(f"[automsg #{job['id']}] send error: {e}")
                    break
        except asyncio.CancelledError:
            raise
        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            raise


def _start_job(job: dict):
    jid = job["id"]
    if jid in _tasks and not _tasks[jid].done():
        return
    _tasks[jid] = asyncio.create_task(_job_loop(job))


async def _stop_job(jid: int):
    task = _tasks.pop(jid, None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


def _find_job(jid: int) -> dict | None:
    for j in _state["jobs"]:
        if j["id"] == jid:
            return j
    return None


async def automsg_handler(client: Client, message: Message):
    parts = (message.text or "").split()
    if len(parts) < 2:
        await _show_list(message)
        return

    sub = parts[1].lower()

    if sub == "list":
        await _show_list(message)
        return

    if sub == "stop":
        if len(parts) < 3:
            await message.edit_text(
                "Укажи id или <code>all</code>",
                parse_mode=ParseMode.HTML,
            )
            return
        target = parts[2].lower()
        if target == "all":
            for j in list(_state["jobs"]):
                await _stop_job(j["id"])
            _state["jobs"].clear()
            _save_state(_state)
            await message.edit_text(
                "<b>Все задания остановлены</b>",
                parse_mode=ParseMode.HTML,
            )
            return
        try:
            jid = int(target)
        except ValueError:
            await message.edit_text(
                "id должен быть числом",
                parse_mode=ParseMode.HTML,
            )
            return
        job = _find_job(jid)
        if not job:
            await message.edit_text(
                f"Задание <code>{jid}</code> не найдено",
                parse_mode=ParseMode.HTML,
            )
            return
        await _stop_job(jid)
        _state["jobs"] = [j for j in _state["jobs"] if j["id"] != jid]
        _save_state(_state)
        await message.edit_text(
            f"<b>Остановлено:</b> <code>{jid}</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    if len(parts) < 4:
        await message.edit_text(
            "Использование: <code>.automsg &lt;link&gt; &lt;text&gt; &lt;interval&gt;</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    link = parts[1]
    interval_str = parts[-1]
    text_parts = parts[2:-1]
    text = " ".join(text_parts)

    try:
        interval = _parse_interval(interval_str)
    except ValueError as e:
        await message.edit_text(
            f"<b>Ошибка интервала:</b> {html.escape(str(e))}",
            parse_mode=ParseMode.HTML,
        )
        return

    if interval < MIN_INTERVAL:
        await message.edit_text(
            f"Минимальный интервал — {MIN_INTERVAL}s",
            parse_mode=ParseMode.HTML,
        )
        return

    jid = _state.get("next_id", 1)
    _state["next_id"] = jid + 1
    job = {
        "id": jid,
        "chat": link,
        "message": text,
        "interval": interval,
    }
    _state["jobs"].append(job)
    _save_state(_state)
    _start_job(job)

    await message.edit_text(
        f"<b>Автосообщение #{jid}:</b>\n"
        f"<b>Чат:</b> <code>{html.escape(link)}</code>\n"
        f"<b>Интервал:</b> {_fmt_interval(interval)}\n"
        f"<b>Текст:</b> <code>{html.escape(text[:200])}</code>",
        parse_mode=ParseMode.HTML,
    )


async def _show_list(message: Message):
    jobs = _state.get("jobs", [])
    if not jobs:
        await message.edit_text(
            "<i>Нет активных автосообщений</i>",
            parse_mode=ParseMode.HTML,
        )
        return
    lines = [f"<b>Автосообщения ({len(jobs)}):</b>", ""]
    for j in jobs:
        preview = j["message"][:50]
        if len(j["message"]) > 50:
            preview += "..."
        lines.append(
            f"<code>#{j['id']}</code> → <code>{html.escape(j['chat'])}</code> "
            f"· {_fmt_interval(int(j['interval']))}\n"
            f"   <i>{html.escape(preview)}</i>"
        )
    await message.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)


def register(app: Client):
    app.add_handler(
        MessageHandler(
            automsg_handler,
            owners.auth & filters.command("automsg", prefixes=PREFIXES),
        )
    )


async def on_start(app: Client):
    global _app
    _app = app
    for job in _state.get("jobs", []):
        _start_job(job)


async def on_stop(app: Client):
    for jid in list(_tasks):
        await _stop_job(jid)
