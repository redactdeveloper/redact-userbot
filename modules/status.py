import asyncio
import html

import aiohttp
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "Operational-статус AI-сервисов со status-страниц",
    "commands": {".status": "проверить популярные AI"},
}

SERVICES: list[tuple[str, str]] = [
    ("OpenAI", "https://status.openai.com/api/v2/status.json"),
    ("Anthropic", "https://status.anthropic.com/api/v2/status.json"),
    ("Mistral", "https://mistral.statuspage.io/api/v2/status.json"),
    ("Groq", "https://groqstatus.com/api/v2/status.json"),
    ("Perplexity", "https://perplexity.statuspage.io/api/v2/status.json"),
    ("Cohere", "https://status.cohere.com/api/v2/status.json"),
    ("Together", "https://status.together.ai/api/v2/status.json"),
    ("Fireworks", "https://status.fireworks.ai/api/v2/status.json"),
    ("Copilot", "https://www.githubstatus.com/api/v2/status.json"),
    ("Replicate", "https://replicatestatus.com/api/v2/status.json"),
]

TIMEOUT = 8.0

INDICATOR_LABEL = {
    "none": "Operational",
    "minor": "Minor issue",
    "major": "Major outage",
    "critical": "Critical outage",
    "maintenance": "Maintenance",
}

MARK = {
    "none": "+",
    "minor": "!",
    "major": "x",
    "critical": "x",
    "maintenance": "m",
}


async def _check(sess: aiohttp.ClientSession, name: str, url: str):
    try:
        async with sess.get(url) as r:
            r.raise_for_status()
            data = await r.json(content_type=None)
    except asyncio.TimeoutError:
        return name, "?", "timeout", ""
    except Exception as e:
        return name, "?", type(e).__name__, ""

    st = data.get("status") or {}
    indicator = st.get("indicator") or ""
    description = st.get("description") or ""
    label = INDICATOR_LABEL.get(indicator, indicator or "unknown")
    return name, MARK.get(indicator, "?"), label, description


async def status_handler(client: Client, message: Message):
    await message.edit_text(
        "<i>опрашиваю status-страницы...</i>",
        parse_mode=ParseMode.HTML,
    )

    timeout = aiohttp.ClientTimeout(total=TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        results = await asyncio.gather(
            *(_check(s, name, url) for name, url in SERVICES)
        )

    max_name = max(len(name) for name, _ in SERVICES)
    lines = ["<b>AI статус (по status-страницам):</b>", ""]
    ok_count = 0
    for name, mark, label, desc in results:
        if mark == "+":
            ok_count += 1
        pad = name.ljust(max_name)
        line = f"<code>[{mark}] {html.escape(pad)}</code>  {html.escape(label)}"
        if desc and desc.lower() != label.lower():
            line += f" <i>— {html.escape(desc)}</i>"
        lines.append(line)
    lines.append("")
    lines.append(f"<i>operational: {ok_count}/{len(SERVICES)}</i>")

    await message.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)


def register(app: Client):
    app.add_handler(
        MessageHandler(
            status_handler,
            owners.auth & filters.command("status", prefixes=PREFIXES),
        )
    )
