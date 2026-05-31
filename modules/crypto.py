import html
import json

import aiohttp
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "Курс популярных криптовалют",
    "commands": {
        ".crypto": "топ-30 монет, цена + 24h изменение",
        ".crypto <SYM>": "одна монета (BTC, ETH, ...)",
    },
}

URL = "https://api.binance.com/api/v3/ticker/24hr"

COINS = [
    "BTC", "ETH", "BNB", "SOL", "XRP",
    "ADA", "DOGE", "TRX", "TON", "AVAX",
    "LINK", "DOT", "SHIB", "LTC", "BCH",
    "UNI", "XLM", "ATOM", "XMR", "ETC",
    "FIL", "ICP", "HBAR", "APT", "NEAR",
    "ARB", "OP", "SUI", "AAVE", "INJ",
]


def _fmt_price(p: float) -> str:
    if p >= 1000:
        return f"${p:,.2f}".replace(",", " ")
    if p >= 1:
        return f"${p:,.2f}"
    if p >= 0.01:
        return f"${p:.4f}"
    return f"${p:.8f}".rstrip("0").rstrip(".")


async def _fetch(symbols: list[str]) -> list[dict]:
    params = {"symbols": json.dumps(symbols, separators=(",", ":"))}
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.get(URL, params=params) as r:
            r.raise_for_status()
            data = await r.json()
    if not isinstance(data, list):
        return [data]
    return data


async def crypto_handler(client: Client, message: Message):
    parts = (message.text or "").split(maxsplit=1)
    arg = parts[1].strip().upper() if len(parts) > 1 else ""

    if arg:
        symbols = [f"{arg}USDT"]
    else:
        symbols = [f"{c}USDT" for c in COINS]

    await message.edit_text("<i>тяну курсы...</i>", parse_mode=ParseMode.HTML)

    try:
        data = await _fetch(symbols)
    except aiohttp.ClientResponseError as e:
        await message.edit_text(
            f"<b>Ошибка API:</b> <code>{e.status} {e.message}</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    except Exception as e:
        await message.edit_text(
            f"<b>Ошибка:</b> <code>{html.escape(str(e))}</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    by_symbol = {
        d["symbol"]: d for d in data if isinstance(d, dict) and "symbol" in d
    }

    rows: list[tuple[str, str, float]] = []
    for sym in symbols:
        d = by_symbol.get(sym)
        name = sym.replace("USDT", "")
        if not d:
            continue
        try:
            price = float(d.get("lastPrice") or 0)
            change = float(d.get("priceChangePercent") or 0)
        except ValueError:
            continue
        rows.append((name, _fmt_price(price), change))

    if not rows:
        await message.edit_text(
            "<i>нет данных</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    name_w = max(len(r[0]) for r in rows)
    price_w = max(len(r[1]) for r in rows)

    lines = []
    for name, price_str, change in rows:
        sign = "+" if change >= 0 else ""
        line = (
            f"{name.ljust(name_w)}  {price_str.rjust(price_w)}  "
            f"{sign}{change:.2f}%"
        )
        lines.append(line)

    body = "\n".join(lines)
    text = f"<b>Crypto ({len(rows)}):</b>\n<pre>{html.escape(body)}</pre>"
    await message.edit_text(text, parse_mode=ParseMode.HTML)


def register(app: Client):
    app.add_handler(
        MessageHandler(
            crypto_handler,
            owners.auth & filters.command("crypto", prefixes=PREFIXES),
        )
    )
