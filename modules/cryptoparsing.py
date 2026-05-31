import asyncio
import html
import json
from pathlib import Path

import aiohttp
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "Автоотправка курса криптовалюты с интервалом",
    "commands": {
        ".cryptoparsing <coin> <interval>": "запустить (10s/10m/10h/10d)",
        ".cryptoparsing list": "список активных",
        ".cryptoparsing stop <id>": "остановить по id",
        ".cryptoparsing stop all": "остановить все",
    },
}

URL = "https://api.binance.com/api/v3/ticker/24hr"
MIN_INTERVAL = 10
_STATE_FILE = Path(__file__).parent.parent / ".cryptoparsing_state.json"

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
        raise ValueError("интервал > 0")
    return num * mult


def _fmt_interval(seconds: int) -> str:
    if seconds % 86400 == 0:
        return f"{seconds // 86400}d"
    if seconds % 3600 == 0:
        return f"{seconds // 3600}h"
    if seconds % 60 == 0:
        return f"{seconds // 60}m"
    return f"{seconds}s"


def _fmt_price(p: float) -> str:
    if p >= 1000:
        return f"${p:,.2f}".replace(",", " ")
    if p >= 1:
        return f"${p:,.2f}"
    if p >= 0.01:
        return f"${p:.4f}"
    return f"${p:.8f}".rstrip("0").rstrip(".")


async def _fetch_price(coin: str) -> tuple[float, float]:
    symbol = f"{coin}USDT"
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.get(URL, params={"symbol": symbol}) as r:
            r.raise_for_status()
            data = await r.json()
    return float(data["lastPrice"]), float(data["priceChangePercent"])


async def _job_loop(job: dict):
    coin = job["coin"].upper()
    chat_id = int(job["chat_id"])
    interval = int(job["interval"])
    jid = job["id"]
    while True:
        try:
            if _app is None:
                return
            try:
                price, change = await _fetch_price(coin)
            except Exception as e:
                print(f"[cryptoparsing #{jid}] fetch error: {e}")
            else:
                sign = "+" if change >= 0 else ""
                text = (
                    f"<b>{html.escape(coin)}</b>: "
                    f"<code>{_fmt_price(price)}</code> "
                    f"({sign}{change:.2f}%)"
                )
                while True:
                    try:
                        await _app.send_message(
                            chat_id, text, parse_mode=ParseMode.HTML
                        )
                        break
                    except FloodWait as e:
                        await asyncio.sleep(e.value + 1)
                    except Exception as e:
                        print(f"[cryptoparsing #{jid}] send error: {e}")
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


async def _show_list(message: Message):
    jobs = _state.get("jobs", [])
    if not jobs:
        await message.edit_text(
            "<i>Нет активных трекеров</i>",
            parse_mode=ParseMode.HTML,
        )
        return
    lines = [f"<b>Crypto трекеры ({len(jobs)}):</b>", ""]
    for j in jobs:
        lines.append(
            f"<code>#{j['id']}</code> · <b>{html.escape(j['coin'])}</b> "
            f"→ <code>{j['chat_id']}</code> · {_fmt_interval(int(j['interval']))}"
        )
    await message.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cp_handler(client: Client, message: Message):
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
                "<b>Все трекеры остановлены</b>",
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
                f"Трекер <code>{jid}</code> не найден",
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

    if len(parts) < 3:
        await message.edit_text(
            "Использование: <code>.cryptoparsing COIN 10m</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    coin = parts[1].upper()
    interval_str = parts[2]

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

    try:
        await _fetch_price(coin)
    except Exception as e:
        await message.edit_text(
            f"<b>Монета не найдена:</b> <code>{html.escape(coin)}</code> "
            f"({html.escape(str(e))})",
            parse_mode=ParseMode.HTML,
        )
        return

    jid = _state.get("next_id", 1)
    _state["next_id"] = jid + 1
    job = {
        "id": jid,
        "coin": coin,
        "chat_id": message.chat.id,
        "interval": interval,
    }
    _state["jobs"].append(job)
    _save_state(_state)
    _start_job(job)

    await message.edit_text(
        f"<b>Трекер #{jid}:</b>\n"
        f"<b>Монета:</b> {html.escape(coin)}\n"
        f"<b>Чат:</b> <code>{message.chat.id}</code>\n"
        f"<b>Интервал:</b> {_fmt_interval(interval)}",
        parse_mode=ParseMode.HTML,
    )


def register(app: Client):
    app.add_handler(
        MessageHandler(
            cp_handler,
            owners.auth & filters.command(
                ["cryptoparsing", "cp"], prefixes=PREFIXES
            ),
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
