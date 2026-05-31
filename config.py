import os
from pathlib import Path

_ENV_PATH = Path(__file__).with_name(".env")


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue

        if value and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        os.environ.setdefault(key, value)


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    raise RuntimeError(
        f"Missing required setting: {name}. Fill it in {_ENV_PATH} or environment."
    )


def _required_int(name: str) -> int:
    value = _required(name)
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer, got: {value!r}") from exc


def _list(name: str, default: str) -> list[str]:
    raw = os.environ.get(name, default)
    return [part.strip() for part in raw.split(",") if part.strip()]


_load_dotenv(_ENV_PATH)

API_ID = _required_int("API_ID")
API_HASH = _required("API_HASH")
SESSION_NAME = os.environ.get("SESSION_NAME", "userbot")
PREFIXES = _list("PREFIXES", ".,!")
TELEGRAM_DEVICE_MODEL = os.environ.get("TELEGRAM_DEVICE_MODEL", "Redact Desktop")
TELEGRAM_SYSTEM_VERSION = os.environ.get("TELEGRAM_SYSTEM_VERSION", "Linux")
TELEGRAM_APP_VERSION = os.environ.get("TELEGRAM_APP_VERSION", "redact userbot")
TELEGRAM_LANG_CODE = os.environ.get("TELEGRAM_LANG_CODE", "ru")

AI_URL = "https://api.onlysq.ru/ai/v2"
AI_KEY = _required("AI_KEY")
AI_MODEL = os.environ.get("AI_MODEL", "gpt-4o-mini")

AI_MODELS = [
    # Anthropic Claude
    "claude-opus-4-6",
    "claude-opus-4-5",
    "claude-sonnet-4-6",
    "claude-sonnet-4-5",
    "claude-haiku-4-5",
    # OpenAI GPT-5
    "gpt-5.4",
    "gpt-5.2",
    "gpt-5.2-chat",
    "gpt-5.1",
    "gpt-5",
    "gpt-5-chat",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-5-search",
    # OpenAI GPT-4
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    "chatgpt-4o",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-3.5-turbo",
    # OpenAI reasoning
    "o4-mini",
    "o3",
    "o3-mini",
    "o1",
    # OpenAI open-source
    "gpt-oss-120b",
    "gpt-oss-20b",
    # Google Gemini
    "gemini-3.1-pro",
    "gemini-3-flash",
    # xAI Grok
    "grok-4-1-fast",
    "grok-3",
    "grok-2-vision",
    # Qwen
    "qwen3-max",
    "qwen3-next-80b-a3b",
    "qwen3-235b-a22b-2507",
    "qwen3-coder-plus",
    "qwen-max-latest",
    "qwen-3-32b",
    # DeepSeek
    "deepseek-v3",
    "deepseek-r1",
    # Llama
    "llama-3.3-70b",
    "llama3.1-8b",
    # Mistral
    "mistral-small-3.1",
    # Cohere Command
    "command-a-03-2025",
    "command-r-plus-08-2024",
    "command-a-reasoning-08-2025",
    # Z.AI / GLM
    "zai-glm-4.6",
    "glm-4.7-flash",
    # Perplexity Sonar
    "sonar-pro",
    "sonar-reasoning-pro",
    "sonar-deep-research",
]

AI_IMAGE_MODELS = [
    "gpt-image-1.5",
    "gpt-image-1",
    "gpt-image-1-mini",
    "phoenix-1.0",
    "lucid-origin",
    "flux-2-dev",
    "flux-2-klein-9b",
    "flux-2-klein-4b",
    "flux",
    "grok-2-image",
]
AI_IMAGE_MODEL = os.environ.get("AI_IMAGE_MODEL", "gpt-image-1.5")
AI_VISION_MODEL = os.environ.get("AI_VISION_MODEL", "gpt-4o")

AI2_URL = "https://abuzgroup.lol/v1"
AI2_KEY = os.environ.get("AI2_KEY", "").strip()
AI2_MODELS = [
    "glm-5.1",
    "glm-5",
    "glm-4.7",
    "glm-4.6",
]

PROVIDERS = [
    {
        "name": "AI",
        "url": AI_URL,
        "key": AI_KEY,
        "models": AI_MODELS,
        "image_models": AI_IMAGE_MODELS,
        "style": "nested",
    },
]

if AI2_KEY:
    PROVIDERS.append(
        {
            "name": "AI2",
            "url": AI2_URL,
            "key": AI2_KEY,
            "models": AI2_MODELS,
            "image_models": [],
            "style": "openai",
        }
    )

BIO_TEMPLATE = "@redactdevbot / apichecker.dev | {ts}"
BIO_TIME_FORMAT = "%d.%m.%Y %H:%M"
BIO_INTERVAL = 60

USERBOT_NAME = "redact"
USERBOT_VERSION = "1.0.0"
USERBOT_BRANCH = "master"
INFO_IMAGE = os.path.join(os.path.dirname(__file__), "assets", "info")
