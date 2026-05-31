import ast
import html
import math
import operator as op

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

import owners
from config import PREFIXES

HELP = {
    "description": "Безопасный калькулятор",
    "commands": {".calc <expr>": "вычислить (math функции доступны)"},
}

_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.FloorDiv: op.floordiv,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}

_NAMES = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "inf": math.inf,
}

_FUNCS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "exp": math.exp,
    "floor": math.floor,
    "ceil": math.ceil,
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
}


def _ev(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("только числа")
    if isinstance(node, ast.BinOp):
        fn = _OPS.get(type(node.op))
        if not fn:
            raise ValueError("оператор не поддерживается")
        return fn(_ev(node.left), _ev(node.right))
    if isinstance(node, ast.UnaryOp):
        fn = _OPS.get(type(node.op))
        if not fn:
            raise ValueError("оператор не поддерживается")
        return fn(_ev(node.operand))
    if isinstance(node, ast.Name):
        if node.id in _NAMES:
            return _NAMES[node.id]
        raise ValueError(f"unknown name: {node.id}")
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("bad call")
        fn = _FUNCS.get(node.func.id)
        if fn is None:
            raise ValueError(f"unknown function: {node.func.id}")
        return fn(*[_ev(a) for a in node.args])
    raise ValueError(f"unsupported: {type(node).__name__}")


def safe_eval(expr: str):
    tree = ast.parse(expr, mode="eval")
    return _ev(tree.body)


async def calc_handler(client: Client, message: Message):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.edit_text(
            "Использование: <code>.calc выражение</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    expr = parts[1].strip()
    try:
        result = safe_eval(expr)
    except Exception as e:
        await message.edit_text(
            f"<b>Ошибка:</b> <code>{html.escape(str(e))}</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    await message.edit_text(
        f"<code>{html.escape(expr)}</code>\n= <b>{result}</b>",
        parse_mode=ParseMode.HTML,
    )


def register(app: Client):
    app.add_handler(
        MessageHandler(
            calc_handler,
            owners.auth & filters.command("calc", prefixes=PREFIXES),
        )
    )
