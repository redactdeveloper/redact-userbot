import html
import io
import json
from pathlib import Path

import aiohttp
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import providers
import owners
from config import ONLYSQ_IMAGE_MODEL, ONLYSQ_MODEL, PREFIXES

HELP = {
    "description": "ИИ через мульти-провайдерный роутинг",
    "commands": {
        ".ai <text>": "задать вопрос (или реплай)",
        ".image <text>": f"сгенерировать картинку ({ONLYSQ_IMAGE_MODEL})",
        ".prompt <text>": "задать системный промпт",
        ".prompt 0": "сбросить системный промпт",
        ".model": "показать список моделей",
        ".model <N|name>": "выбрать модель",
    },
}

TG_LIMIT = 4000
_STATE_FILE = Path(__file__).parent.parent / ".ai_state.json"


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


def _current_model() -> str:
    return _state.get("model") or ONLYSQ_MODEL


def _current_prompt() -> str:
    return _state.get("system_prompt") or ""


async def _ask(user_prompt: str) -> str:
    messages = []
    system_prompt = _current_prompt()
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    return await providers.chat(_current_model(), messages)


async def ai_handler(client: Client, message: Message):
    parts = (message.text or "").split(maxsplit=1)
    prompt = parts[1].strip() if len(parts) > 1 else ""
    if not prompt and message.reply_to_message:
        prompt = (
            message.reply_to_message.text
            or message.reply_to_message.caption
            or ""
        ).strip()
    if not prompt:
        await message.edit_text(
            "Использование: <code>.ai текст</code> (или реплай)",
            parse_mode=ParseMode.HTML,
        )
        return

    await message.edit_text("<i>думаю...</i>", parse_mode=ParseMode.HTML)
    try:
        answer = await _ask(prompt)
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

    answer = (answer or "").strip()
    if len(answer) > TG_LIMIT:
        answer = answer[:TG_LIMIT] + "..."

    text = (
        f"<b>Q:</b> {html.escape(prompt)}\n\n"
        f"<b>A ({html.escape(_current_model())}):</b>\n{html.escape(answer)}"
    )
    await message.edit_text(text, parse_mode=ParseMode.HTML)


async def image_handler(client: Client, message: Message):
    parts = (message.text or "").split(maxsplit=1)
    prompt = parts[1].strip() if len(parts) > 1 else ""
    if not prompt and message.reply_to_message:
        prompt = (
            message.reply_to_message.text
            or message.reply_to_message.caption
            or ""
        ).strip()
    if not prompt:
        await message.edit_text(
            "Использование: <code>.image описание</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    await message.edit_text("<i>генерирую...</i>", parse_mode=ParseMode.HTML)
    try:
        png = await providers.image(ONLYSQ_IMAGE_MODEL, prompt)
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

    buf = io.BytesIO(png)
    buf.name = "image.png"
    chat_id = message.chat.id
    reply_to = message.reply_to_message.id if message.reply_to_message else None
    try:
        await message.delete()
    except Exception:
        pass
    caption = (
        f"<b>{html.escape(ONLYSQ_IMAGE_MODEL)}</b>\n"
        f"<code>{html.escape(prompt[:800])}</code>"
    )
    await client.send_photo(
        chat_id,
        photo=buf,
        caption=caption,
        parse_mode=ParseMode.HTML,
        reply_to_message_id=reply_to,
    )


async def prompt_handler(client: Client, message: Message):
    parts = (message.text or "").split(maxsplit=1)
    arg = parts[1].strip() if len(parts) > 1 else ""

    if not arg:
        current = _current_prompt()
        if not current:
            text = "<i>Системный промпт не задан</i>"
        else:
            text = f"<b>Текущий промпт:</b>\n<code>{html.escape(current)}</code>"
        await message.edit_text(text, parse_mode=ParseMode.HTML)
        return

    if arg == "0":
        _state.pop("system_prompt", None)
        _save_state(_state)
        await message.edit_text("<b>Промпт сброшен.</b>", parse_mode=ParseMode.HTML)
        return

    _state["system_prompt"] = arg
    _save_state(_state)
    await message.edit_text(
        f"<b>Промпт установлен:</b>\n<code>{html.escape(arg)}</code>",
        parse_mode=ParseMode.HTML,
    )


async def model_handler(client: Client, message: Message):
    parts = (message.text or "").split(maxsplit=1)
    arg = parts[1].strip() if len(parts) > 1 else ""
    current = _current_model()

    models = providers.all_chat_models()

    if not arg:
        lines = [f"<b>Модели ({len(models)}):</b>", ""]
        current_provider = None
        n = 0
        for model_name, provider_name in models:
            n += 1
            if provider_name != current_provider:
                if current_provider is not None:
                    lines.append("")
                lines.append(f"<b>[{html.escape(provider_name)}]</b>")
                current_provider = provider_name
            mark = " ←" if model_name == current else ""
            lines.append(
                f"<code>{n:3d}.</code> {html.escape(model_name)}{mark}"
            )
        lines.append("")
        lines.append("<i>Выбрать:</i> <code>.model &lt;N&gt;</code>")
        await message.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)
        return

    selected: str | None = None
    if arg.isdigit():
        idx = int(arg) - 1
        if 0 <= idx < len(models):
            selected = models[idx][0]
    else:
        for m, _ in models:
            if m == arg:
                selected = m
                break

    if not selected:
        await message.edit_text(
            f"<b>Модель не найдена:</b> <code>{html.escape(arg)}</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    _state["model"] = selected
    _save_state(_state)
    provider = providers.find_chat_provider(selected)
    provider_name = provider["name"] if provider else "?"
    await message.edit_text(
        f"<b>Модель:</b> <code>{html.escape(selected)}</code> "
        f"[<i>{html.escape(provider_name)}</i>]",
        parse_mode=ParseMode.HTML,
    )


def register(app: Client):
    app.add_handler(
        MessageHandler(
            ai_handler,
            owners.auth & filters.command("ai", prefixes=PREFIXES),
        )
    )
    app.add_handler(
        MessageHandler(
            image_handler,
            owners.auth & filters.command(["image", "img"], prefixes=PREFIXES),
        )
    )
    app.add_handler(
        MessageHandler(
            prompt_handler,
            owners.auth & filters.command("prompt", prefixes=PREFIXES),
        )
    )
    app.add_handler(
        MessageHandler(
            model_handler,
            owners.auth & filters.command("model", prefixes=PREFIXES),
        )
    )
