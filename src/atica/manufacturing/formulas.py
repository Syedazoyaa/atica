"""A small, safe arithmetic formula evaluator.

Formulas are parsed by a hand-written parser into an expression tree and
evaluated with :class:`~decimal.Decimal`. **Nothing is passed to** ``eval`` /
``exec``; only numbers, named variables, ``+ - * / ^``, parentheses and the
functions ``min max abs ceil floor round sqrt`` are understood.

>>> Formula("quantity * per_unit").evaluate(quantity=1000, per_unit="0.5")
Decimal('500')
"""
from __future__ import annotations

import re
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal, DivisionByZero, InvalidOperation
from typing import Any, Dict, List, Set

from ..calculations.numeric import calc_context, clean, to_decimal
from ..exceptions import InvalidQuantityError, ManufacturingError

MAX_FORMULA_LENGTH = 500
MAX_DEPTH = 40
MAX_EXPONENT = 100

_TOKEN = re.compile(
    r"\s*(?:(?P<num>\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)"
    r"|(?P<name>[A-Za-z_][A-Za-z_0-9]*)"
    r"|(?P<op>\*\*|[-+*/^(),]))"
)
_FUNCTIONS = {"min", "max", "abs", "ceil", "floor", "round", "sqrt"}


def _err(message: str, code: str = "INVALID_FORMULA") -> ManufacturingError:
    return ManufacturingError(message, code=code, field="formula")


def _tokenize(text: str) -> List[tuple]:
    tokens = []
    pos = 0
    text = text.rstrip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise _err("Unexpected character %r at position %d." % (text[pos:].lstrip()[:1], pos + 1))
        pos = m.end()
        kind = m.lastgroup
        tokens.append((kind, m.group(kind)))
    return tokens


class Formula:
    """A parsed formula that can be evaluated repeatedly with different variables."""

    def __init__(self, expression: str) -> None:
        if not isinstance(expression, str) or not expression.strip():
            raise _err("A formula must be a non-empty string.")
        if len(expression) > MAX_FORMULA_LENGTH:
            raise _err("Formula is longer than %d characters." % MAX_FORMULA_LENGTH)
        self.expression = expression.strip()
        self._tokens = _tokenize(self.expression)
        self._i = 0
        self._tree = self._parse_expr(0)
        if self._i != len(self._tokens):
            raise _err("Unexpected %r in formula." % (self._tokens[self._i][1],))
        self._tokens = []

    # ---------------------------------------------------------------- parsing
    def _peek(self):
        return self._tokens[self._i] if self._i < len(self._tokens) else (None, None)

    def _next(self):
        tok = self._peek()
        self._i += 1
        return tok

    def _accept(self, *ops):
        kind, val = self._peek()
        if kind == "op" and val in ops:
            self._i += 1
            return val
        return None

    def _parse_expr(self, depth):
        if depth > MAX_DEPTH:
            raise _err("Formula is nested too deeply.")
        node = self._parse_term(depth)
        while True:
            op = self._accept("+", "-")
            if not op:
                return node
            node = ("bin", op, node, self._parse_term(depth))

    def _parse_term(self, depth):
        node = self._parse_unary(depth)
        while True:
            op = self._accept("*", "/")
            if not op:
                return node
            node = ("bin", op, node, self._parse_unary(depth))

    def _parse_unary(self, depth):
        if depth > MAX_DEPTH:
            raise _err("Formula is nested too deeply.")
        op = self._accept("+", "-")
        if op:
            inner = self._parse_unary(depth + 1)
            return ("neg", inner) if op == "-" else inner
        return self._parse_power(depth)

    def _parse_power(self, depth):
        # -2^2 == -(2^2); the exponent may itself be signed (2^-1) and is right-associative.
        base = self._parse_atom(depth)
        if self._accept("^", "**"):
            return ("bin", "^", base, self._parse_unary(depth + 1))
        return base

    def _parse_atom(self, depth):
        kind, val = self._next()
        if kind == "num":
            return ("num", Decimal(val))
        if kind == "name":
            if self._accept("("):
                if val not in _FUNCTIONS:
                    raise _err("Unknown function %r. Allowed: %s." % (val, ", ".join(sorted(_FUNCTIONS))), "UNKNOWN_FUNCTION")
                args = []
                if not self._accept(")"):
                    args.append(self._parse_expr(depth + 1))
                    while self._accept(","):
                        args.append(self._parse_expr(depth + 1))
                    if not self._accept(")"):
                        raise _err("Missing ')' after arguments of %s()." % val)
                return ("call", val, args)
            return ("var", val)
        if kind == "op" and val == "(":
            node = self._parse_expr(depth + 1)
            if not self._accept(")"):
                raise _err("Missing closing ')'.")
            return node
        raise _err("Unexpected end of formula." if kind is None else "Unexpected %r in formula." % (val,))

    # ------------------------------------------------------------- inspection
    @property
    def variables(self) -> Set[str]:
        names: Set[str] = set()

        def walk(node):
            if node[0] == "var":
                names.add(node[1])
            elif node[0] == "neg":
                walk(node[1])
            elif node[0] == "bin":
                walk(node[2]); walk(node[3])
            elif node[0] == "call":
                for a in node[2]:
                    walk(a)

        walk(self._tree)
        return names

    # ------------------------------------------------------------- evaluation
    def evaluate(self, variables: Dict[str, Any] = None, **kwargs: Any) -> Decimal:
        values: Dict[str, Decimal] = {}
        merged = dict(variables or {}, **kwargs)
        for name in self.variables:
            if name not in merged:
                raise _err("Formula uses undefined variable %r." % name, "UNKNOWN_VARIABLE")
            try:
                values[name] = to_decimal(merged[name], field=name)
            except InvalidQuantityError as exc:
                raise _err("Variable %r: %s" % (name, exc.message), "INVALID_NUMBER") from exc
        try:
            with calc_context():
                return clean(self._eval(self._tree, values))
        except (DivisionByZero, ZeroDivisionError):
            raise _err("Division by zero in formula.", "DIVISION_BY_ZERO") from None
        except InvalidOperation:
            raise _err("Formula produced an invalid result.", "INVALID_RESULT") from None

    def _eval(self, node, values):
        kind = node[0]
        if kind == "num":
            return node[1]
        if kind == "var":
            return values[node[1]]
        if kind == "neg":
            return -self._eval(node[1], values)
        if kind == "bin":
            a, b = self._eval(node[2], values), self._eval(node[3], values)
            op = node[1]
            if op == "+":
                return a + b
            if op == "-":
                return a - b
            if op == "*":
                return a * b
            if op == "/":
                if b == 0:
                    raise ZeroDivisionError
                return a / b
            if b != b.to_integral_value() or abs(b) > MAX_EXPONENT:
                raise _err("Exponent must be a whole number between -%d and %d." % (MAX_EXPONENT, MAX_EXPONENT), "INVALID_EXPONENT")
            if a == 0 and b < 0:
                raise ZeroDivisionError
            return a ** int(b)
        name, args = node[1], [self._eval(a, values) for a in node[2]]
        if name in ("min", "max"):
            if not args:
                raise _err("%s() needs at least one argument." % name)
            return min(args) if name == "min" else max(args)
        if name == "round":
            if len(args) not in (1, 2):
                raise _err("round() takes 1 or 2 arguments.")
            places = int(args[1]) if len(args) == 2 else 0
            return args[0].quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
        if len(args) != 1:
            raise _err("%s() takes exactly 1 argument." % name)
        x = args[0]
        if name == "abs":
            return abs(x)
        if name == "ceil":
            return x.to_integral_value(rounding=ROUND_CEILING)
        if name == "floor":
            return x.to_integral_value(rounding=ROUND_FLOOR)
        if x < 0:
            raise _err("sqrt() of a negative number.", "INVALID_RESULT")
        return x.sqrt()


def evaluate_formula(expression: str, variables: Dict[str, Any] = None, **kwargs: Any) -> Decimal:
    """Parse and evaluate ``expression`` in one step."""
    return Formula(expression).evaluate(variables, **kwargs)
