import asyncio
import html
import json
import math
import tempfile
import time
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
    "description": "Погода через wttr.in (без ключей)",
    "commands": {
        ".weather": "погода в сохранённом городе",
        ".weather <город>": "погода в любом городе",
        ".weather set <город>": "сохранить город",
        ".weather top": "топ городов с самой высокой темп.",
        ".weather cold": "топ городов с самой низкой темп.",
    },
}

_STATE_FILE = Path(__file__).parent.parent / ".weather_state.json"
_CARD_DIR = Path(__file__).parent.parent / "downloads" / "weather"
_FONT_REGULAR = "/usr/share/fonts/gnu-free/FreeSans.otf"
_FONT_BOLD = "/usr/share/fonts/gnu-free/FreeSansBold.otf"

CITIES = [
    "Moscow", "Saint Petersburg", "Kazan", "Novosibirsk",
    "Yekaterinburg", "Sochi", "Vladivostok", "Rostov-on-Don",
    "Krasnodar", "Murmansk", "Yakutsk", "Norilsk",
    "London", "New York", "Tokyo", "Paris", "Berlin", "Madrid",
    "Rome", "Istanbul", "Dubai", "Beijing", "Mumbai",
    "Sydney", "Cairo", "Lagos", "Buenos Aires", "Mexico City",
    "Los Angeles", "Toronto", "Bangkok", "Singapore", "Seoul",
    "Reykjavik", "Oslo", "Helsinki", "Stockholm", "Anchorage",
]

TOP_N = 10
DAY_NAMES = ("ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС")


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_state(state: dict):
    _STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


_state = _load_state()


async def _fetch(session: aiohttp.ClientSession, city: str) -> dict:
    url = f"https://wttr.in/{city}?format=j1&lang=ru"
    async with session.get(url) as r:
        r.raise_for_status()
        return await r.json(content_type=None)


async def _fetch_daily(session: aiohttp.ClientSession, lat: str, lon: str) -> dict:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min"
        "&timezone=auto&forecast_days=6"
    )
    async with session.get(url) as r:
        r.raise_for_status()
        return await r.json(content_type=None)


def _parse(data: dict) -> dict:
    cur = (data.get("current_condition") or [{}])[0]
    temp = int(cur.get("temp_C") or 0)
    feels = int(cur.get("FeelsLikeC") or 0)
    desc = ""
    lang_ru = cur.get("lang_ru") or []
    if lang_ru:
        desc = lang_ru[0].get("value", "")
    if not desc:
        wd = cur.get("weatherDesc") or []
        desc = wd[0].get("value", "") if wd else ""
    humidity = cur.get("humidity", "?")
    wind = cur.get("windspeedKmph", "?")
    area = ""
    nearest = data.get("nearest_area") or []
    if nearest:
        an = nearest[0].get("areaName") or []
        if an:
            area = an[0].get("value", "")
        country = nearest[0].get("country") or []
        if country:
            c = country[0].get("value", "")
            if c:
                area = f"{area}, {c}" if area else c
    return {
        "temp": temp,
        "feels": feels,
        "desc": desc,
        "humidity": humidity,
        "wind": wind,
        "area": area,
        "code": int(cur.get("weatherCode") or 116),
        "lat": (nearest[0].get("latitude") if nearest else "") or "",
        "lon": (nearest[0].get("longitude") if nearest else "") or "",
    }


def _format_one(info: dict) -> str:
    area = info["area"] or "город"
    return (
        f"<b>{html.escape(area)}</b>\n"
        f"<b>Температура:</b> {info['temp']}°C "
        f"(ощущается {info['feels']}°C)\n"
        f"<b>Состояние:</b> {html.escape(info['desc'])}\n"
        f"<b>Влажность:</b> {info['humidity']}%\n"
        f"<b>Ветер:</b> {info['wind']} км/ч"
    )


async def _show_city(city: str) -> str:
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        data = await _fetch(s, city)
    info = _parse(data)
    return _format_one(info)


def _x(s: object) -> str:
    return html.escape(str(s), quote=True)


def _weather_kind(code: int) -> str:
    if code in (0, 113):
        return "sun"
    if code in (1, 2, 3, 116, 119, 122, 143, 248, 260):
        return "cloud"
    if code in (45, 48):
        return "fog"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 176, 263, 266, 281, 284, 293, 296, 299, 302, 305, 308, 311, 314, 353, 356, 359):
        return "rain"
    if code in (71, 73, 75, 77, 85, 86, 179, 182, 185, 227, 230, 317, 320, 323, 326, 329, 332, 335, 338, 350, 362, 365, 368, 371, 374, 377):
        return "snow"
    if code in (95, 96, 99, 200, 386, 389, 392, 395):
        return "storm"
    return "cloud"


def _icon_svg(kind: str, x: int, y: int, scale: float = 1.0) -> str:
    sw = max(3, round(4 * scale, 1))
    color = "#f4c64f"
    parts = [
        f'<g transform="translate({x} {y}) scale({scale})" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">'
    ]
    if kind in ("sun", "cloud"):
        if kind == "sun":
            parts.append('<circle cx="30" cy="30" r="12"/>')
            for x1, y1, x2, y2 in ((30, 6, 30, 0), (30, 60, 30, 54), (6, 30, 0, 30), (60, 30, 54, 30), (13, 13, 8, 8), (47, 47, 52, 52), (47, 13, 52, 8), (13, 47, 8, 52)):
                parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')
        else:
            parts.append('<path d="M18 44h31c9 0 15-6 15-14s-7-14-15-14c-4 0-7 1-10 4C36 11 28 6 19 8S4 19 6 29c-7 1-12 7-12 15 0 8 7 14 16 14h8" transform="translate(4 -5)"/>')
    elif kind == "rain":
        parts.append('<path d="M18 36h31c8 0 13-5 13-12s-6-13-14-13c-4 0-7 1-10 4C35 7 27 3 19 5S5 15 6 24c-6 1-10 6-10 12 0 7 6 12 14 12h8" transform="translate(5 -2)"/>')
        parts.append('<line x1="22" y1="50" x2="18" y2="62"/><line x1="38" y1="50" x2="34" y2="62"/><line x1="54" y1="50" x2="50" y2="62"/>')
    elif kind == "snow":
        parts.append('<path d="M18 36h31c8 0 13-5 13-12s-6-13-14-13c-4 0-7 1-10 4C35 7 27 3 19 5S5 15 6 24c-6 1-10 6-10 12 0 7 6 12 14 12h8" transform="translate(5 -2)"/>')
        parts.append('<path d="M22 55h10M27 50v10M42 55h10M47 50v10"/>')
    elif kind == "storm":
        parts.append('<path d="M18 36h31c8 0 13-5 13-12s-6-13-14-13c-4 0-7 1-10 4C35 7 27 3 19 5S5 15 6 24c-6 1-10 6-10 12 0 7 6 12 14 12h8" transform="translate(5 -2)"/>')
        parts.append('<path d="M34 48l-8 17h11l-6 14 17-22H37l7-9z" fill="#f4c64f" stroke="none"/>')
    else:
        parts.append('<path d="M8 25h48M2 38h60M12 51h38"/>')
    parts.append("</g>")
    return "".join(parts)


def _daily_from_wttr(data: dict) -> list[dict]:
    result = []
    for item in data.get("weather") or []:
        hourly = item.get("hourly") or [{}]
        code = int((hourly[len(hourly) // 2] or {}).get("weatherCode") or 116)
        result.append(
            {
                "date": item.get("date", ""),
                "max": int(float(item.get("maxtempC") or 0)),
                "min": int(float(item.get("mintempC") or 0)),
                "code": code,
            }
        )
    return result


def _daily_from_open_meteo(data: dict) -> list[dict]:
    daily = data.get("daily") or {}
    dates = daily.get("time") or []
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    codes = daily.get("weather_code") or []
    result = []
    for date, high, low, code in zip(dates, highs, lows, codes):
        result.append(
            {
                "date": date,
                "max": int(round(float(high))),
                "min": int(round(float(low))),
                "code": int(code),
            }
        )
    return result


def _day_label(date_text: str) -> str:
    try:
        from datetime import date

        y, m, d = [int(part) for part in date_text.split("-")]
        return DAY_NAMES[date(y, m, d).weekday()]
    except Exception:
        return "—"


def _weather_card_svg(city: str, info: dict, daily: list[dict]) -> str:
    city = city.strip() or info.get("area") or "Погода"
    temp = int(info["temp"])
    days = daily[:6] or _daily_from_wttr({"weather": []})
    width, height = 824, 424
    main_kind = _weather_kind(int(info.get("code") or 116))
    day_width = 112
    start_x = 66
    forecast = []
    for index, day in enumerate(days[:6]):
        x = start_x + index * day_width
        forecast.append(f'<text x="{x + 38}" y="249" class="day" text-anchor="middle">{_x(_day_label(day["date"]))}</text>')
        forecast.append(_icon_svg(_weather_kind(int(day["code"])), x + 3, 284, 0.72))
        forecast.append(f'<text x="{x + 38}" y="385" class="range" text-anchor="middle">{day["max"]}°/{day["min"]}°</text>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<defs>
  <style>
    @font-face {{ font-family: WeatherSans; src: url("{_FONT_REGULAR}"); }}
    @font-face {{ font-family: WeatherSans; font-weight: 700; src: url("{_FONT_BOLD}"); }}
    text {{ font-family: WeatherSans, Arial, sans-serif; fill: #f6f0e8; }}
    .city {{ font-size: 36px; font-weight: 700; }}
    .temp {{ font-size: 42px; font-weight: 700; }}
    .tz {{ font-size: 20px; font-weight: 700; fill: #d6d1c9; }}
    .day {{ font-size: 20px; font-weight: 700; fill: #e4ded4; }}
    .range {{ font-size: 20px; fill: #e6dfd5; }}
  </style>
  <filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="14"/></filter>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#19170f"/>
    <stop offset="0.52" stop-color="#595957"/>
    <stop offset="1" stop-color="#252315"/>
  </linearGradient>
  <clipPath id="card"><rect x="16" y="14" width="792" height="396" rx="28"/></clipPath>
</defs>
<rect width="{width}" height="{height}" fill="#0e0d09"/>
<g clip-path="url(#card)">
  <rect x="16" y="14" width="792" height="396" fill="url(#bg)"/>
  <circle cx="560" cy="64" r="190" fill="#8c8c8a" opacity="0.38" filter="url(#soft)"/>
  <circle cx="328" cy="120" r="145" fill="#2a2925" opacity="0.42" filter="url(#soft)"/>
  <circle cx="742" cy="360" r="150" fill="#090806" opacity="0.34" filter="url(#soft)"/>
  <rect x="16" y="14" width="792" height="396" fill="#000" opacity="0.18"/>
  {_icon_svg(main_kind, 88, 72, 1.02)}
  <text x="230" y="93" class="city">{_x(city)}</text>
  <text x="230" y="149" class="temp">{temp}°C</text>
  <text x="{230 + 86 + max(0, math.floor(math.log10(abs(temp) + 1)) * 22)}" y="144" class="tz">(GMT+3)</text>
  <line x1="66" y1="202" x2="758" y2="202" stroke="#d9cdbb" opacity="0.22"/>
  {''.join(forecast)}
</g>
</svg>'''


async def _render_weather_card(city: str, info: dict, daily: list[dict]) -> Path:
    _CARD_DIR.mkdir(parents=True, exist_ok=True)
    svg = _weather_card_svg(city, info, daily)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".svg", delete=False) as src:
        src.write(svg)
        src_path = Path(src.name)
    out_path = _CARD_DIR / f"weather_{int(time.time() * 1000)}.png"
    proc = await asyncio.create_subprocess_exec(
        "magick",
        str(src_path),
        str(out_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    src_path.unlink(missing_ok=True)
    if proc.returncode != 0:
        raise RuntimeError(stderr.decode("utf-8", "ignore") or "ImageMagick failed")
    return out_path


async def _show_city_card(city: str) -> tuple[Path, str]:
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        data = await _fetch(s, city)
        info = _parse(data)
        daily = _daily_from_wttr(data)
        if info["lat"] and info["lon"]:
            try:
                daily = _daily_from_open_meteo(await _fetch_daily(s, info["lat"], info["lon"])) or daily
            except Exception:
                pass
    path = await _render_weather_card(city, info, daily)
    return path, _format_one(info)


async def _top(cold: bool) -> str:
    timeout = aiohttp.ClientTimeout(total=20)
    results: list[tuple[str, int, str]] = []

    async def one(sess: aiohttp.ClientSession, city: str):
        try:
            data = await _fetch(sess, city)
            info = _parse(data)
            results.append((info["area"] or city, info["temp"], info["desc"]))
        except Exception:
            pass

    async with aiohttp.ClientSession(timeout=timeout) as s:
        await asyncio.gather(*(one(s, c) for c in CITIES))

    if not results:
        return "<i>ничего не получил</i>"

    results.sort(key=lambda x: x[1], reverse=not cold)
    results = results[:TOP_N]

    title = "Топ холодных" if cold else "Топ горячих"
    lines = [f"<b>{title} (сейчас):</b>", ""]
    for i, (area, temp, desc) in enumerate(results, 1):
        lines.append(
            f"<code>{i:2d}.</code> <b>{temp:+d}°C</b> — "
            f"{html.escape(area)} <i>({html.escape(desc)})</i>"
        )
    return "\n".join(lines)


async def weather_handler(client: Client, message: Message):
    parts = (message.text or "").split(maxsplit=1)
    arg = parts[1].strip() if len(parts) > 1 else ""

    if not arg:
        city = _state.get("city")
        if not city:
            await message.edit_text(
                "Город не задан. Используй <code>.weather set Москва</code>",
                parse_mode=ParseMode.HTML,
            )
            return
        await message.edit_text("<i>смотрю погоду...</i>", parse_mode=ParseMode.HTML)
        try:
            photo, _ = await _show_city_card(city)
        except Exception as e:
            await message.edit_text(
                f"<b>Ошибка:</b> <code>{html.escape(str(e))}</code>",
                parse_mode=ParseMode.HTML,
            )
            return
        try:
            await client.send_photo(message.chat.id, str(photo))
            await message.delete()
        except FloodWait as e:
            await message.edit_text(
                f"Telegram просит подождать {e.value} сек. Попробуй позже.",
                parse_mode=ParseMode.HTML,
            )
        return

    low = arg.lower()
    if low.startswith("set "):
        city = arg[4:].strip()
        if not city:
            await message.edit_text("Укажи город", parse_mode=ParseMode.HTML)
            return
        _state["city"] = city
        _save_state(_state)
        await message.edit_text(
            f"<b>Город сохранён:</b> {html.escape(city)}",
            parse_mode=ParseMode.HTML,
        )
        return

    if low in ("top", "hot", "max"):
        await message.edit_text(
            "<i>опрашиваю города...</i>",
            parse_mode=ParseMode.HTML,
        )
        try:
            text = await _top(cold=False)
        except Exception as e:
            await message.edit_text(
                f"<b>Ошибка:</b> <code>{html.escape(str(e))}</code>",
                parse_mode=ParseMode.HTML,
            )
            return
        await message.edit_text(text, parse_mode=ParseMode.HTML)
        return

    if low in ("cold", "min"):
        await message.edit_text(
            "<i>опрашиваю города...</i>",
            parse_mode=ParseMode.HTML,
        )
        try:
            text = await _top(cold=True)
        except Exception as e:
            await message.edit_text(
                f"<b>Ошибка:</b> <code>{html.escape(str(e))}</code>",
                parse_mode=ParseMode.HTML,
            )
            return
        await message.edit_text(text, parse_mode=ParseMode.HTML)
        return

    await message.edit_text("<i>смотрю погоду...</i>", parse_mode=ParseMode.HTML)
    try:
        photo, _ = await _show_city_card(arg)
    except Exception as e:
        await message.edit_text(
            f"<b>Ошибка:</b> <code>{html.escape(str(e))}</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    try:
        await client.send_photo(message.chat.id, str(photo))
        await message.delete()
    except FloodWait as e:
        await message.edit_text(
            f"Telegram просит подождать {e.value} сек. Попробуй позже.",
            parse_mode=ParseMode.HTML,
        )


def register(app: Client):
    app.add_handler(
        MessageHandler(
            weather_handler,
            owners.auth & filters.command("weather", prefixes=PREFIXES),
        )
    )
