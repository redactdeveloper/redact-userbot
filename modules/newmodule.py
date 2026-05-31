import html
import re
from pathlib import Path

from pyrogram import Client, StopPropagation, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import owners
import providers
from config import PREFIXES

HELP = {
    "description": "Генерация и управление AI-модулями",
    "commands": {
        ".newmodule": "создать новый модуль через ИИ (многошагово)",
        ".newmodule cancel": "отменить текущий flow",
        ".moduleai": "список AI-модулей",
        ".moduleai delete <name>": "удалить AI-модуль",
        ".moduleai delete all": "удалить все AI-модули",
    },
}

MODULES_DIR = Path(__file__).parent
PREFIX = "moduleai_"

_flows: dict[int, dict] = {}

GEN_SYSTEM_PROMPT = """Ты — генератор модулей для существующего pyrogram v2 (kurigram) userbot'а.

=== ЧТО ЗА ПРОЕКТ ===

Это модульный userbot для Telegram на базе kurigram (форк pyrogram 2). Проект лежит в /home/redact/userbot/. Архитектура:

- main.py — точка входа, поднимает Client через asyncio.run, регистрирует модули и держит их горячий релоад (file watcher раз в секунду, подхватывает изменения modules/*.py без рестарта).
- config.py — константы: PREFIXES=[".", "!"], USERBOT_NAME/VERSION, OnlySQ/Abuz провайдеры AI, API_ID/HASH и т.д.
- providers.py — мульти-провайдерный роутинг к AI API. Функции:
    providers.chat(model: str, messages: list[dict], timeout_s: float = 120) -> str
    providers.image(model: str, prompt: str, size: str = "1024x1024") -> bytes
    providers.all_chat_models() -> list[tuple[model, provider]]
  messages в OpenAI-формате: [{"role": "system"/"user"/"assistant", "content": "..."}].
- owners.py — whitelist доступа. `owners.auth` — pyrogram-фильтр, который пропускает владельца и добавленных через .owner add.
- modules/*.py — собственно фичи. Watcher автоматически загружает register() и вызывает on_start/on_stop.

=== СТРУКТУРА МОДУЛЯ ===

Каждый модуль должен определять:

1. HELP dict:
   HELP = {
       "description": "краткое однострочное описание",
       "commands": {".имя": "что делает", ".имя <arg>": "..."},
   }
   Используется командой .commands для показа списка.

2. Одну или несколько async функций-хэндлеров с сигнатурой:
   async def handler(client: Client, message: Message): ...

3. Функцию register(app: Client) которая добавляет хэндлеры через MessageHandler.

4. Опционально — async функции on_start(app)/on_stop(app) для фоновых задач
   (они вызываются при загрузке/выгрузке модуля, используй для запуска/отмены asyncio.Task).

=== ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА КОДА ===

- ВЫДАВАЙ ТОЛЬКО валидный Python-код. Никакого markdown (```), никаких объяснений, никакого текста до или после кода.
- Всё должно компилироваться как есть, синтаксически корректно.
- Все command-хэндлеры фильтруются через owners.auth (НЕ filters.me), чтобы whitelist-пользователи тоже могли запускать:
    owners.auth & filters.command("name", prefixes=PREFIXES)
- Для отправки текста всегда parse_mode=ParseMode.HTML.
- Пользовательский ввод экранируй через html.escape() перед вставкой в HTML.
- Для обновления сообщения пользователя (если это твоя команда) используй message.edit_text(...).
- Для отправки нового сообщения — client.send_message(chat_id, text, parse_mode=...).
- При ошибках — перехватывай Exception и сообщай через edit_text с html-escape текстом ошибки.
- Если дергаешь внешний API — используй aiohttp, timeout ~15-60 секунд.
- Если нужно фоновое состояние — храни в JSON файле рядом с main.py (Path(__file__).parent.parent / ".имя_state.json").

=== СТАНДАРТНЫЕ ИМПОРТЫ ===

import html
import owners
from config import PREFIXES
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

Добавляй дополнительные по необходимости: asyncio, aiohttp, json, time, re, base64, pathlib.Path, providers.

=== ПРИМЕР ПРОСТОЙ КОМАНДЫ ===

import html
import owners
from config import PREFIXES
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

HELP = {
    "description": "поздороваться с миром",
    "commands": {".hello": "сказать привет"},
}


async def hello_handler(client: Client, message: Message):
    await message.edit_text(
        "<b>Hello, world!</b>",
        parse_mode=ParseMode.HTML,
    )


def register(app: Client):
    app.add_handler(
        MessageHandler(
            hello_handler,
            owners.auth & filters.command("hello", prefixes=PREFIXES),
        )
    )

=== ПРИМЕР С ИИ-ЗАПРОСОМ ===

import html
import owners
import providers
from config import ONLYSQ_MODEL, PREFIXES
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

HELP = {
    "description": "спросить у ии",
    "commands": {".joke": "рассказать шутку"},
}


async def joke_handler(client: Client, message: Message):
    await message.edit_text("<i>думаю...</i>", parse_mode=ParseMode.HTML)
    try:
        answer = await providers.chat(
            ONLYSQ_MODEL,
            [{"role": "user", "content": "Расскажи короткую программистскую шутку"}],
        )
    except Exception as e:
        await message.edit_text(
            f"<b>Ошибка:</b> <code>{html.escape(str(e))}</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    await message.edit_text(html.escape(answer.strip()), parse_mode=ParseMode.HTML)


def register(app: Client):
    app.add_handler(
        MessageHandler(
            joke_handler,
            owners.auth & filters.command("joke", prefixes=PREFIXES),
        )
    )

=== ПРИМЕР С ФОНОВОЙ ЗАДАЧЕЙ ===

import asyncio
import owners
from config import PREFIXES
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

HELP = {
    "description": "фоновый тикер каждую минуту",
    "commands": {".tick": "показать счётчик"},
}

_counter = {"n": 0}
_task: asyncio.Task | None = None


async def _loop():
    while True:
        _counter["n"] += 1
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            raise


async def tick_handler(client: Client, message: Message):
    await message.edit_text(
        f"<b>тик:</b> {_counter['n']}",
        parse_mode=ParseMode.HTML,
    )


def register(app: Client):
    app.add_handler(
        MessageHandler(
            tick_handler,
            owners.auth & filters.command("tick", prefixes=PREFIXES),
        )
    )


async def on_start(app: Client):
    global _task
    _task = asyncio.create_task(_loop())


async def on_stop(app: Client):
    global _task
    if _task and not _task.done():
        _task.cancel()
        try:
            await _task
        except (asyncio.CancelledError, Exception):
            pass
    _task = None

=== ТВОЯ ЗАДАЧА ===

По имени и описанию от пользователя — напиши полный корректный файл модуля, следуя шаблону выше. Одна главная команда должна совпадать с именем модуля. Добавляй дополнительные команды только если описание явно этого требует. Код должен быть минимальным, рабочим и синтаксически валидным.
"""


def _strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        first_nl = s.find("\n")
        if first_nl > 0:
            s = s[first_nl + 1:]
    if s.endswith("```"):
        s = s[:-3]
    return s.strip()


def _split_code(code: str, max_chars: int = 3800) -> list[str]:
    if len(code) <= max_chars:
        return [code]
    lines = code.splitlines(keepends=True)
    midpoint = len(lines) // 2
    first = "".join(lines[:midpoint])
    second = "".join(lines[midpoint:])
    if len(first) > max_chars:
        first = first[: max_chars - 20] + "\n...[обрезано]"
    if len(second) > max_chars:
        second = second[: max_chars - 20] + "\n...[обрезано]"
    return [first, second]


async def newmodule_handler(client: Client, message: Message):
    parts = (message.text or "").split(maxsplit=1)
    arg = parts[1].strip().lower() if len(parts) > 1 else ""

    if arg == "cancel":
        _flows.pop(message.chat.id, None)
        await message.edit_text(
            "<i>flow отменён</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    _flows[message.chat.id] = {"step": "name", "data": {}}
    await message.edit_text(
        "<b>Новый модуль</b>\n\n"
        "Как назвать? (a-z, 0-9, _; начинать с буквы)",
        parse_mode=ParseMode.HTML,
    )


async def flow_handler(client: Client, message: Message):
    chat_id = message.chat.id
    flow = _flows.get(chat_id)
    if not flow:
        return

    text = (message.text or "").strip()
    if not text:
        return

    step = flow["step"]

    if step == "name":
        name = text.lower()
        if not re.match(r"^[a-z][a-z0-9_]*$", name):
            await client.send_message(
                chat_id,
                "Имя должно быть a-z / 0-9 / _, начинаться с буквы",
                parse_mode=ParseMode.HTML,
            )
            raise StopPropagation
        if (MODULES_DIR / f"{PREFIX}{name}.py").exists():
            await client.send_message(
                chat_id,
                f"Уже существует: <code>{html.escape(name)}</code>",
                parse_mode=ParseMode.HTML,
            )
            raise StopPropagation
        flow["data"]["name"] = name
        flow["step"] = "model"
        models = providers.all_chat_models()
        lines = [
            f"<b>Имя:</b> <code>{html.escape(name)}</code>",
            "",
            "<b>Выбери модель (отправь номер):</b>",
            "",
        ]
        cur = None
        for i, (m, p) in enumerate(models, 1):
            if p != cur:
                if cur is not None:
                    lines.append("")
                lines.append(f"<b>[{html.escape(p)}]</b>")
                cur = p
            lines.append(f"<code>{i:3d}.</code> {html.escape(m)}")
        await client.send_message(
            chat_id, "\n".join(lines), parse_mode=ParseMode.HTML
        )
        raise StopPropagation

    if step == "model":
        try:
            idx = int(text) - 1
        except ValueError:
            await client.send_message(
                chat_id,
                "Отправь номер модели",
                parse_mode=ParseMode.HTML,
            )
            raise StopPropagation
        models = providers.all_chat_models()
        if not (0 <= idx < len(models)):
            await client.send_message(
                chat_id,
                "Номер вне диапазона",
                parse_mode=ParseMode.HTML,
            )
            raise StopPropagation
        chosen = models[idx][0]
        flow["data"]["model"] = chosen
        flow["step"] = "desc"
        await client.send_message(
            chat_id,
            f"<b>Модель:</b> <code>{html.escape(chosen)}</code>\n\n"
            f"Опиши что должен делать модуль:",
            parse_mode=ParseMode.HTML,
        )
        raise StopPropagation

    if step == "desc":
        name = flow["data"]["name"]
        model = flow["data"]["model"]
        desc = text
        _flows.pop(chat_id, None)

        status = await client.send_message(
            chat_id,
            f"<b>генерирую через {html.escape(model)}...</b>",
            parse_mode=ParseMode.HTML,
        )

        try:
            code = await providers.chat(
                model,
                [
                    {"role": "system", "content": GEN_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Имя модуля и имя главной команды: {name}\n"
                            f"Описание: {desc}\n\n"
                            "Сгенерируй полный Python-файл модуля."
                        ),
                    },
                ],
                timeout_s=180,
            )
        except Exception as e:
            await status.edit_text(
                f"<b>Ошибка генерации:</b> <code>{html.escape(str(e))}</code>",
                parse_mode=ParseMode.HTML,
            )
            raise StopPropagation

        code = _strip_fences(code)
        if not code:
            await status.edit_text(
                "<b>Пустой ответ от ИИ</b>",
                parse_mode=ParseMode.HTML,
            )
            raise StopPropagation

        try:
            compile(code, f"{name}.py", "exec")
        except SyntaxError as e:
            await status.edit_text(
                f"<b>Синтаксическая ошибка в коде ИИ:</b>\n"
                f"<code>{html.escape(str(e))}</code>\n\n"
                f"Попробуй с другой моделью.",
                parse_mode=ParseMode.HTML,
            )
            raise StopPropagation

        filepath = MODULES_DIR / f"{PREFIX}{name}.py"
        try:
            filepath.write_text(code, encoding="utf-8")
        except Exception as e:
            await status.edit_text(
                f"<b>Не удалось записать файл:</b> <code>{html.escape(str(e))}</code>",
                parse_mode=ParseMode.HTML,
            )
            raise StopPropagation

        added = len(code.splitlines())
        await status.edit_text(
            f"<b>{html.escape(model)}</b> → "
            f"<code>{PREFIX}{html.escape(name)}.py</code>\n"
            f"<i>(+{added} -0)</i>",
            parse_mode=ParseMode.HTML,
        )

        chunks = _split_code(code)
        total = len(chunks)
        for i, chunk in enumerate(chunks, 1):
            header = f"<b>[{i}/{total}]</b>\n" if total > 1 else ""
            await client.send_message(
                chat_id,
                f"{header}<pre>{html.escape(chunk)}</pre>",
                parse_mode=ParseMode.HTML,
            )

        raise StopPropagation


async def moduleai_handler(client: Client, message: Message):
    parts = (message.text or "").split(maxsplit=2)
    sub = parts[1].strip().lower() if len(parts) > 1 else ""

    files = sorted(MODULES_DIR.glob(f"{PREFIX}*.py"))

    if not sub or sub == "list":
        if not files:
            await message.edit_text(
                "<i>Нет AI-модулей</i>",
                parse_mode=ParseMode.HTML,
            )
            return
        lines = [f"<b>AI-модули ({len(files)}):</b>", ""]
        for f in files:
            name = f.stem[len(PREFIX):]
            lines.append(f"<code>{html.escape(name)}</code>")
        await message.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)
        return

    if sub == "delete":
        if len(parts) < 3:
            await message.edit_text(
                "Укажи имя или <code>all</code>",
                parse_mode=ParseMode.HTML,
            )
            return
        target = parts[2].strip().lower()
        if target == "all":
            deleted = 0
            for f in files:
                try:
                    f.unlink()
                    deleted += 1
                except Exception:
                    pass
            await message.edit_text(
                f"<b>Удалено:</b> {deleted}",
                parse_mode=ParseMode.HTML,
            )
            return
        filepath = MODULES_DIR / f"{PREFIX}{target}.py"
        if not filepath.exists():
            await message.edit_text(
                f"<code>{html.escape(target)}</code> не найден",
                parse_mode=ParseMode.HTML,
            )
            return
        try:
            filepath.unlink()
            await message.edit_text(
                f"<b>Удалён:</b> <code>{html.escape(target)}</code>",
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            await message.edit_text(
                f"<b>Ошибка:</b> <code>{html.escape(str(e))}</code>",
                parse_mode=ParseMode.HTML,
            )
        return

    await message.edit_text(
        "<code>.moduleai</code> | <code>.moduleai delete &lt;name&gt;</code> | "
        "<code>.moduleai delete all</code>",
        parse_mode=ParseMode.HTML,
    )


def register(app: Client):
    app.add_handler(
        MessageHandler(
            newmodule_handler,
            owners.auth & filters.command("newmodule", prefixes=PREFIXES),
        )
    )
    app.add_handler(
        MessageHandler(
            moduleai_handler,
            owners.auth & filters.command("moduleai", prefixes=PREFIXES),
        )
    )
    app.add_handler(
        MessageHandler(flow_handler, owners.auth & filters.text),
        group=10,
    )
