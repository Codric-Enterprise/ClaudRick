"""Accord's syntax: controlled English, one sentence form per construct, read and written back."""

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
    r"\s*(?:(?P<num>\d+\.\d+|\d+)|(?P<str>\"[^\"\\]*\")|(?P<word>[A-Za-z_]\w*)|(?P<p>[,:.()]))"
)
RESERVED = {
    "is", "of", "and", "plus", "minus", "times", "divided", "by", "the", "negative",
    "greater", "less", "than", "at", "least", "most", "equal", "to", "not", "true", "false",
    "list", "empty", "length", "first", "rest", "trusted",
}  # fmt: skip
BUILTINS = {"length": "len", "first": "head", "rest": "tail"}
COMPARE = [
    (("not", "equal", "to"), "!="),
    (("greater", "than"), ">"),
    (("less", "than"), "<"),
    (("at", "least"), ">="),
    (("at", "most"), "<="),
    (("equal", "to"), "=="),
]


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
        elif m["word"]:
            tokens.append(("word", m["word"]))
        else:
            tokens.append(("p", m["p"]))
    return tokens


class Sentence:
    def __init__(self, number: int, indent: int, tokens: list):
        self.number, self.indent, self.tokens, self.i = number, indent, tokens, 0

    def peek(self, offset: int = 0):
        j = self.i + offset
        return self.tokens[j] if j < len(self.tokens) else ("end", None)

    def is_word(self, *words: str, offset: int = 0) -> bool:
        for k, w in enumerate(words):
            kind, value = self.peek(offset + k)
            if kind != "word" or value.lower() != w:
                return False
        return True

    def word(self, *words: str):
        for w in words:
            if not self.is_word(w):
                raise AccordError(self.number, f"expected {w!r}, found {self.peek()[1]!r}")
            self.i += 1

    def punct(self, p: str):
        if self.peek() != ("p", p):
            raise AccordError(self.number, f"expected {p!r}, found {self.peek()[1]!r}")
        self.i += 1

    def name(self) -> str:
        kind, value = self.peek()
        if kind != "word" or value.lower() in RESERVED:
            raise AccordError(self.number, f"expected a name, found {value!r}")
        self.i += 1
        return value

    def whole(self) -> int:
        kind, value = self.peek()
        if kind != "num" or not isinstance(value, int):
            raise AccordError(self.number, f"expected a whole number, found {value!r}")
        self.i += 1
        return value

    def article(self):
        if self.is_word("a") or self.is_word("an"):
            self.i += 1
        else:
            raise AccordError(self.number, f"expected 'a' or 'an', found {self.peek()[1]!r}")

    def end(self, p: str = "."):
        self.punct(p)
        if self.i != len(self.tokens):
            raise AccordError(self.number, f"unexpected {self.peek()[1]!r} after the sentence")


def split(source: str) -> list[Sentence]:
    out = []
    for n, raw in enumerate(source.splitlines(), 1):
        tokens = lex(raw, n)
        if not tokens:
            continue
        lead = raw[: len(raw) - len(raw.lstrip())]
        if "\t" in lead:
            raise AccordError(n, "indent with spaces, not tabs")
        out.append(Sentence(n, len(lead), tokens))
    return out


def parse(source: str) -> Function:
    """One function. A source with several is a program: use `program`."""
    functions = program(source)
    if len(functions) != 1:
        raise AccordError(1, f"expected one function, found {len(functions)}: use program()")
    return functions[0]


def program(source: str) -> tuple[Function, ...]:
    """Every function in a source, in order. Each starts at a 'To ...:' header at column 0."""
    sentences = split(source)
    if not sentences:
        raise AccordError(1, "empty program")
    if sentences[0].indent or not sentences[0].is_word("to"):
        raise AccordError(sentences[0].number, "a program starts with 'To ...:' at column 0")
    groups: list[list[Sentence]] = []
    for s in sentences:
        if s.indent == 0 and s.is_word("to"):
            groups.append([])
        groups[-1].append(s)
    return tuple(_function(group) for group in groups)


def _function(sentences: list[Sentence]) -> Function:
    head = sentences[0]
    if head.indent:
        raise AccordError(head.number, "'To ...' must start at column 0")
    head.word("to")
    fn = head.name()
    names = []
    if head.is_word("given"):
        head.word("given")
        names.append(head.name())
        while head.peek() == ("p", ",") and not head.is_word("answering", offset=1):
            head.punct(",")
            names.append(head.name())
        if head.is_word("and"):
            head.word("and")
            names.append(head.name())
    head.punct(",")
    head.word("answering")
    head.article()
    returns = type_name(head)
    head.end(":")

    body = [s for s in sentences[1:] if s.indent > 0]
    checks = [s for s in sentences[1:] if s.indent == 0]
    if checks and body and checks[0].number < body[-1].number:
        raise AccordError(checks[0].number, "checks go after the body")
    if not body:
        raise AccordError(head.number, "a function needs a body")
    indent = body[0].indent

    params = []
    for pname in names:
        if not body or body[0].indent != indent:
            raise AccordError(head.number, f"R1: {pname} is never declared")
        s = body.pop(0)
        declared = s.name()
        if declared != pname:
            raise AccordError(s.number, f"declare {pname} here, not {declared}")
        s.word("is")
        s.article()
        kind = type_name(s)
        if s.peek() == ("p", "."):
            raise AccordError(s.number, f"R1: {pname} says nothing about how far it is trusted")
        s.punct(",")
        trust = trusted(s)
        s.end()
        params.append(Param(pname, kind, trust))

    if not body:
        raise AccordError(head.number, "R5: say 'It never repeats.' or 'It shrinks by N.'")
    s = body.pop(0)
    s.word("it")
    if s.is_word("never"):
        s.word("never", "repeats")
        measure = None
    elif s.is_word("shrinks"):
        s.word("shrinks", "by")
        measure = s.name()
    else:
        raise AccordError(s.number, "R5: say 'It never repeats.' or 'It shrinks by N.'")
    s.end()

    stmts, rest = block(body, indent)
    if rest:
        raise AccordError(rest[0].number, "unexpected indentation")
    examples = tuple(check_sentence(s, fn) for s in checks)
    return Function(fn, tuple(params), returns, measure, tuple(stmts), examples)


def type_name(s: Sentence) -> str:
    kind, value = s.peek()
    if kind != "word":
        raise AccordError(s.number, f"expected a type, found {value!r}")
    s.i += 1
    if value != "List":
        return value
    if not s.is_word("of"):
        raise AccordError(s.number, "R3: a List needs an element type, as 'a List of Int'")
    s.word("of")
    return f"List[{type_name(s)}]"


def trusted(s: Sentence) -> int:
    s.word("trusted")
    trust = s.whole()
    s.word("of")
    if s.peek() != ("num", 256):
        raise AccordError(s.number, "trust is counted out of 256")
    s.i += 1
    return trust


def block(sentences: list[Sentence], indent: int):
    stmts = []
    while sentences and sentences[0].indent == indent:
        s = sentences.pop(0)
        if s.is_word("make", "sure"):
            s.word("make", "sure")
            subject = s.name()
            s.word("is", "not", "void")
            s.end()
            stmts.append(Require("not_void", subject))
        elif s.is_word("let"):
            s.word("let")
            name = s.name()
            s.word("be")
            s.article()
            kind = type_name(s)
            if s.peek() != ("p", ","):
                raise AccordError(s.number, f"R1: {name} says nothing about how far it is trusted")
            s.punct(",")
            trust = trusted(s)
            s.punct(",")
            s.word("equal", "to")
            value = expr(s)
            s.end()
            stmts.append(Let(name, kind, trust, value))
        elif s.is_word("answer"):
            s.word("answer")
            value = expr(s)
            s.end()
            stmts.append(Return(value))
        elif s.is_word("if"):
            s.word("if")
            cond = expr(s)
            s.end(":")
            then, sentences = nested(sentences, indent, s)
            if (
                not sentences
                or sentences[0].indent != indent
                or not sentences[0].is_word("otherwise")
            ):
                raise AccordError(s.number, "R5: an If needs an Otherwise; every path must answer")
            other = sentences.pop(0)
            other.word("otherwise")
            other.end(":")
            orelse, sentences = nested(sentences, indent, other)
            stmts.append(If(cond, tuple(then), tuple(orelse)))
        else:
            raise AccordError(s.number, f"cannot start a sentence with {s.peek()[1]!r}")
    return stmts, sentences


def nested(sentences: list[Sentence], indent: int, owner: Sentence):
    if not sentences or sentences[0].indent <= indent:
        raise AccordError(owner.number, "expected an indented block")
    stmts, sentences = block(sentences, sentences[0].indent)
    if sentences and sentences[0].indent > indent:
        raise AccordError(sentences[0].number, "inconsistent indentation")
    return stmts, sentences


def expr(s: Sentence):
    left = additive(s)
    if s.is_word("is"):
        s.word("is")
        for words, op in COMPARE:
            if s.is_word(*words):
                s.word(*words)
                return Bin(op, left, additive(s))
        raise AccordError(s.number, f"unknown comparison at {s.peek()[1]!r}")
    return left


def additive(s: Sentence):
    left = multiplicative(s)
    while s.is_word("plus") or s.is_word("minus"):
        op = "+" if s.is_word("plus") else "-"
        s.i += 1
        left = Bin(op, left, multiplicative(s))
    return left


def multiplicative(s: Sentence):
    left = unary(s)
    while s.is_word("times") or s.is_word("divided", "by"):
        if s.is_word("times"):
            s.word("times")
            op = "*"
        else:
            s.word("divided", "by")
            op = "/"
        left = Bin(op, left, unary(s))
    return left


def unary(s: Sentence):
    if s.is_word("negative"):
        s.word("negative")
        inner = unary(s)
        if isinstance(inner, Lit) and not isinstance(inner.value, (str, bool)):
            return Lit(-inner.value)
        return Bin("-", Lit(0), inner)
    return atom(s)


def atom(s: Sentence):
    kind, value = s.peek()
    if kind in ("num", "str"):
        s.i += 1
        return Lit(value)
    if s.is_word("true") or s.is_word("false"):
        s.i += 1
        return Lit(value.lower() == "true")
    if kind == "p" and value == "(":
        s.punct("(")
        inner = expr(s)
        s.punct(")")
        return inner
    if s.is_word("the"):
        s.word("the")
    if s.is_word("empty", "list"):
        s.word("empty", "list")
        return ListLit(())
    if s.is_word("list", "of"):
        s.word("list", "of")
        items = [atom(s)]
        while s.peek() == ("p", ",") and not s.is_word("trusted", offset=1):
            s.punct(",")
            if s.is_word("and"):
                raise AccordError(s.number, "no comma before a list's final 'and'")
            items.append(atom(s))
        if s.is_word("and"):
            s.word("and")
            items.append(atom(s))
        return ListLit(tuple(items))
    for word, builtin in BUILTINS.items():
        if s.is_word(word, "of"):
            s.word(word, "of")
            return Call(builtin, (atom(s),))
    name = s.name()
    if s.is_word("of"):
        s.word("of")
        args = [atom(s)]
        while s.is_word("and"):
            s.word("and")
            args.append(atom(s))
        return Call(name, tuple(args))
    return Name(name)


def check_sentence(s: Sentence, fn: str) -> Example:
    s.word("check")
    s.punct(":")
    called = s.name()
    if called != fn:
        raise AccordError(s.number, f"check calls {called!r}, the function is {fn!r}")
    args = []
    if s.is_word("of"):
        s.word("of")
        args.append(literal(s))
        while s.is_word("and"):
            s.word("and")
            args.append(literal(s))
    s.word("gives")
    value = literal(s)
    s.punct(",")
    s.word("trusted")
    trust = s.whole()
    s.end()
    return Example(tuple(args), value, trust)


def literal(s: Sentence):
    return _value(s, unary(s))


def _value(s: Sentence, node):
    if isinstance(node, Lit):
        return node.value
    if isinstance(node, ListLit):
        return tuple(_value(s, item) for item in node.items)
    raise AccordError(s.number, "check values must be literals")


# ── speaking the language back: every message a person reads is written in it ─

WORDS = {op: " ".join(words) for words, op in COMPARE}
ARITHMETIC = {"+": "plus", "-": "minus", "*": "times", "/": "divided by"}
SPOKEN = {builtin: word for word, builtin in BUILTINS.items()}


def render(e) -> str:
    """An expression, in the words `parse` reads. parse(render(e)) gives e back."""
    if isinstance(e, Lit):
        return render_value(e.value)
    if isinstance(e, Name):
        return e.id
    if isinstance(e, ListLit):
        if not e.items:
            return "the empty list"
        items = [_operand(i) for i in e.items]
        if len(items) == 1:
            return f"the list of {items[0]}"
        return f"the list of {', '.join(items[:-1])} and {items[-1]}"
    if isinstance(e, Call):
        if e.fn in SPOKEN:
            return f"the {SPOKEN[e.fn]} of {_operand(e.args[0])}"
        return f"{e.fn} of " + " and ".join(_operand(a, in_call=True) for a in e.args)
    if isinstance(e, Bin):
        if e.op in WORDS:
            return f"{_operand(e.left)} is {WORDS[e.op]} {_operand(e.right)}"
        return f"{_operand(e.left)} {ARITHMETIC[e.op]} {_operand(e.right)}"
    raise TypeError(f"cannot render {e!r}")


def _operand(e, in_call: bool = False) -> str:
    wrap = isinstance(e, Bin) or (in_call and isinstance(e, (ListLit, Call)))
    wrap = wrap or (isinstance(e, Lit) and _num(e.value) and e.value < 0)
    return f"({render(e)})" if wrap else render(e)


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def render_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return f'"{v}"'
    if isinstance(v, tuple):
        return render(ListLit(tuple(Lit(x) for x in v)))
    if _num(v) and v < 0:
        return f"negative {-v}"
    return str(v)


def values(text: str) -> tuple:
    """Arguments typed by a person, in the language: `200`, `the list of 1 and 2`, ..."""
    s = Sentence(1, 0, lex(text, 1))
    found = []
    while s.i < len(s.tokens):
        found.append(literal(s))
        if s.i < len(s.tokens):
            s.word("and") if s.is_word("and") else s.punct(",")
    return tuple(found)
