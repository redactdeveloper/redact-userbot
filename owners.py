import json
from pathlib import Path

from pyrogram import filters
from pyrogram.types import Message

_STATE_FILE = Path(__file__).parent / ".owners.json"


def _load() -> set[int]:
    if _STATE_FILE.exists():
        try:
            data = json.loads(_STATE_FILE.read_text())
            return set(int(x) for x in data)
        except Exception:
            pass
    return set()


def _save(owners: set[int]):
    _STATE_FILE.write_text(json.dumps(sorted(owners)))


_owners: set[int] = _load()


def get_owners() -> set[int]:
    return _owners


def add_owner(uid: int):
    _owners.add(uid)
    _save(_owners)


def remove_owner(uid: int):
    _owners.discard(uid)
    _save(_owners)


async def _auth_func(_, __, message: Message):
    fu = message.from_user
    if not fu:
        return False
    if fu.is_self:
        return True
    return fu.id in _owners


auth = filters.create(_auth_func, name="OwnerAuth")
