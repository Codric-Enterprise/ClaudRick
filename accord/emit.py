"""Emit: the dense surface. Every trust, type and check is written as a symbol."""

from __future__ import annotations

import re

from core import (
    AccordError,
    Bin,
    Call,
    Example,
    Function,
    If,
    Let,
    ListLit,
    Lit,
    Name,
    Param,
    Require,
    Return,
)

TOKEN = re.compile(
    r"\s*(?:(?P<num>\d+\.\d+|\d+)|(?P<str>\"[^\"\\]*\")|(?P<name>[A-Za-z_]\w*)"
    r"|(?P<op>->|==|!=|<=|>=|[()\[\]:,@<>+\-*/=]))"
)
KEYWORDS = {"def", "measure", "none", "require", "let", "if", "else", "return", "example"}
CMP = ("==", "!=", "<", ">", "<=", ">=")


def lex(text: str, line: int) -> list[tuple[str, object]]:
    tokens, pos = [], 0
    text = text.rstrip()
    while pos < len(text):
        if text[pos:].lstrip().startswith("#"):
            break
        m = TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise AccordError(line, f"cannot read {text[pos : pos + 12]!r}")
        pos = m.end()
        if m["num"]:
            tokens.append(("num", float(m["num"]) if "." in m["num"] else int(m["num"])))
        elif m["str"]:
            tokens.append(("str", m["str"][1:-1]))
        elif m["name"]:
            word = m["name"]
            if word in ("true", "false"):
                tokens.append(("bool", word == "true"))
            else:
                tokens.append(("kw" if word in KEYWORDS else "name", word))
        else:
            tokens.append(("op", m["op"]))
    return tokens


class Line:
    def __init__(self, number: int, indent: int, tokens: list):
        self.number, self.indent, self.tokens, self.i = number, indent, tokens, 0

    def peek(self, offset: int = 0):
        j = self.i + offset
        return self.tokens[j] if j < len(self.tokens) else ("end", None)

    def take(self, kind: str, value=None):
        tok = self.peek()
        if tok[0] != kind or (value is not None and tok[1] != value):
            want = value if value is not None else kind
            raise AccordError(self.number, f"expected {want!r}, found {tok[1]!r}")
        self.i += 1
        return tok[1]

    def at(self, kind: str, value=None) -> bool:
        tok = self.peek()
        return tok[0] == kind and (value is None or tok[1] == value)

    def done(self):
        if self.i != len(self.tokens):
            raise AccordError(self.number, f"unexpected {self.peek()[1]!r}")


def split(source: str) -> list[Line]:
    lines = []
    for n, raw in enumerate(source.splitlines(), 1):
        tokens = lex(raw, n)
        if not tokens:
            continue
        lead = raw[: len(raw) - len(raw.lstrip())]
        if "\t" in lead:
            raise AccordError(n, "indent with spaces, not tabs")
        lines.append(Line(n, len(lead), tokens))
    return lines


def parse(source: str) -> Function:
    lines = split(source)
    if not lines:
        raise AccordError(1, "empty program")
    head = lines[0]
    if head.indent:
        raise AccordError(head.number, "def must start at column 0")
    head.take("kw", "def")
    name = head.take("name")
    head.take("op", "(")
    params = []
    while not head.at("op", ")"):
        params.append(param(head))
        if not head.at("op", ")"):
            head.take("op", ",")
    head.take("op", ")")
    head.take("op", "->")
    returns = type_name(head)
    head.done()

    body_lines = [ln for ln in lines[1:] if ln.indent > 0]
    example_lines = [ln for ln in lines[1:] if ln.indent == 0]
    if not body_lines:
        raise AccordError(head.number, "a function needs a body")
    first = body_lines[0]
    first.take("kw", "measure")
    first.take("op", ":")
    measure = None if first.at("kw", "none") else first.peek()[1]
    first.take("kw", "none") if measure is None else first.take("name")
    first.done()
    body, rest = block(body_lines[1:], first.indent)
    if rest:
        raise AccordError(rest[0].number, "unexpected indentation")
    examples = tuple(example(ln, name) for ln in example_lines)
    if example_lines and body_lines and example_lines[0].number < body_lines[-1].number:
        raise AccordError(example_lines[0].number, "examples go after the body")
    return Function(name, tuple(params), returns, measure, tuple(body), examples)


def type_name(line: Line) -> str:
    kind = line.take("name")
    if kind != "List":
        return kind
    if not line.at("op", "[") or line.peek(1) == ("name", "trust"):
        raise AccordError(line.number, "R3: a List needs an element type, as List[Int]")
    line.take("op", "[")
    inner = type_name(line)
    line.take("op", "]")
    return f"List[{inner}]"


def param(line: Line) -> Param:
    name = line.take("name")
    line.take("op", ":")
    kind = type_name(line)
    if not line.at("op", "["):
        raise AccordError(line.number, f"R1: {name} has no [trust: N]")
    line.take("op", "[")
    line.take("name", "trust")
    line.take("op", ":")
    trust = line.take("num")
    line.take("op", "]")
    return Param(name, kind, trust)


def block(lines: list[Line], indent: int) -> tuple[list, list[Line]]:
    stmts = []
    while lines and lines[0].indent == indent:
        ln = lines.pop(0)
        if ln.at("kw", "require"):
            ln.take("kw", "require")
            ln.take("op", ":")
            pred = ln.take("name")
            ln.take("op", "(")
            subject = ln.take("name")
            ln.take("op", ")")
            ln.done()
            stmts.append(Require(pred, subject))
        elif ln.at("kw", "let"):
            ln.take("kw", "let")
            name = ln.take("name")
            ln.take("op", ":")
            kind = type_name(ln)
            if not ln.at("op", "["):
                raise AccordError(ln.number, f"R1: {name} has no [trust: N]")
            ln.take("op", "[")
            ln.take("name", "trust")
            ln.take("op", ":")
            trust = ln.take("num")
            ln.take("op", "]")
            ln.take("op", "=")
            stmts.append(Let(name, kind, trust, expr(ln)))
            ln.done()
        elif ln.at("kw", "return"):
            ln.take("kw", "return")
            stmts.append(Return(expr(ln)))
            ln.done()
        elif ln.at("kw", "if"):
            ln.take("kw", "if")
            cond = expr(ln)
            ln.take("op", ":")
            ln.done()
            then, lines = nested(lines, indent, ln)
            if not lines or lines[0].indent != indent or not lines[0].at("kw", "else"):
                raise AccordError(ln.number, "R5: an if needs an else; every path must answer")
            other = lines.pop(0)
            other.take("kw", "else")
            other.take("op", ":")
            other.done()
            orelse, lines = nested(lines, indent, other)
            stmts.append(If(cond, tuple(then), tuple(orelse)))
        else:
            raise AccordError(ln.number, f"cannot start a statement with {ln.peek()[1]!r}")
    return stmts, lines


def nested(lines: list[Line], indent: int, owner: Line):
    if not lines or lines[0].indent <= indent:
        raise AccordError(owner.number, "expected an indented block")
    inner = lines[0].indent
    stmts, lines = block(lines, inner)
    if lines and lines[0].indent > indent:
        raise AccordError(lines[0].number, "inconsistent indentation")
    return stmts, lines


def expr(line: Line):
    left = additive(line)
    if line.peek()[0] == "op" and line.peek()[1] in CMP:
        op = line.take("op")
        left = Bin(op, left, additive(line))
    return left


def additive(line: Line):
    left = multiplicative(line)
    while line.peek() in (("op", "+"), ("op", "-")):
        left = Bin(line.take("op"), left, multiplicative(line))
    return left


def multiplicative(line: Line):
    left = unary(line)
    while line.peek() in (("op", "*"), ("op", "/")):
        left = Bin(line.take("op"), left, unary(line))
    return left


def unary(line: Line):
    if line.at("op", "-"):
        line.take("op", "-")
        inner = unary(line)
        if isinstance(inner, Lit) and not isinstance(inner.value, (str, bool)):
            return Lit(-inner.value)
        return Bin("-", Lit(0), inner)
    return atom(line)


def atom(line: Line):
    kind, value = line.peek()
    if kind in ("num", "str", "bool"):
        line.i += 1
        return Lit(value)
    if kind == "op" and value == "(":
        line.take("op", "(")
        inner = expr(line)
        line.take("op", ")")
        return inner
    if kind == "op" and value == "[":
        line.take("op", "[")
        items = []
        while not line.at("op", "]"):
            items.append(expr(line))
            if line.at("op", ","):
                line.take("op", ",")
                if line.at("op", "]"):
                    raise AccordError(line.number, "a list takes no trailing comma")
            elif not line.at("op", "]"):
                raise AccordError(line.number, f"expected ',' or ']', found {line.peek()[1]!r}")
        line.take("op", "]")
        return ListLit(tuple(items))
    if kind == "name":
        line.i += 1
        if line.at("op", "("):
            line.take("op", "(")
            args = []
            while not line.at("op", ")"):
                args.append(expr(line))
                if not line.at("op", ")"):
                    line.take("op", ",")
            line.take("op", ")")
            return Call(value, tuple(args))
        return Name(value)
    raise AccordError(line.number, f"expected a value, found {value!r}")


def example(line: Line, fn: str) -> Example:
    line.take("kw", "example")
    line.take("op", ":")
    called = line.take("name")
    if called != fn:
        raise AccordError(line.number, f"example calls {called!r}, the function is {fn!r}")
    line.take("op", "(")
    args = []
    while not line.at("op", ")"):
        args.append(literal(line))
        if not line.at("op", ")"):
            line.take("op", ",")
    line.take("op", ")")
    line.take("op", "==")
    value = literal(line)
    line.take("op", "@")
    trust = line.take("num")
    line.done()
    return Example(tuple(args), value, trust)


def literal(line: Line):
    return _value(line, unary(line))


def _value(line: Line, node):
    if isinstance(node, Lit):
        return node.value
    if isinstance(node, ListLit):
        return tuple(_value(line, item) for item in node.items)
    raise AccordError(line.number, "example values must be literals")
