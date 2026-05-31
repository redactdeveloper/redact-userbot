# Redact Userbot

Modular Telegram userbot written in Python. It loads modules dynamically, keeps command access owner-only by default, and uses a local `.env` file for Telegram and AI provider credentials.

## Features

- Dynamic module discovery from `modules/*.py`
- Owner whitelist for command access
- Telegram session stored locally and ignored by Git
- AI chat, image generation, OCR, grammar correction, and auto-replies through configurable providers
- Chat statistics, weather cards, QR tools, downloads, screenshots, shell execution, automation helpers
- Runtime state stored in ignored local JSON files

## Requirements

- Python 3.12+
- Telegram API credentials: `API_ID` and `API_HASH`
- AI API key for AI modules: `AI_KEY`
- Optional second AI provider key: `AI2_KEY`
- Optional system tools:
  - `g++` for the native stats worker
  - `grim`, `grimblast`, `hyprshot`, `scrot`, `gnome-screenshot`, `spectacle`, or `maim` for screenshots

## Installation

```bash
cd /path/to/userbot
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

```env
API_ID=12345678
API_HASH=your_telegram_api_hash
SESSION_NAME=userbot
PREFIXES=.,!

AI_KEY=your_ai_key
AI_MODEL=gpt-4o-mini
AI_IMAGE_MODEL=gpt-image-1.5
AI_VISION_MODEL=gpt-4o

AI2_KEY=
```

## Running

```bash
python main.py
```

On first launch, Pyrogram will create a local Telegram session file such as `userbot.session`. That file is ignored by Git and must never be committed.

## Configuration

| Variable | Required | Description |
| --- | --- | --- |
| `API_ID` | Yes | Telegram app API ID |
| `API_HASH` | Yes | Telegram app API hash |
| `SESSION_NAME` | No | Local Pyrogram session name, default `userbot` |
| `PREFIXES` | No | Command prefixes, default `.,!` |
| `TELEGRAM_DEVICE_MODEL` | No | Device name shown to Telegram |
| `TELEGRAM_SYSTEM_VERSION` | No | System version shown to Telegram |
| `TELEGRAM_APP_VERSION` | No | App version shown to Telegram |
| `TELEGRAM_LANG_CODE` | No | Telegram language code |
| `AI_KEY` | Yes | Main AI provider key |
| `AI_MODEL` | No | Default chat model |
| `AI_IMAGE_MODEL` | No | Default image model |
| `AI_VISION_MODEL` | No | Default vision/OCR model |
| `AI2_KEY` | No | Optional secondary AI provider key |

## Security Notes

- Keep `.env`, `*.session`, state files, and downloads out of Git.
- Use `.owner` carefully: added owners can run protected commands.
- `.ssh` executes shell commands on the host. Restrict owners carefully.
- `.automsg`, `.spam`, `.autoreplay`, `.grammatic`, `.online`, `.logdelete`, `bio`, and `rate` can automate account behavior. Use them conservatively.
- If a key or session was ever exposed, revoke it at the provider or in Telegram and create a new one.

## Module Reference

| Module | Commands | Description |
| --- | --- | --- |
| `afk` | `.afk [reason]`, `.unafk` | Enables AFK mode and auto-replies to private messages, mentions, and replies to you with cooldown protection. |
| `ai` | `.ai`, `.image`/`.img`, `.prompt`, `.model` | AI chat, image generation, system prompt management, and model selection through configured providers. |
| `automsg` | `.automsg`, `.automsg list`, `.automsg stop <id|all>` | Sends repeated messages to a target chat at intervals like `10s`, `5m`, `1h`, or `1d`. |
| `autoreplay` | `.autoreplay [on|off]` | AI auto-responder for pings and direct conversations with recent chat context and delay simulation. |
| `bio` | none | Disabled auto-bio updater. Can update account bio on a timer if enabled in code. |
| `calc` | `.calc <expression>` | Safe calculator for arithmetic expressions. |
| `commands` | `.modules` | Builds a help overview from module `HELP` metadata. |
| `crypto` | `.crypto <symbol>` | Fetches cryptocurrency price data. |
| `cryptoparsing` | `.cryptoparsing`/`.cp`, `.cryptoparsing list`, `.cryptoparsing stop <id|all>` | Periodic crypto price tracking and reporting jobs. |
| `dance` | `.dance` | Animated text progress/dance effect. |
| `download` | `.download`/`.dl` | Downloads replied Telegram media to local `downloads/`. |
| `grammatic` | `.grammatic`/`.gram [on|off]` | AI grammar correction for your outgoing text messages. |
| `help` | `.help` | Basic help entry point. |
| `id` | `.id` | Shows chat, user, and replied-message identifiers. |
| `info` | `.info` | Sends host and userbot information: uptime, CPU, memory, OS, GPU, and version details. |
| `logdelete` | `.logdelete`, `.logdelete here`, `.logdelete me` | Logs deleted private messages, including media type metadata, to Saved Messages or the current chat. |
| `moduleai_lox` | `.lox` | Small AI-powered text command. |
| `newmodule` | `.newmodule`, `.moduleai`, `.name`, `.hello`, `.joke`, `.tick` | Generates or experiments with modules and helper demo commands. Review generated code before keeping it. |
| `online` | `.online [on|off]` | Keeps account presence active while enabled. |
| `owner` | `.owner`, `.owner add`, `.owner rm` | Manages the owner whitelist. By default, only your own account is authorized. |
| `ping` | `.ping` | Measures response latency. |
| `prefixc` | `.prefixc`, `.prefixc list`, `.prefixc del`, `.prefixc clear` | Creates command aliases, for example `.prefixc weather .w`. |
| `profileclean` | `.profileclean` | Cleans profile fields according to module logic. |
| `purge` | `.purge` | Deletes messages in bulk from a reply point. |
| `qr` | `.qr`, `.qrread` | Generates QR codes and reads QR codes from replied images. |
| `rate` | none | Disabled USD/RUB last-name updater. Can update account last name on a timer if enabled in code. |
| `restart` | `.restart` | Restarts the running userbot process. |
| `scanner` | `.scanner` | OCR for replied images through the configured vision model. |
| `screen` | `.screen` | Captures a screenshot from the host and sends it as a document. |
| `spam` | `.spam <count> <text>` | Sends repeated messages. Use responsibly. |
| `ssh` | `.ssh`/`.sh <cmd>` | Executes a shell command on the host and returns stdout/stderr. |
| `stats` | `.stats`, `.stats=<N>`, `.stats rebuild`, `.stats import` | Fast chat statistics from cache, raw history rebuilds, and Telegram export imports. |
| `status` | `.status` | Checks service status endpoints. |
| `top` | `.top [limit]` | Scans chat history and builds a top users list. `stats` is the newer faster path. |
| `translate` | `.tr`/`.translate` | Translates replied or provided text. |
| `type` | `.type <text>` | Typing animation by editing the command message. |
| `weather` | `.weather`, `.weather set`, `.weather top`, `.weather cold` | Weather lookup, saved city, hot/cold city rankings, and rendered weather cards. |

## Runtime Files

These files can appear while the bot runs and are intentionally ignored:

- `.env`
- `*.session`, `*.session-journal`, `*.session-wal`, `*.session-shm`
- `.*_state.json`
- `.owners.json`
- `.prefixc_aliases.json`
- `.stats_cache.json`
- `downloads/`
- `bin/`
- `__pycache__/`

---

# Redact Userbot [RU]

Модульный Telegram userbot на Python. Он динамически загружает модули из `modules/`, по умолчанию разрешает команды только владельцу аккаунта и хранит ключи в локальном `.env`.

## Возможности

- Динамическая загрузка модулей из `modules/*.py`
- Whitelist владельцев для доступа к командам
- Локальная Telegram-сессия, исключенная из Git
- AI-чат, генерация изображений, OCR, коррекция грамматики и автоответы через провайдеры
- Статистика чатов, погода, QR, скачивание медиа, скриншоты, shell-команды и автоматизация
- Runtime-состояние хранится в локальных JSON-файлах, исключенных из Git

## Требования

- Python 3.12+
- Telegram credentials: `API_ID` и `API_HASH`
- AI API key для AI-модулей: `AI_KEY`
- Опционально второй AI provider key: `AI2_KEY`
- Опциональные системные утилиты:
  - `g++` для нативного worker статистики
  - `grim`, `grimblast`, `hyprshot`, `scrot`, `gnome-screenshot`, `spectacle` или `maim` для скриншотов

## Установка

```bash
cd /path/to/userbot
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Заполни `.env`:

```env
API_ID=12345678
API_HASH=your_telegram_api_hash
SESSION_NAME=userbot
PREFIXES=.,!

AI_KEY=your_ai_key
AI_MODEL=gpt-4o-mini
AI_IMAGE_MODEL=gpt-image-1.5
AI_VISION_MODEL=gpt-4o

AI2_KEY=
```

## Запуск

```bash
python main.py
```

При первом запуске Pyrogram создаст локальный файл Telegram-сессии, например `userbot.session`. Этот файл игнорируется Git и не должен попадать в репозиторий.

## Настройки

| Переменная | Обязательная | Описание |
| --- | --- | --- |
| `API_ID` | Да | Telegram app API ID |
| `API_HASH` | Да | Telegram app API hash |
| `SESSION_NAME` | Нет | Имя локальной Pyrogram-сессии, по умолчанию `userbot` |
| `PREFIXES` | Нет | Префиксы команд, по умолчанию `.,!` |
| `TELEGRAM_DEVICE_MODEL` | Нет | Название устройства для Telegram |
| `TELEGRAM_SYSTEM_VERSION` | Нет | Версия системы для Telegram |
| `TELEGRAM_APP_VERSION` | Нет | Версия приложения для Telegram |
| `TELEGRAM_LANG_CODE` | Нет | Язык Telegram |
| `AI_KEY` | Да | Ключ основного AI-провайдера |
| `AI_MODEL` | Нет | Модель чата по умолчанию |
| `AI_IMAGE_MODEL` | Нет | Модель изображений по умолчанию |
| `AI_VISION_MODEL` | Нет | Vision/OCR модель по умолчанию |
| `AI2_KEY` | Нет | Ключ дополнительного AI-провайдера |

## Безопасность

- Не коммить `.env`, `*.session`, state-файлы и `downloads/`.
- Аккуратно используй `.owner`: добавленные владельцы получают доступ к защищенным командам.
- `.ssh` выполняет shell-команды на хосте. Не выдавай owner-доступ лишним людям.
- `.automsg`, `.spam`, `.autoreplay`, `.grammatic`, `.online`, `.logdelete`, `bio` и `rate` автоматизируют поведение аккаунта. Используй осторожно.
- Если ключ или сессия когда-либо были раскрыты, отзови их у провайдера или в Telegram и создай новые.

## Описание модулей

| Модуль | Команды | Описание |
| --- | --- | --- |
| `afk` | `.afk [причина]`, `.unafk` | AFK-режим с автоответом в личке, на упоминания и ответы на твои сообщения. Есть cooldown. |
| `ai` | `.ai`, `.image`/`.img`, `.prompt`, `.model` | AI-чат, генерация картинок, системный промпт и выбор модели через провайдеры. |
| `automsg` | `.automsg`, `.automsg list`, `.automsg stop <id|all>` | Периодически отправляет сообщение в выбранный чат с интервалами `10s`, `5m`, `1h`, `1d`. |
| `autoreplay` | `.autoreplay [on|off]` | AI-автоответчик на пинги и активные диалоги с учетом контекста чата. |
| `bio` | нет | Отключенный автоапдейтер био. Может обновлять bio по таймеру, если включить в коде. |
| `calc` | `.calc <выражение>` | Безопасный калькулятор арифметических выражений. |
| `commands` | `.modules` | Собирает список команд из `HELP`-метаданных модулей. |
| `crypto` | `.crypto <symbol>` | Получает цену криптовалюты. |
| `cryptoparsing` | `.cryptoparsing`/`.cp`, `.cryptoparsing list`, `.cryptoparsing stop <id|all>` | Периодический трекинг и отправка цен криптовалют. |
| `dance` | `.dance` | Анимированный текстовый эффект. |
| `download` | `.download`/`.dl` | Скачивает медиа из реплая в локальную папку `downloads/`. |
| `grammatic` | `.grammatic`/`.gram [on|off]` | AI-коррекция грамматики в твоих исходящих сообщениях. |
| `help` | `.help` | Базовая справка. |
| `id` | `.id` | Показывает ID чата, пользователя и сообщения из реплая. |
| `info` | `.info` | Информация о хосте и userbot: uptime, CPU, RAM, OS, GPU, версия. |
| `logdelete` | `.logdelete`, `.logdelete here`, `.logdelete me` | Логирует удаленные сообщения из личек, включая тип медиа. |
| `moduleai_lox` | `.lox` | Небольшая AI-команда для текста. |
| `newmodule` | `.newmodule`, `.moduleai`, `.name`, `.hello`, `.joke`, `.tick` | Генерация/эксперименты с модулями и демо-команды. Сгенерированный код нужно проверять. |
| `online` | `.online [on|off]` | Поддерживает online-presence аккаунта. |
| `owner` | `.owner`, `.owner add`, `.owner rm` | Управляет whitelist владельцев. По умолчанию доступ есть только у твоего аккаунта. |
| `ping` | `.ping` | Измеряет задержку ответа. |
| `prefixc` | `.prefixc`, `.prefixc list`, `.prefixc del`, `.prefixc clear` | Создает алиасы команд, например `.prefixc weather .w`. |
| `profileclean` | `.profileclean` | Очищает поля профиля по логике модуля. |
| `purge` | `.purge` | Массово удаляет сообщения от точки реплая. |
| `qr` | `.qr`, `.qrread` | Генерирует QR-коды и распознает QR из изображений. |
| `rate` | нет | Отключенный апдейтер USD/RUB в last name. Может работать по таймеру, если включить в коде. |
| `restart` | `.restart` | Перезапускает userbot-процесс. |
| `scanner` | `.scanner` | OCR текста с изображения через vision-модель. |
| `screen` | `.screen` | Делает скриншот хоста и отправляет файлом. |
| `spam` | `.spam <count> <text>` | Повторно отправляет сообщение. Использовать осторожно. |
| `ssh` | `.ssh`/`.sh <cmd>` | Выполняет shell-команду на хосте и возвращает stdout/stderr. |
| `stats` | `.stats`, `.stats=<N>`, `.stats rebuild`, `.stats import` | Быстрая статистика чата из кэша, пересчет истории и импорт Telegram export. |
| `status` | `.status` | Проверяет статусы сервисов. |
| `top` | `.top [limit]` | Сканирует историю чата и строит топ пользователей. Новый быстрый путь — `stats`. |
| `translate` | `.tr`/`.translate` | Переводит текст из реплая или аргумента команды. |
| `type` | `.type <text>` | Анимация печати через редактирование сообщения. |
| `weather` | `.weather`, `.weather set`, `.weather top`, `.weather cold` | Погода, сохраненный город, рейтинги жары/холода и погодные карточки. |

## Локальные файлы

Эти файлы появляются при работе и специально игнорируются:

- `.env`
- `*.session`, `*.session-journal`, `*.session-wal`, `*.session-shm`
- `.*_state.json`
- `.owners.json`
- `.prefixc_aliases.json`
- `.stats_cache.json`
- `downloads/`
- `bin/`
- `__pycache__/`
