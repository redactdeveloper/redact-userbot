import html
import io

import aiohttp
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "Генерация и распознавание QR-кодов",
    "commands": {
        ".qr <text>": "создать QR",
        ".qrread": "распознать QR из реплая на фото",
    },
}

GEN_URL = "https://api.qrserver.com/v1/create-qr-code/"
READ_URL = "https://api.qrserver.com/v1/read-qr-code/"


async def qr_handler(client: Client, message: Message):
    parts = (message.text or "").split(maxsplit=1)
    text = parts[1].strip() if len(parts) > 1 else ""
    if not text and message.reply_to_message:
        text = (
            message.reply_to_message.text
            or message.reply_to_message.caption
            or ""
        ).strip()
    if not text:
        await message.edit_text(
            "Использование: <code>.qr текст</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    await message.edit_text("<i>генерирую...</i>", parse_mode=ParseMode.HTML)
    params = {"data": text, "size": "500x500", "format": "png"}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(GEN_URL, params=params) as r:
                r.raise_for_status()
                png = await r.read()
    except Exception as e:
        await message.edit_text(
            f"<b>Ошибка:</b> <code>{html.escape(str(e))}</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    buf = io.BytesIO(png)
    buf.name = "qr.png"
    chat_id = message.chat.id
    reply_to = message.reply_to_message.id if message.reply_to_message else None
    try:
        await message.delete()
    except Exception:
        pass
    caption = f"QR: <code>{html.escape(text[:200])}</code>"
    await client.send_photo(
        chat_id,
        photo=buf,
        caption=caption,
        parse_mode=ParseMode.HTML,
        reply_to_message_id=reply_to,
    )


async def qr_read_handler(client: Client, message: Message):
    r = message.reply_to_message
    if not r or not (r.photo or r.document):
        await message.edit_text(
            "Сделай реплай на фото с QR",
            parse_mode=ParseMode.HTML,
        )
        return
    await message.edit_text("<i>читаю...</i>", parse_mode=ParseMode.HTML)
    try:
        buf = await r.download(in_memory=True)
        data = buf.getvalue()
        form = aiohttp.FormData()
        form.add_field("file", data, filename="qr.png", content_type="image/png")
        async with aiohttp.ClientSession() as s:
            async with s.post(READ_URL, data=form) as resp:
                resp.raise_for_status()
                res = await resp.json()
        decoded = res[0]["symbol"][0]["data"]
    except Exception as e:
        await message.edit_text(
            f"<b>Ошибка:</b> <code>{html.escape(str(e))}</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    if not decoded:
        await message.edit_text("QR не распознан", parse_mode=ParseMode.HTML)
        return

    await message.edit_text(
        f"<b>QR:</b>\n<code>{html.escape(decoded)}</code>",
        parse_mode=ParseMode.HTML,
    )


def register(app: Client):
    app.add_handler(
        MessageHandler(
            qr_handler,
            owners.auth & filters.command("qr", prefixes=PREFIXES),
        )
    )
    app.add_handler(
        MessageHandler(
            qr_read_handler,
            owners.auth & filters.command("qrread", prefixes=PREFIXES),
        )
    )
