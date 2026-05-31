import base64
import html

import aiohttp
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import providers
import owners
from config import ONLYSQ_VISION_MODEL, PREFIXES

HELP = {
    "description": "OCR: распознать текст с картинки через vision-модель",
    "commands": {".scanner": "реплай на фото → извлечь текст"},
}

TG_LIMIT = 4000
OCR_PROMPT = (
    "Извлеки и верни ВЕСЬ текст с этого изображения точно так, как он там написан, "
    "с сохранением порядка строк и абзацев. "
    "Верни только сам текст, без комментариев, пояснений и разметки."
)


async def _ocr(image_bytes: bytes) -> str:
    b64 = base64.b64encode(image_bytes).decode()
    data_url = f"data:image/jpeg;base64,{b64}"
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": OCR_PROMPT},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
    ]
    text = await providers.chat(ONLYSQ_VISION_MODEL, messages, timeout_s=120)
    return (text or "").strip()


async def scanner_handler(client: Client, message: Message):
    r = message.reply_to_message
    if not r or not (r.photo or (r.document and r.document.mime_type and r.document.mime_type.startswith("image/"))):
        await message.edit_text(
            "Нужен реплай на фото",
            parse_mode=ParseMode.HTML,
        )
        return

    await message.edit_text("<i>сканирую...</i>", parse_mode=ParseMode.HTML)
    try:
        buf = await r.download(in_memory=True)
        image_bytes = buf.getvalue()
        text = await _ocr(image_bytes)
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

    if not text:
        await message.edit_text(
            "<i>Текст не найден на изображении</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    truncated = len(text) > TG_LIMIT
    if truncated:
        text = text[:TG_LIMIT] + "..."

    out = (
        f"<b>Scanner ({html.escape(ONLYSQ_VISION_MODEL)}):</b>\n"
        f"<blockquote>{html.escape(text)}</blockquote>"
    )
    await message.edit_text(out, parse_mode=ParseMode.HTML)


def register(app: Client):
    app.add_handler(
        MessageHandler(
            scanner_handler,
            owners.auth & filters.command("scanner", prefixes=PREFIXES),
        )
    )
