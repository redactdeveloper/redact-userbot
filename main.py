import asyncio
import importlib
import os
import pkgutil
import subprocess
import signal
import sys
import time
import traceback
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_VENV_PYTHON = _ROOT / ".venv" / "bin" / "python"


def _apply_time_offset():
    raw_offset = os.environ.get("TELEGRAM_TIME_OFFSET_SECONDS", "").strip()
    if not raw_offset:
        return
    try:
        offset = float(raw_offset)
    except ValueError:
        print(f"[time] bad TELEGRAM_TIME_OFFSET_SECONDS: {raw_offset!r}", flush=True)
        return
    original_time = time.time
    time.time = lambda: original_time() + offset
    print(f"[time] applied Telegram time offset: {offset:.1f}s", flush=True)


def _ensure_local_python():
    if _VENV_PYTHON.exists() and Path(sys.executable).resolve() != _VENV_PYTHON.resolve():
        env = os.environ.copy()
        env["PATH"] = f"{_VENV_PYTHON.parent}:{env.get('PATH', '')}"
        result = subprocess.run([str(_VENV_PYTHON), __file__, *sys.argv[1:]], env=env)
        raise SystemExit(result.returncode)


_ensure_local_python()
_apply_time_offset()

if sys.version_info >= (3, 14):
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client

from config import (
    API_HASH,
    API_ID,
    SESSION_NAME,
    TELEGRAM_APP_VERSION,
    TELEGRAM_DEVICE_MODEL,
    TELEGRAM_LANG_CODE,
    TELEGRAM_SYSTEM_VERSION,
)
import modules


def _log(message: str):
    print(message, flush=True)


app: Client

_mod_handlers: dict[str, list] = {}
_mod_mtimes: dict[str, float] = {}
_modules_dir = Path(modules.__path__[0])


def _create_client() -> Client:
    client = Client(
        SESSION_NAME,
        api_id=API_ID,
        api_hash=API_HASH,
        app_version=TELEGRAM_APP_VERSION,
        device_model=TELEGRAM_DEVICE_MODEL,
        system_version=TELEGRAM_SYSTEM_VERSION,
        lang_code=TELEGRAM_LANG_CODE,
    )
    client.start_time = time.time()
    return client


def _discover() -> list[str]:
    return [name for _, name, _ in pkgutil.iter_modules(modules.__path__)]


async def _load(name: str):
    full = f"modules.{name}"
    path = _modules_dir / f"{name}.py"
    _log(f"[load] {name}")

    orig_add = app.add_handler
    added: list = []

    def tracked(handler, group=0):
        result = orig_add(handler, group)
        added.append((handler, group))
        return result

    app.add_handler = tracked  # type: ignore[method-assign]
    try:
        if full in sys.modules:
            mod = importlib.reload(sys.modules[full])
        else:
            mod = importlib.import_module(full)
        if hasattr(mod, "register"):
            mod.register(app)
    finally:
        app.add_handler = orig_add  # type: ignore[method-assign]

    _mod_handlers[name] = added
    _mod_mtimes[name] = path.stat().st_mtime if path.exists() else 0.0

    if hasattr(mod, "on_start"):
        try:
            await mod.on_start(app)
        except Exception:
            traceback.print_exc()


async def _unload(name: str):
    full = f"modules.{name}"
    mod = sys.modules.get(full)
    if mod and hasattr(mod, "on_stop"):
        try:
            await mod.on_stop(app)
        except Exception:
            traceback.print_exc()

    for handler, group in _mod_handlers.pop(name, []):
        try:
            app.remove_handler(handler, group)
        except Exception:
            pass


async def _reload(name: str):
    _log(f"[reload] {name}")
    try:
        await _unload(name)
        await _load(name)
    except Exception:
        _log(f"[reload] {name} failed:")
        traceback.print_exc()


async def _watcher():
    while True:
        await asyncio.sleep(1.0)
        try:
            current = set(_discover())
            for name in current:
                path = _modules_dir / f"{name}.py"
                if not path.exists():
                    continue
                mtime = path.stat().st_mtime
                prev = _mod_mtimes.get(name)
                if prev is None:
                    await _load(name)
                elif mtime > prev:
                    await _reload(name)
            for name in list(_mod_handlers):
                if name not in current:
                    _log(f"[reload] {name} removed")
                    await _unload(name)
                    _mod_mtimes.pop(name, None)
        except asyncio.CancelledError:
            raise
        except Exception:
            traceback.print_exc()


async def _main():
    global app
    app = _create_client()

    _log("[start] connecting to Telegram")
    await app.start()
    me = await app.get_me()
    _log(
        f"[start] connected as @{me.username}" if me.username else f"[start] connected as {me.id}"
    )

    for name in _discover():
        await _load(name)
    _log(f"[+] loaded modules: {', '.join(_mod_handlers) or '—'}")

    watcher = asyncio.create_task(_watcher())

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass

    try:
        await stop.wait()
    finally:
        watcher.cancel()
        try:
            await watcher
        except asyncio.CancelledError:
            pass
        for name in list(_mod_handlers):
            await _unload(name)
        await app.stop()


if __name__ == "__main__":
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        pass
