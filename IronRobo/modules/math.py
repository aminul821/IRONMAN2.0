# Math commands, solved locally with SymPy (the newton.now.sh API is gone).
import re

import sympy
from IronRobo import dispatcher
from IronRobo.modules.disable import DisableAbleCommandHandler
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)
from telegram import Update
from telegram.ext import CallbackContext

TRANSFORMS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)
MAX_INPUT = 200
x = sympy.Symbol("x")


def _expr(text):
    text = text.replace("(over)", "/").strip()
    if not text:
        raise ValueError("empty expression")
    if len(text) > MAX_INPUT:
        raise ValueError("expression too long")
    return parse_expr(text, transformations=TRANSFORMS, local_dict={"x": x})


def _split(text, seps="|l"):
    """Split newton style "c|f(x)" / "clf(x)" input."""
    match = re.match(r"^\s*([^|l]+?)\s*[%s]\s*(.+)$" % re.escape(seps), text)
    if not match:
        raise ValueError("bad format")
    return match.group(1), match.group(2)


def _fmt(value):
    if isinstance(value, (list, tuple, set)):
        return ", ".join(_fmt(v) for v in value) or "No solutions"
    if isinstance(value, sympy.Basic):
        value = sympy.nsimplify(value) if value.is_Float else value
        text = str(value).replace("**", "^")
        if value.is_number and not value.is_Integer and not value.is_Rational:
            text += f" ≈ {sympy.N(value, 10)}"
        return text
    return str(value)


def _simplify(t):
    return sympy.simplify(_expr(t))


def _factor(t):
    return sympy.factor(_expr(t))


def _derive(t):
    return sympy.diff(_expr(t), x)


def _integrate(t):
    return f"{_fmt(sympy.integrate(_expr(t), x))} + C"


def _zeroes(t):
    return sympy.solve(_expr(t), x)


def _tangent(t):
    point, func = _split(t)
    f = _expr(func)
    c = _expr(point)
    slope = sympy.diff(f, x).subs(x, c)
    return sympy.expand(slope * (x - c) + f.subs(x, c))


def _area(t):
    bounds, func = _split(t)
    start, end = bounds.split(":", 1)
    return sympy.integrate(_expr(func), (x, _expr(start), _expr(end)))


def _log(t):
    if "l" in t or "|" in t:
        base, value = _split(t)
        return sympy.log(_expr(value), _expr(base))
    return sympy.log(_expr(t))


SOLVERS = {
    "math": _simplify,
    "factor": _factor,
    "derive": _derive,
    "integrate": _integrate,
    "zeroes": _zeroes,
    "tangent": _tangent,
    "area": _area,
    "cos": lambda t: sympy.cos(_expr(t)),
    "sin": lambda t: sympy.sin(_expr(t)),
    "tan": lambda t: sympy.tan(_expr(t)),
    "arccos": lambda t: sympy.acos(_expr(t)),
    "arcsin": lambda t: sympy.asin(_expr(t)),
    "arctan": lambda t: sympy.atan(_expr(t)),
    "abs": lambda t: sympy.Abs(_expr(t)),
    "log": _log,
}


def solve(update: Update, context: CallbackContext):
    message = update.effective_message
    command = message.text.split(None, 1)[0][1:].split("@")[0].lower()
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        message.reply_text(f"Give me something to calculate, eg: `/{command} x^2+2x`", parse_mode="markdown")
        return
    try:
        result = SOLVERS[command](parts[1])
        message.reply_text(_fmt(result))
    except Exception:
        message.reply_text("I couldn't solve that, check the format in /help.")


__mod_name__ = "Math"

MATH_HANDLERS = [
    DisableAbleCommandHandler(cmd, solve, run_async=True) for cmd in SOLVERS
]
for handler in MATH_HANDLERS:
    dispatcher.add_handler(handler)

__command_list__ = list(SOLVERS)
__handlers__ = MATH_HANDLERS
