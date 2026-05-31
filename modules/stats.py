import asyncio
import html
import json
import re
from collections import defaultdict
from pathlib import Path

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
from pyrogram.handlers import MessageHandler
from pyrogram.raw.functions.messages import GetHistory
from pyrogram import raw, utils
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "Быстрая статистика чата из кэша",
    "commands": {
        ".stats": "мгновенный топ 10 из кэша",
        ".stats=<N>": "мгновенный топ N из кэша",
        ".stats rebuild": "точный быстрый пересчёт всей истории",
        ".stats rebuild <N>": "пересчёт последних N сообщений",
        ".stats import <path/result.json>": "импорт статистики из экспорта Telegram",
        ".stats import auto": "автоимпорт подходящего экспорта",
    },
}

DEFAULT_TOP_N = 10
MAX_TOP_N = 100
DEFAULT_REBUILD_LIMIT = None
MAX_REBUILD_LIMIT = 250_000
PROGRESS_STEP = 500
PROGRESS_INTERVAL = 2.0

_ROOT = Path(__file__).resolve().parent.parent
_NATIVE_DIR = _ROOT / "native"
_BIN_DIR = _ROOT / "bin"
_SOURCE = _NATIVE_DIR / "stats_worker.cpp"
_BINARY = _BIN_DIR / "stats_worker"
_CACHE_FILE = _ROOT / ".stats_cache.json"
_PREFIX_PATTERN = "|".join(re.escape(prefix) for prefix in PREFIXES)
_EXPORT_SEARCH_DIRS = [
    Path.home() / "Downloads",
    Path.home() / "Documents",
    Path.home() / "Desktop",
    Path.home() / "Downloads" / "Telegram Desktop",
    Path.home() / "Downloads" / "AyuGram Desktop",
]
_cache: dict[str, dict] = {}
_dirty = False
_save_task: asyncio.Task | None = None


def _parse_top_n(text: str | None) -> int:
    raw = (text or "").strip()
    if not raw:
        return DEFAULT_TOP_N

    parts = raw.split("=", 1)
    if len(parts) == 2:
        raw = parts[1].strip()
    else:
        chunks = raw.split(maxsplit=1)
        raw = chunks[1].strip() if len(chunks) > 1 else ""

    if not raw:
        return DEFAULT_TOP_N

    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_TOP_N
    return max(1, min(MAX_TOP_N, value))


def _parse_rebuild_limit(text: str | None) -> int | None:
    raw = (text or "").strip().lower()
    if not re.search(r"\bstats\s+rebuild\b", raw):
        return DEFAULT_REBUILD_LIMIT
    match = re.search(r"\bstats\s+rebuild\s+(\d+)\b", raw)
    if not match:
        return DEFAULT_REBUILD_LIMIT
    return max(1, min(MAX_REBUILD_LIMIT, int(match.group(1))))


def _parse_import_path(text: str | None) -> Path | None:
    raw = (text or "").strip()
    match = re.search(r"\bstats\s+import\s+(.+)$", raw, flags=re.IGNORECASE)
    if not match:
        return None
    path = match.group(1).strip().strip("'\"")
    if not path:
        return None
    return Path(path).expanduser()


def _is_auto_import(text: str | None) -> bool:
    return bool(re.search(r"\bstats\s+import\s+auto\s*$", text or "", flags=re.IGNORECASE))


def _load_cache() -> dict[str, dict]:
    if not _CACHE_FILE.exists():
        return {}
    try:
        data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _save_cache_now() -> None:
    _CACHE_FILE.write_text(json.dumps(_cache, ensure_ascii=False), encoding="utf-8")


async def _save_cache_loop():
    global _dirty
    while True:
        await asyncio.sleep(3)
        if not _dirty:
            continue
        _dirty = False
        try:
            await asyncio.to_thread(_save_cache_now)
        except Exception as e:
            print(f"[stats] cache save error: {e}", flush=True)


def _chat_key(chat_id: int) -> str:
    return str(chat_id)


def _empty_chat_cache() -> dict:
    return {
        "total_messages": 0,
        "counts": {},
        "names": {},
    }


def _extract_peer(message: Message) -> tuple[int, str] | None:
    if message.from_user:
        user = message.from_user
        label = user.first_name or user.username or f"id{user.id}"
        return user.id, label
    if message.sender_chat:
        chat = message.sender_chat
        return -chat.id, chat.title or f"chat{chat.id}"
    return None


def _remember_message(message: Message) -> None:
    global _dirty
    peer = _extract_peer(message)
    if peer is None:
        return
    peer_id, label = peer
    chat = _cache.setdefault(_chat_key(message.chat.id), _empty_chat_cache())
    counts = chat.setdefault("counts", {})
    names = chat.setdefault("names", {})
    key = str(peer_id)
    counts[key] = int(counts.get(key) or 0) + 1
    names[key] = label
    chat["total_messages"] = int(chat.get("total_messages") or 0) + 1
    _dirty = True


def _stats_from_cache(chat_id: int, top_n: int) -> tuple[dict, dict[int, str]] | None:
    chat = _cache.get(_chat_key(chat_id))
    if not chat:
        return None
    counts = chat.get("counts") or {}
    if not counts:
        return None

    ranked = sorted(
        ((int(peer_id), int(count)) for peer_id, count in counts.items()),
        key=lambda item: (-item[1], item[0]),
    )[:top_n]
    names = {int(peer_id): str(name) for peer_id, name in (chat.get("names") or {}).items()}
    stats = {
        "total_messages": int(chat.get("total_messages") or sum(counts.values())),
        "unique_authors": len(counts),
        "top": [{"peer_id": peer_id, "count": count} for peer_id, count in ranked],
        "meta": chat.get("meta") or {},
    }
    return stats, names


def _iter_export_messages(data):
    if isinstance(data, dict):
        messages = data.get("messages")
        if isinstance(messages, list):
            yield from messages
            return

        chats = data.get("chats")
        if isinstance(chats, dict):
            chat_list = chats.get("list")
            if isinstance(chat_list, list):
                for chat in chat_list:
                    messages = chat.get("messages")
                    if isinstance(messages, list):
                        yield from messages


def _export_title(data) -> str:
    if isinstance(data, dict):
        for key in ("name", "title"):
            value = data.get(key)
            if value:
                return str(value)
        chats = data.get("chats")
        if isinstance(chats, dict):
            chat_list = chats.get("list")
            if isinstance(chat_list, list) and len(chat_list) == 1:
                chat = chat_list[0]
                for key in ("name", "title"):
                    value = chat.get(key)
                    if value:
                        return str(value)
    return ""


def _norm_title(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _find_auto_export(chat_title: str | None) -> Path | None:
    expected = _norm_title(chat_title or "")
    candidates: list[tuple[float, Path, str]] = []

    for root in _EXPORT_SEARCH_DIRS:
        if not root.exists():
            continue
        try:
            files = list(root.rglob("result.json"))
        except Exception:
            continue
        for path in files:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                title = _export_title(data)
            except Exception:
                continue
            normalized = _norm_title(title)
            if expected and normalized != expected:
                continue
            candidates.append((path.stat().st_mtime, path, title))

    if not candidates:
        return None
    candidates.sort(reverse=True, key=lambda item: item[0])
    return candidates[0][1]


def _import_export(path: Path) -> tuple[dict, dict[int, str], dict]:
    if path.is_dir():
        path = path / "result.json"
    if not path.exists():
        raise FileNotFoundError(str(path))

    data = json.loads(path.read_text(encoding="utf-8"))
    counts: defaultdict[int, int] = defaultdict(int)
    names: dict[int, str] = {}
    skipped = 0

    for msg in _iter_export_messages(data):
        if not isinstance(msg, dict):
            continue
        if msg.get("type") != "message":
            continue

        from_id = msg.get("from_id")
        if from_id is None:
            skipped += 1
            continue

        raw_id = str(from_id)
        match = re.search(r"-?\d+", raw_id)
        if not match:
            skipped += 1
            continue
        peer_id = int(match.group(0))
        counts[peer_id] += 1

        label = msg.get("from")
        if label:
            names[peer_id] = str(label)

    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    stats = {
        "total_messages": sum(counts.values()),
        "unique_authors": len(counts),
        "top": [
            {"peer_id": peer_id, "count": count}
            for peer_id, count in ranked[:DEFAULT_TOP_N]
        ],
        "all": [
            {"peer_id": peer_id, "count": count}
            for peer_id, count in ranked
        ],
    }
    meta = {
        "source": str(path),
        "imported": True,
        "skipped": skipped,
    }
    return stats, names, meta


async def _compile_worker() -> None:
    _BIN_DIR.mkdir(parents=True, exist_ok=True)
    if _BINARY.exists() and _BINARY.stat().st_mtime >= _SOURCE.stat().st_mtime:
        return

    proc = await asyncio.create_subprocess_exec(
        "g++",
        "-O2",
        "-std=c++20",
        str(_SOURCE),
        "-o",
        str(_BINARY),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        details = (stderr or stdout or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"не удалось собрать C++ воркер: {details or proc.returncode}")


async def _get_total(client: Client, chat_id: int) -> int:
    peer = await client.resolve_peer(chat_id)
    while True:
        try:
            result = await client.invoke(
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
            return getattr(result, "count", len(getattr(result, "messages", []) or []))
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)


async def _start_worker(top_n: int):
    await _compile_worker()
    return await asyncio.create_subprocess_exec(
        str(_BINARY),
        str(top_n),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

async def _resolve_names(client: Client, sender_chat_names: dict[int, str], ranked_ids: list[int]) -> dict[int, str]:
    names: dict[int, str] = {}
    user_ids = [peer_id for peer_id in ranked_ids if peer_id > 0]
    if user_ids:
        try:
            users = await client.get_users(user_ids)
        except Exception:
            users = []
        if not isinstance(users, list):
            users = [users]
        for user in users:
            label = user.first_name or user.username or f"id{user.id}"
            names[user.id] = label

    for peer_id, title in sender_chat_names.items():
        if peer_id in ranked_ids and peer_id not in names:
            names[peer_id] = title

    return names


async def _scan_chat(
    client: Client,
    chat_id: int,
    top_n: int,
    on_progress,
    max_messages: int | None,
    max_seconds: float | None,
) -> tuple[dict, dict[int, str], dict]:
    proc = await _start_worker(top_n)
    if proc.stdin is None or proc.stdout is None or proc.stderr is None:
        raise RuntimeError("не удалось запустить C++ воркер")

    scanned = 0
    last_report = 0.0
    started_at = asyncio.get_running_loop().time()
    elapsed = 0.0
    sender_chat_names: dict[int, str] = {}

    try:
        async for item in client.get_chat_history(chat_id):
            peer_id: int | None = None
            if item.from_user:
                peer_id = item.from_user.id
            elif item.sender_chat:
                peer_id = -item.sender_chat.id
                sender_chat_names[peer_id] = item.sender_chat.title or f"chat{item.sender_chat.id}"

            if peer_id is None:
                continue

            proc.stdin.write(f"{peer_id}\n".encode("utf-8"))
            scanned += 1

            if max_messages is not None and scanned >= max_messages:
                break
            if max_seconds is not None and asyncio.get_running_loop().time() - started_at >= max_seconds:
                break

            if scanned % PROGRESS_STEP == 0:
                await proc.stdin.drain()

            now = asyncio.get_running_loop().time()
            if scanned % PROGRESS_STEP == 0 or now - last_report >= PROGRESS_INTERVAL:
                last_report = now
                await on_progress(scanned)

        proc.stdin.close()
        elapsed = asyncio.get_running_loop().time() - started_at
        stdout, stderr = await proc.communicate()
    finally:
        if proc.returncode is None:
            proc.kill()
            await proc.wait()

    if proc.returncode != 0:
        details = (stderr or stdout or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"C++ воркер завершился с ошибкой: {details or proc.returncode}")

    try:
        stats = json.loads(stdout.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("C++ воркер вернул битый JSON") from exc
    meta = {
        "scanned": scanned,
        "max_messages": max_messages,
        "max_seconds": max_seconds,
        "elapsed": elapsed,
    }
    return stats, sender_chat_names, meta


def _raw_name_maps(result) -> dict[int, str]:
    names: dict[int, str] = {}
    for user in getattr(result, "users", []) or []:
        label = (
            getattr(user, "first_name", None)
            or getattr(user, "username", None)
            or f"id{user.id}"
        )
        names[int(user.id)] = label
    for chat in getattr(result, "chats", []) or []:
        try:
            peer_id = utils.get_raw_peer_id(raw.types.PeerChannel(channel_id=chat.id))
        except Exception:
            try:
                peer_id = utils.get_raw_peer_id(raw.types.PeerChat(chat_id=chat.id))
            except Exception:
                peer_id = -int(chat.id)
        title = getattr(chat, "title", None) or f"chat{chat.id}"
        names[int(peer_id)] = title
    return names


async def _scan_chat_raw(
    client: Client,
    chat_id: int,
    top_n: int,
    on_progress,
    max_messages: int | None,
) -> tuple[dict, dict[int, str], dict]:
    peer = await client.resolve_peer(chat_id)
    counts: defaultdict[int, int] = defaultdict(int)
    names: dict[int, str] = {}
    offset_id = 0
    scanned = 0
    last_report = 0.0
    started_at = asyncio.get_running_loop().time()

    while True:
        try:
            result = await client.invoke(
                GetHistory(
                    peer=peer,
                    offset_id=offset_id,
                    offset_date=0,
                    add_offset=0,
                    limit=100,
                    max_id=0,
                    min_id=0,
                    hash=0,
                )
            )
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            continue

        batch = [
            msg
            for msg in (getattr(result, "messages", []) or [])
            if isinstance(msg, (raw.types.Message, raw.types.MessageService))
        ]
        if not batch:
            break

        names.update(_raw_name_maps(result))

        for msg in batch:
            from_id = getattr(msg, "from_id", None)
            if from_id is None:
                continue
            try:
                peer_id = int(utils.get_raw_peer_id(from_id))
            except Exception:
                continue
            counts[peer_id] += 1
            scanned += 1
            if max_messages is not None and scanned >= max_messages:
                break

        offset_id = min(int(msg.id) for msg in batch)

        now = asyncio.get_running_loop().time()
        if scanned % PROGRESS_STEP == 0 or now - last_report >= PROGRESS_INTERVAL:
            last_report = now
            await on_progress(scanned)

        if max_messages is not None and scanned >= max_messages:
            break

    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    stats = {
        "total_messages": sum(counts.values()),
        "unique_authors": len(counts),
        "top": [
            {"peer_id": peer_id, "count": count}
            for peer_id, count in ranked[:top_n]
        ],
        "all": [
            {"peer_id": peer_id, "count": count}
            for peer_id, count in ranked
        ],
    }
    meta = {
        "scanned": scanned,
        "max_messages": max_messages,
        "elapsed": asyncio.get_running_loop().time() - started_at,
        "raw": True,
    }
    return stats, names, meta


def _store_rebuild(
    chat_id: int,
    stats: dict,
    sender_chat_names: dict[int, str],
    names: dict[int, str],
    meta: dict | None = None,
) -> None:
    global _dirty
    counts = {}
    for item in stats.get("all") or []:
        counts[str(int(item["peer_id"]))] = int(item["count"])

    if not counts:
        for item in stats.get("top") or []:
            counts[str(int(item["peer_id"]))] = int(item["count"])

    merged_names = {str(peer_id): label for peer_id, label in names.items()}
    for peer_id, label in sender_chat_names.items():
        merged_names.setdefault(str(peer_id), label)

    _cache[_chat_key(chat_id)] = {
        "total_messages": int(stats.get("total_messages") or sum(counts.values())),
        "counts": counts,
        "names": merged_names,
        "meta": meta or {},
    }
    _dirty = True


def _format_stats(message: Message, stats: dict, names: dict[int, str]) -> str:
    total_messages = int(stats.get("total_messages") or 0)
    ranked = stats.get("top") or []
    title = message.chat.title or "этот чат"

    lines = [
        f"<b>Статистика — {html.escape(title)}</b>",
        f"<i>всего сообщений в кэше: {total_messages}, уникальных авторов: {int(stats.get('unique_authors') or 0)}</i>",
    ]
    meta = stats.get("meta") or {}
    if meta.get("max_messages") or meta.get("max_seconds"):
        lines.append(
            "<i>"
            f"срез: {int(meta.get('scanned') or total_messages)} сообщений"
            f", {float(meta.get('elapsed') or 0):.1f} сек"
            "</i>"
        )
    lines.append("")

    for place, item in enumerate(ranked, 1):
        peer_id = int(item["peer_id"])
        count = int(item["count"])
        percent = count / total_messages * 100 if total_messages else 0
        name = names.get(peer_id, f"id{peer_id}" if peer_id > 0 else f"chat{-peer_id}")
        lines.append(
            f"<code>{place:2d} место.</code> {html.escape(name)} — <b>{count}</b> <i>({percent:.1f}%)</i>"
        )

    return "\n".join(lines)


async def stats_handler(client: Client, message: Message):
    top_n = _parse_top_n(message.text)
    text = message.text or ""
    auto_import = _is_auto_import(text)
    import_path = _parse_import_path(text)
    if auto_import:
        import_path = await asyncio.to_thread(_find_auto_export, message.chat.title)
    rebuild = bool(re.search(r"\bstats\s+rebuild\b", text, flags=re.IGNORECASE))
    rebuild_limit = _parse_rebuild_limit(text)

    if auto_import and import_path is None:
        await message.edit_text(
            "Не нашёл export <code>result.json</code> с таким же названием чата. "
            "Сделай экспорт в JSON и положи его в Downloads.",
            parse_mode=ParseMode.HTML,
        )
        return

    if import_path is not None:
        await message.edit_text("<i>импортирую export result.json...</i>", parse_mode=ParseMode.HTML)
        try:
            stats, names, meta = await asyncio.to_thread(_import_export, import_path)
        except Exception as e:
            await message.edit_text(
                f"<b>Ошибка импорта:</b> <code>{html.escape(str(e))}</code>",
                parse_mode=ParseMode.HTML,
            )
            return
        if int(stats.get("total_messages") or 0) <= 0:
            await message.edit_text(
                "В экспорте не нашёл сообщений. Нужен Telegram export в JSON.",
                parse_mode=ParseMode.HTML,
            )
            return
        stats["top"] = stats.get("all", [])[:top_n]
        stats["meta"] = meta
        _store_rebuild(message.chat.id, stats, {}, names, meta)
        await asyncio.to_thread(_save_cache_now)
        await message.edit_text(_format_stats(message, stats, names), parse_mode=ParseMode.HTML)
        return

    if not rebuild:
        cached = _stats_from_cache(message.chat.id, top_n)
        if cached is None:
            auto_path = await asyncio.to_thread(_find_auto_export, message.chat.title)
            if auto_path is None:
                await message.edit_text(
                    "Кэш пуст, подходящий export не найден. "
                    "Сделай экспорт чата в JSON или запусти <code>.stats rebuild</code>.",
                    parse_mode=ParseMode.HTML,
                )
                return
            await message.edit_text("<i>кэш пуст, импортирую найденный export...</i>", parse_mode=ParseMode.HTML)
            try:
                stats, names, meta = await asyncio.to_thread(_import_export, auto_path)
            except Exception as e:
                await message.edit_text(
                    f"<b>Ошибка автоимпорта:</b> <code>{html.escape(str(e))}</code>",
                    parse_mode=ParseMode.HTML,
                )
                return
            stats["top"] = stats.get("all", [])[:top_n]
            stats["meta"] = meta
            _store_rebuild(message.chat.id, stats, {}, names, meta)
            await asyncio.to_thread(_save_cache_now)
            await message.edit_text(_format_stats(message, stats, names), parse_mode=ParseMode.HTML)
            return
        stats, names = cached
        await message.edit_text(_format_stats(message, stats, names), parse_mode=ParseMode.HTML)
        return

    if rebuild_limit is None:
        await message.edit_text(
            "<i>считаю всю историю чата быстрым raw-сканером...</i>",
            parse_mode=ParseMode.HTML,
        )
    else:
        await message.edit_text(
            f"<i>считаю последние {rebuild_limit} сообщений быстрым raw-сканером...</i>",
            parse_mode=ParseMode.HTML,
        )

    total_hint = 0
    try:
        total_hint = await _get_total(client, message.chat.id)
    except Exception:
        total_hint = 0

    progress_total = min(total_hint, rebuild_limit) if rebuild_limit and total_hint else total_hint

    async def on_progress(done: int):
        if progress_total:
            pct = done / progress_total * 100
            text = f"<i>считаю историю... {done}/{progress_total} ({pct:.0f}%)</i>"
        else:
            text = f"<i>считаю историю... {done}</i>"
        try:
            await message.edit_text(text, parse_mode=ParseMode.HTML)
        except Exception:
            pass

    try:
        stats, sender_chat_names, meta = await _scan_chat_raw(
            client,
            message.chat.id,
            top_n,
            on_progress,
            rebuild_limit,
        )
    except Exception as e:
        await message.edit_text(
            f"<b>Ошибка:</b> <code>{html.escape(str(e))}</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    total_messages = int(stats.get("total_messages") or 0)
    ranked = stats.get("top") or []
    if total_messages <= 0 or not ranked:
        await message.edit_text("Нет сообщений для подсчёта", parse_mode=ParseMode.HTML)
        return

    ranked_ids = [int(item["peer_id"]) for item in ranked if "peer_id" in item]
    names = await _resolve_names(client, sender_chat_names, ranked_ids)
    stats["meta"] = meta
    _store_rebuild(message.chat.id, stats, sender_chat_names, names, meta)
    await asyncio.to_thread(_save_cache_now)
    await message.edit_text(_format_stats(message, stats, names), parse_mode=ParseMode.HTML)


async def stats_cache_handler(client: Client, message: Message):
    _remember_message(message)


def register(app: Client):
    app.add_handler(
        MessageHandler(
            stats_handler,
            owners.auth & filters.regex(
                rf"^(?:{_PREFIX_PATTERN})stats(?:=\d+|\s+\d+|\s+rebuild(?:\s+\d+)?|\s+import\s+.+)?$"
            ),
        )
    )
    app.add_handler(MessageHandler(stats_cache_handler, filters.group & filters.text), group=20)


async def on_start(app: Client):
    global _cache, _save_task
    _cache = _load_cache()
    _save_task = asyncio.create_task(_save_cache_loop())


async def on_stop(app: Client):
    global _save_task
    if _save_task and not _save_task.done():
        _save_task.cancel()
        try:
            await _save_task
        except (asyncio.CancelledError, Exception):
            pass
    _save_task = None
    if _dirty:
        await asyncio.to_thread(_save_cache_now)
