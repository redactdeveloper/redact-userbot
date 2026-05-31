import base64
import json

import aiohttp

from config import PROVIDERS


def find_chat_provider(model: str) -> dict | None:
    for p in PROVIDERS:
        if model in p.get("models", []):
            return p
    return None


def find_image_provider(model: str) -> dict | None:
    for p in PROVIDERS:
        if model in p.get("image_models", []):
            return p
    return None


def all_chat_models() -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for p in PROVIDERS:
        for m in p.get("models", []):
            result.append((m, p["name"]))
    return result


def all_image_models() -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for p in PROVIDERS:
        for m in p.get("image_models", []):
            result.append((m, p["name"]))
    return result


async def chat(model: str, messages: list[dict], timeout_s: float = 120) -> str:
    provider = find_chat_provider(model)
    if not provider:
        raise ValueError(f"модель не найдена: {model}")

    headers = {"Authorization": f"Bearer {provider['key']}"}
    style = provider.get("style", "openai")

    if style == "onlysq":
        url = provider["url"]
        payload = {
            "model": model,
            "request": {"messages": messages, "stream": False},
        }
    else:
        url = provider["url"].rstrip("/") + "/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
        }

    timeout = aiohttp.ClientTimeout(total=timeout_s)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.post(url, json=payload, headers=headers) as r:
            r.raise_for_status()
            data = await r.json()

    choices = data.get("choices") or []
    if not choices:
        raise ValueError(f"пустой ответ: {json.dumps(data, ensure_ascii=False)[:300]}")
    return (choices[0].get("message") or {}).get("content") or ""


async def image(model: str, prompt: str, size: str = "1024x1024") -> bytes:
    provider = find_image_provider(model)
    if not provider:
        raise ValueError(f"image-модель не найдена: {model}")

    headers = {"Authorization": f"Bearer {provider['key']}"}
    style = provider.get("style", "openai")

    if style == "onlysq":
        url = provider["url"]
        payload = {
            "model": model,
            "request": {"prompt": prompt, "n": 1, "size": size},
        }
    else:
        url = provider["url"].rstrip("/") + "/images/generations"
        payload = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size,
        }

    timeout = aiohttp.ClientTimeout(total=180)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.post(url, json=payload, headers=headers) as r:
            r.raise_for_status()
            data = await r.json()

    item: dict | None = None
    if isinstance(data.get("data"), list) and data["data"]:
        item = data["data"][0]
    elif isinstance(data.get("images"), list) and data["images"]:
        item = data["images"][0]

    url_field: str | None = None
    b64: str | None = None
    if isinstance(item, dict):
        url_field = item.get("url")
        b64 = item.get("b64_json") or item.get("b64")
    url_field = url_field or data.get("url")
    b64 = b64 or data.get("b64_json") or data.get("b64")

    if b64:
        return base64.b64decode(b64)
    if url_field:
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(url_field) as r:
                r.raise_for_status()
                return await r.read()

    raise ValueError(
        f"неизвестный формат: {json.dumps(data, ensure_ascii=False)[:500]}"
    )
