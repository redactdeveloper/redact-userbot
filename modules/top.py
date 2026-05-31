# обновлённый модуль который быстрее -> stats.py



import asyncio
import html

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
from pyrogram.handlers import MessageHandler
from pyrogram.raw import types as raw_types
from pyrogram.raw.functions.messages import GetHistory
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "Топ пользователей по количеству сообщений (вся история)",
    "commands": {
        ".top": "скан всей истории чата",
        ".top <N>": "ограничить количество сообщений",
    },
}

TOP_N = 10
BATCH = 100
WORKERS = 2
BATCH_PAUSE = 0.15
PROGRESS_INTERVAL = 2.0


async def _get_total(client: Client, peer) -> int:
    try:
        r = await client.invoke(
            GetHistory(
                peer=peer,
                offset_id=0,
                offset_date=0,
                add_offset=0,
                limit=1,
                max_id=0,
                min_id=0,
                hash=0,
            )
        )
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
        return await _get_total(client, peer)
    return getattr(r, "count", len(getattr(r, "messages", []) or []))


async def _worker(
    client: Client,
    peer,
    start_skip: int,
    quota: int,
    counts: dict[int, int],
    seen: set[int],
    stats: dict,
):
    offset_id = 0
    add_offset = start_skip
    remaining = quota

    while remaining > 0:
        limit = min(BATCH, remaining)
        try:
            r = await client.invoke(
                GetHistory(
                    peer=peer,
                    offset_id=offset_id,
                    offset_date=0,
                    add_offset=add_offset,
                    limit=limit,
                    max_id=0,
                    min_id=0,
                    hash=0,
                )
            )
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            continue

        msgs = getattr(r, "messages", None) or []
        if not msgs:
            break

        for m in msgs:
            mid = getattr(m, "id", None)
            if mid is None or mid in seen:
                continue
            seen.add(mid)
            stats["total"] += 1
            if isinstance(m, raw_types.Message) and m.from_id is not None:
                uid = getattr(m.from_id, "user_id", None)
                if uid:
                    counts[uid] = counts.get(uid, 0) + 1

        remaining -= len(msgs)
        if len(msgs) < limit:
            break
        offset_id = msgs[-1].id
        add_offset = 0
        await asyncio.sleep(BATCH_PAUSE)


async def _raw_scan(
    client: Client,
    chat_id: int,
    limit: int | None,
    on_progress,
) -> tuple[dict[int, int], int]:
    peer = await client.resolve_peer(chat_id)

    total_in_chat = await _get_total(client, peer)
    target = min(total_in_chat, limit) if limit else total_in_chat
    if target <= 0:
        return {}, 0

    workers = min(WORKERS, max(1, target // BATCH))
    chunk = target // workers
    extra = target % workers

    counts: dict[int, int] = {}
    seen: set[int] = set()
    stats = {"total": 0, "done": False}

    async def progress_loop():
        while not stats["done"]:
            try:
                await on_progress(stats["total"], target)
            except Exception:
                pass
            try:
                await asyncio.sleep(PROGRESS_INTERVAL)
            except asyncio.CancelledError:
                return

    progress_task = asyncio.create_task(progress_loop())

    try:
        tasks = []
        start = 0
        for i in range(workers):
            quota = chunk + (1 if i < extra else 0)
            if quota <= 0:
                continue
            tasks.append(
                _worker(client, peer, start, quota, counts, seen, stats)
            )
            start += quota
        await asyncio.gather(*tasks)
    finally:
        stats["done"] = True
        progress_task.cancel()
        try:
            await progress_task
        except asyncio.CancelledError:
            pass

    return counts, stats["total"]


async def _resolve_names(
    client: Client, user_ids: list[int]
) -> dict[int, str]:
    names: dict[int, str] = {}
    if not user_ids:
        return names
    try:
        users = await client.get_users(user_ids)
    except Exception:
        users = []
    if not isinstance(users, list):
        users = [users]
    for u in users:
        names[u.id] = u.first_name or u.username or f"id{u.id}"
    return names


async def top_handler(client: Client, message: Message):
    parts = (message.text or "").split(maxsplit=1)
    limit: int | None = None
    if len(parts) > 1:
        try:
            limit = max(1, int(parts[1]))
        except ValueError:
            limit = None

    await message.edit_text(
        "<i>сканирую историю...</i>",
        parse_mode=ParseMode.HTML,
    )

    async def on_progress(n: int, target: int):
        pct = (n / target * 100) if target else 0
        try:
            await message.edit_text(
                f"<i>сканирую... {n}/{target} ({pct:.0f}%)</i>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

    try:
        counts, total = await _raw_scan(client, message.chat.id, limit, on_progress)
    except Exception as e:
        await message.edit_text(
            f"<b>Ошибка:</b> <code>{html.escape(str(e))}</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    if not counts:
        await message.edit_text(
            "Нет сообщений для подсчёта",
            parse_mode=ParseMode.HTML,
        )
        return

    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]
    names = await _resolve_names(client, [uid for uid, _ in top])

    title = message.chat.title or "этот чат"
    lines = [
        f"<b>Топ — {html.escape(title)}</b>",
        f"<i>всего {total} сообщений, уникальных юзеров: {len(counts)}</i>",
        "",
    ]
    for i, (uid, cnt) in enumerate(top, 1):
        pct = cnt / total * 100 if total else 0
        name = names.get(uid, f"id{uid}")
        lines.append(
            f"<code>{i:2d}.</code> {html.escape(name)} — <b>{cnt}</b> "
            f"<i>({pct:.1f}%)</i>"
        )

    await message.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)


def register(app: Client):
    app.add_handler(
        MessageHandler(
            top_handler,
            owners.auth & filters.command("top", prefixes=PREFIXES),
        )
    )
