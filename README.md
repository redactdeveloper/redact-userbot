# Redact Userbot
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)
![C++](https://img.shields.io/badge/C++-00599C?style=for-the-badge&logo=cplusplus&logoColor=white)
![WTFPL](https://img.shields.io/badge/License-WTFPL-brightgreen?style=for-the-badge)
![Pyrogram](https://img.shields.io/badge/Pyrogram-2CA5E0?style=for-the-badge&logoColor=white)


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

On first launch, Pyrogram will create a local Telegram session file such as `userbot.session`. That file is ignored by Git.

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

## Module Reference

| Module | Commands | Description |
| --- | --- | --- |
| `afk` | `.afk [reason]`, `.unafk` | Enables AFK mode and auto-replies to private messages, mentions, and replies to you with cooldown protection. |
| `ai` | `.ai`, `.image`/`.img`, `.prompt`, `.model` | AI chat, image generation, system prompt management, and model selection through configured providers. |
| `automsg` | `.automsg`, `.automsg list`, `.automsg stop <id/all>` | Sends repeated messages to a target chat at intervals like `10s`, `5m`, `1h`, or `1d`. |
| `autoreplay` | `.autoreplay [on/off]` | AI auto-responder for pings and direct conversations with recent chat context and delay simulation. |
| `bio` | none | Disabled auto-bio updater. Can update account bio on a timer if enabled in code. |
| `calc` | `.calc <expr>` | Safe calculator with common math functions. |
| `commands` | `.modules` | Shows all loaded modules and their commands from `HELP` metadata. |
| `crypto` | `.crypto`, `.crypto <SYM>` | Shows top crypto prices or one selected coin such as `BTC` or `ETH`. |
| `cryptoparsing` | `.cryptoparsing`/`.cp`, `.cryptoparsing list`, `.cryptoparsing stop <id/all>` | Periodic crypto price tracking and reporting jobs. |
| `dance` | `.dance` | ASCII loading animation with a progress bar. |
| `download` | `.download`/`.dl` | Downloads replied Telegram media to local `downloads/`. |
| `grammatic` | `.grammatic`/`.gram [on/off]` | AI grammar correction for your outgoing text messages. |
| `help` | `.help` | Alias for the module list. |
| `id` | `.id` | Shows chat, user, and replied-message identifiers. |
| `info` | `.info` | Sends host and userbot information: uptime, CPU, memory, OS, GPU, and version details. |
| `logdelete` | `.logdelete`, `.logdelete here`, `.logdelete me` | Logs deleted private messages, including media type metadata, to Saved Messages or the current chat. |
| `moduleai_lox` | `.lox` | Replies `ку` when the command text is `ку`. |
| `newmodule` | `.newmodule`, `.newmodule cancel`, `.moduleai`, `.moduleai delete <name/all>` | Multi-step AI module generator and manager for generated modules. |
| `online` | `.online [on/off]` | Keeps account presence active while enabled. |
| `owner` | `.owner`, `.owner add`, `.owner rm` | Manages the owner whitelist. By default, only your own account is authorized. |
| `ping` | `.ping` | Measures response latency. |
| `prefixc` | `.prefixc`, `.prefixc list`, `.prefixc del`, `.prefixc clear` | Creates command aliases, for example `.prefixc weather .w`. |
| `profileclean` | `.profileclean` | Cleans profile fields according to module logic. |
| `purge` | `.purge`, `.purge <N>` | Deletes messages from a reply point to the command, or deletes the last `N` messages. |
| `qr` | `.qr`, `.qrread` | Generates QR codes and reads QR codes from replied images. |
| `rate` | none | Disabled USD/RUB last-name updater. Can update account last name on a timer if enabled in code. |
| `restart` | `.restart` | Restarts the running userbot process. |
| `scanner` | `.scanner` | OCR for replied images through the configured vision model. |
| `screen` | `.screen` | Captures a screenshot from the host and sends it as a document. |
| `spam` | `.spam <count> <text>` | Sends repeated messages. Use responsibly. |
| `ssh` | `.ssh`/`.sh <cmd>` | Executes a shell command on the host and returns stdout/stderr. |
| `stats` | `.stats`, `.stats=<N>`, `.stats rebuild`, `.stats import` | Fast chat statistics from cache, raw history rebuilds, and Telegram export imports. |
| `status` | `.status` | Checks operational status pages for popular AI services. |
| `top` | `.top [limit]` | Scans chat history and builds a top users list. `stats` is the newer faster path. |
| `translate` | `.tr`/`.translate [lang] <text>` | Translates replied or provided text; default target language is `ru`. |
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

При первом запуске Pyrogram создаст локальный файл Telegram-сессии, например `userbot.session`. Этот файл игнорируется Git.

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

## Описание модулей

| Модуль | Команды | Описание |
| --- | --- | --- |
| `afk` | `.afk [причина]`, `.unafk` | AFK-режим с автоответом в личке, на упоминания и ответы на твои сообщения. Есть cooldown. |
| `ai` | `.ai`, `.image`/`.img`, `.prompt`, `.model` | AI-чат, генерация картинок, системный промпт и выбор модели через провайдеры. |
| `automsg` | `.automsg`, `.automsg list`, `.automsg stop <id/all>` | Периодически отправляет сообщение в выбранный чат с интервалами `10s`, `5m`, `1h`, `1d`. |
| `autoreplay` | `.autoreplay [on/off]` | AI-автоответчик на пинги и активные диалоги с учетом контекста чата. |
| `bio` | нет | Отключенный автоапдейтер био. Может обновлять bio по таймеру, если включить в коде. |
| `calc` | `.calc <expr>` | Безопасный калькулятор с math-функциями. |
| `commands` | `.modules` | Показывает список всех модулей и команд из `HELP`-метаданных. |
| `crypto` | `.crypto`, `.crypto <SYM>` | Показывает топ криптовалют или одну монету, например `BTC` или `ETH`. |
| `cryptoparsing` | `.cryptoparsing`/`.cp`, `.cryptoparsing list`, `.cryptoparsing stop <id/all>` | Периодический трекинг и отправка цен криптовалют. |
| `dance` | `.dance` | ASCII-анимация загрузки с прогресс-баром. |
| `download` | `.download`/`.dl` | Скачивает медиа из реплая в локальную папку `downloads/`. |
| `grammatic` | `.grammatic`/`.gram [on/off]` | AI-коррекция грамматики в твоих исходящих сообщениях. |
| `help` | `.help` | Алиас для списка модулей. |
| `id` | `.id` | Показывает ID чата, пользователя и сообщения из реплая. |
| `info` | `.info` | Информация о хосте и userbot: uptime, CPU, RAM, OS, GPU, версия. |
| `logdelete` | `.logdelete`, `.logdelete here`, `.logdelete me` | Логирует удаленные сообщения из личек, включая тип медиа. |
| `moduleai_lox` | `.lox` | Отвечает `ку`, если текст команды равен `ку`. |
| `newmodule` | `.newmodule`, `.newmodule cancel`, `.moduleai`, `.moduleai delete <name/all>` | Многошаговая генерация и управление AI-модулями. |
| `online` | `.online [on/off]` | Поддерживает online-presence аккаунта. |
| `owner` | `.owner`, `.owner add`, `.owner rm` | Управляет whitelist владельцев. По умолчанию доступ есть только у твоего аккаунта. |
| `ping` | `.ping` | Измеряет задержку ответа. |
| `prefixc` | `.prefixc`, `.prefixc list`, `.prefixc del`, `.prefixc clear` | Создает алиасы команд, например `.prefixc weather .w`. |
| `profileclean` | `.profileclean` | Очищает поля профиля по логике модуля. |
| `purge` | `.purge`, `.purge <N>` | Удаляет сообщения от реплая до команды или последние `N` сообщений. |
| `qr` | `.qr`, `.qrread` | Генерирует QR-коды и распознает QR из изображений. |
| `rate` | нет | Отключенный апдейтер USD/RUB в last name. Может работать по таймеру, если включить в коде. |
| `restart` | `.restart` | Перезапускает userbot-процесс. |
| `scanner` | `.scanner` | OCR текста с изображения через vision-модель. |
| `screen` | `.screen` | Делает скриншот хоста и отправляет файлом. |
| `spam` | `.spam <count> <text>` | Повторно отправляет сообщение. Использовать осторожно. |
| `ssh` | `.ssh`/`.sh <cmd>` | Выполняет shell-команду на хосте и возвращает stdout/stderr. |
| `stats` | `.stats`, `.stats=<N>`, `.stats rebuild`, `.stats import` | Быстрая статистика чата из кэша, пересчет истории и импорт Telegram export. |
| `status` | `.status` | Проверяет status-страницы популярных AI-сервисов. |
| `top` | `.top [limit]` | Сканирует историю чата и строит топ пользователей. Новый быстрый путь — `stats`. |
| `translate` | `.tr`/`.translate [lang] <text>` | Переводит текст из реплая или аргумента команды; язык по умолчанию `ru`. |
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
