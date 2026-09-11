#!/usr/bin/env python3
"""
syntax.py — EZR / Tapestry, stages 1 through 3

    1. Lexer      source  -> [Token]
    2. Parser     [Token] -> AST
    3. Semantic   AST     -> AST, resolved and typed
    4. Execution  handled by eval_ast below and by abstract.py

EZR previously jumped straight to stage 4 and walked strings. That
worked, and it cost three things that only an AST can give back:

  - ultracode measured characters instead of structure, so `n*1` and
    `n` looked like different amounts of program
  - transpilation was impossible; you cannot emit Rust from a regex
  - nothing could answer "is this spec even expressible in my grammar",
    which is the exact gap the notebook batch exposed at cell 7

EVERY STAGE RETURNS E<T>. A lexing error is not an exception, it is a Z
carrying a defect class and a source position. Evaluation being total is
a property of the whole pipeline or it is not a property at all.

Codric Enterprise · Ricky (Dreid) · 2026
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple

from ezr import (
    E, State, Defect, e_z, e_val,
    E_CERTAIN, E_ZERO, E_INTAKE, E_EXECUTE_FLOOR,
)


# ═════════════════════════════════════════════
# 1. LEXER
# ═════════════════════════════════════════════

class T(Enum):
    NUM = auto(); STR = auto(); NAME = auto(); KW = auto()
    OP = auto(); CMP = auto(); LPAR = auto(); RPAR = auto()
    LBRACK = auto(); RBRACK = auto()
    COMMA = auto(); EQ = auto(); EOF = auto()


#: The words the grammar actually reaches, and no others. The
#: incumbent reserved nineteen, thirteen of which appeared in no rule
#: and so reserved names against a syntax that did not exist -- see
#: CORE.md 2.2. `show` is deliberately not here: it is a builtin
#: function, so it has to lex as a NAME to be callable.
KEYWORDS = {"def", "else", "false", "if", "in", "let", "then", "true"}

SPEC = [
    (T.NUM,   r'\d+\.\d+|\d+'),
    # Closed form first, then the unclosed one. Without the second
    # alternative a lone opening quote never matches as a string at all,
    # it falls through to "unexpected character", and the guard below can
    # never fire. The forge settled that an unclosed string is
    # `unbounded`; this is what lets that answer reach the runner.
    (T.STR,   r'"[^"\n]*"|"[^"\n]*'),
    (T.CMP,   r'<=|>=|==|!='),
    (T.EQ,    r'='),
    (T.OP,    r'[-+*/<>]'),
    (T.LPAR,  r'\('),
    (T.RPAR,  r'\)'),
    (T.LBRACK, r'\['),
    (T.RBRACK, r'\]'),
    (T.COMMA, r','),
    (T.NAME,  r'[A-Za-z_]\w*'),
]
MASTER = re.compile("|".join(f"(?P<{t.name}>{p})" for t, p in SPEC))


@dataclass
class Token:
    kind: T
    text: str
    pos: int
    line: int = 1

    def __repr__(self) -> str:
        return f"{self.kind.name}({self.text})"


def lex(src: str) -> Tuple[List[Token], Optional[E]]:
    """Source into tokens. Returns (tokens, error-or-None)."""
    toks: List[Token] = []
    i, line = 0, 1
    n = len(src)

    while i < n:
        ch = src[i]
        if ch == "\n":
            line += 1; i += 1; continue
        if ch in " \t\r":
            i += 1; continue
        if ch == "#":
            while i < n and src[i] != "\n":
                i += 1
            continue

        m = MASTER.match(src, i)
        if not m:
            return toks, e_z("lex",
                             f"unexpected character {ch!r} at {i} (line {line})",
                             Defect.MISBOUND)

        kind = T[m.lastgroup]
        text = m.group()
        if kind is T.NAME and text in KEYWORDS:
            kind = T.KW
        # A bare `"` both starts and ends with a quote, so the length
        # has to be checked too or the one-character case slips through.
        if kind is T.STR and (len(text) < 2 or not text.endswith('"')):
            return toks, e_z("lex", f"unterminated string at line {line}",
                             Defect.UNBOUNDED)

        toks.append(Token(kind, text, i, line))
        i = m.end()

    toks.append(Token(T.EOF, "", i, line))
    return toks, None


# ═════════════════════════════════════════════
# 2. AST
# ═════════════════════════════════════════════

class Node:
    """Base. Every node knows its own size and shape."""

    def size(self) -> int:
        """Structural size. This is what ultracode should have been
        measuring all along: nodes, not characters."""
        return 1 + sum(c.size() for c in self.children())

    def depth(self) -> int:
        cs = self.children()
        return 1 + (max(c.depth() for c in cs) if cs else 0)

    def children(self) -> List["Node"]:
        return []

    def shape(self) -> str:
        """Structure with the constants erased. Two programs with the
        same shape are the same idea with different numbers in it."""
        return type(self).__name__


@dataclass
class Num(Node):
    value: float
    def shape(self) -> str: return "Num"
    def __str__(self) -> str:
        return str(int(self.value)) if self.value == int(self.value) \
            else str(self.value)


@dataclass
class Str(Node):
    value: str
    def __str__(self) -> str: return f'"{self.value}"'


@dataclass
class Bool(Node):
    value: bool
    def __str__(self) -> str: return "true" if self.value else "false"


@dataclass
class Var(Node):
    name: str
    def shape(self) -> str: return "Var"
    def __str__(self) -> str: return self.name


@dataclass
class BinOp(Node):
    op: str
    left: Node
    right: Node
    def children(self) -> List[Node]: return [self.left, self.right]
    def shape(self) -> str:
        return f"({self.left.shape()} {self.op} {self.right.shape()})"
    def __str__(self) -> str: return f"{self.left} {self.op} {self.right}"


@dataclass
class If(Node):
    cond: Node
    then: Node
    els: Node
    def children(self) -> List[Node]: return [self.cond, self.then, self.els]
    def shape(self) -> str:
        return f"if {self.cond.shape()} then {self.then.shape()} " \
               f"else {self.els.shape()}"
    def __str__(self) -> str:
        return f"if {self.cond} then {self.then} else {self.els}"


@dataclass
class Call(Node):
    name: str
    args: List[Node] = field(default_factory=list)
    def children(self) -> List[Node]: return list(self.args)
    def shape(self) -> str:
        return f"{self.name}({', '.join(a.shape() for a in self.args)})"
    def __str__(self) -> str:
        return f"{self.name}({', '.join(str(a) for a in self.args)})"


@dataclass
class Lst(Node):
    """A list literal. Its confidence is the chain rule over its
    elements: no more trusted than the least-trusted thing in it."""
    items: List[Node] = field(default_factory=list)
    def children(self) -> List[Node]: return list(self.items)
    def shape(self) -> str:
        return f"[{', '.join(i.shape() for i in self.items)}]"
    def __str__(self) -> str:
        return "[" + ", ".join(str(i) for i in self.items) + "]"


@dataclass
class Let(Node):
    """`let x = v in body`. A name for a thread that already exists --
    nothing is overwritten, so G9 still holds."""
    name: str
    value: Node
    body: Node
    def children(self) -> List[Node]: return [self.value, self.body]
    def shape(self) -> str:
        return f"let {self.value.shape()} in {self.body.shape()}"
    def __str__(self) -> str:
        return f"let {self.name} = {self.value} in {self.body}"


@dataclass
class FnDef(Node):
    name: str
    params: List[str]
    body: Node
    def children(self) -> List[Node]: return [self.body]
    def __str__(self) -> str:
        return f"def {self.name}({', '.join(self.params)}) = {self.body}"


# ═════════════════════════════════════════════
# 2. PARSER — recursive descent over tokens
# ═════════════════════════════════════════════

@dataclass
class Prog(Node):
    """A whole program: a run of definitions, or a single expression.

    This is the ratified core's `program := definitions | expression`
    (CORE.md 2). There is deliberately no trailing expression after the
    definitions -- that grammar is ambiguous, and the chart parser said
    so: `def f(n) = 1 - 1` would have two derivations, a body of
    `1 - 1` or a body of `1` followed by the expression `- 1`.
    """
    defs: List[FnDef] = field(default_factory=list)
    expr: Optional[Node] = None

    def children(self) -> List[Node]:
        kids: List[Node] = list(self.defs)
        if self.expr is not None:
            kids.append(self.expr)
        return kids

    def __str__(self) -> str:
        parts = [str(d) for d in self.defs]
        if self.expr is not None:
            parts.append(str(self.expr))
        return "\n".join(parts)


def unwrap(node: Node) -> Node:
    """The single node a program contains.

    For callers that want the expression or the definition rather than
    the `Prog` wrapping it. A program with several definitions has no
    single node and is returned as it is.
    """
    if isinstance(node, Prog):
        if node.expr is not None:
            return node.expr
        if len(node.defs) == 1:
            return node.defs[0]
    return node


def definitions(node: Node) -> Dict[str, FnDef]:
    """The function table a program defines, ready for eval_ast."""
    if isinstance(node, Prog):
        return {d.name: d for d in node.defs}
    if isinstance(node, FnDef):
        return {node.name: node}
    return {}


class Parser:
    """Grammar, stated:

        program   := fndef | expr
        fndef     := 'def' NAME '(' params ')' '=' expr
        expr      := ifexpr | compare
        ifexpr    := 'if' expr 'then' expr 'else' expr
        compare   := additive [ CMP additive ]
        additive  := multiply { ('+' | '-') multiply }
        multiply  := atom { ('*' | '/') atom }
        atom      := NUM | STR | 'true' | 'false'
                   | NAME '(' args ')' | NAME | '(' expr ')'

    Left-associative, comparison lowest. This is the whole language;
    anything not derivable here is outside the grammar, and saying so
    precisely is the point of writing it down.
    """

    def __init__(self, toks: List[Token]):
        self.toks = toks
        self.i = 0

    # ── helpers ──
    def peek(self) -> Token: return self.toks[self.i]
    def at(self, kind: T, text: Optional[str] = None) -> bool:
        t = self.peek()
        return t.kind is kind and (text is None or t.text == text)
    def take(self) -> Token:
        t = self.toks[self.i]
        if t.kind is not T.EOF:
            self.i += 1
        return t
    def expect(self, kind: T, text: Optional[str] = None) -> Token:
        if not self.at(kind, text):
            got = self.peek()
            raise ParseError(f"expected {text or kind.name}, "
                             f"found {got.text or 'end of input'} "
                             f"at line {got.line}")
        return self.take()

    # ── grammar ──
    def program(self) -> Node:
        # Both branches must reach the end of the input. The definition
        # branch used to return without checking, so everything after a
        # definition was silently dropped and compile_ezr still
        # reported "ready": `def f(n) = n ) ) )` and
        # `def f(n) = n` followed by a second definition both came back
        # clean, with the tail discarded. Found by layer 7, where all
        # sixteen front ends refuse the same texts.
        # The ratified core takes a run of definitions, not just one.
        # The runtime always held any number of them -- Lambda.globals
        # is a dictionary -- and the grammar simply could not say so,
        # which is the coverage gap CORE.md 2.2 records.
        if self.at(T.KW, "def"):
            defs: List[FnDef] = []
            while self.at(T.KW, "def"):
                defs.append(self.fndef())
            node: Node = Prog(defs=defs)
        else:
            node = Prog(defs=[], expr=self.expr())
        if not self.at(T.EOF):
            t = self.peek()
            raise ParseError(f"unexpected {t.text!r} at line {t.line}")
        return node

    def fndef(self) -> FnDef:
        self.expect(T.KW, "def")
        name = self.expect(T.NAME).text
        self.expect(T.LPAR)
        params: List[str] = []
        if not self.at(T.RPAR):
            params.append(self.expect(T.NAME).text)
            while self.at(T.COMMA):
                self.take()
                params.append(self.expect(T.NAME).text)
        self.expect(T.RPAR)
        self.expect(T.EQ)
        return FnDef(name, params, self.expr())

    def expr(self) -> Node:
        if self.at(T.KW, "let"):
            self.take()
            name = self.expect(T.NAME).text
            self.expect(T.EQ)
            value = self.expr()
            self.expect(T.KW, "in")
            return Let(name, value, self.expr())
        if self.at(T.KW, "if"):
            self.take()
            cond = self.expr()
            self.expect(T.KW, "then")
            then = self.expr()
            self.expect(T.KW, "else")
            return If(cond, then, self.expr())
        return self.compare()

    def compare(self) -> Node:
        left = self.additive()
        if self.at(T.CMP) or (self.at(T.OP) and self.peek().text in "<>"):
            op = self.take().text
            return BinOp(op, left, self.additive())
        return left

    def additive(self) -> Node:
        node = self.multiply()
        while self.at(T.OP) and self.peek().text in "+-":
            op = self.take().text
            node = BinOp(op, node, self.multiply())
        return node

    def multiply(self) -> Node:
        node = self.atom()
        while self.at(T.OP) and self.peek().text in "*/":
            op = self.take().text
            node = BinOp(op, node, self.atom())
        return node

    def atom(self) -> Node:
        t = self.peek()
        if t.kind is T.NUM:
            self.take(); return Num(float(t.text))
        if t.kind is T.STR:
            self.take(); return Str(t.text[1:-1])
        if t.kind is T.KW and t.text in ("true", "false"):
            self.take(); return Bool(t.text == "true")
        if t.kind is T.LBRACK:
            self.take()
            items: List[Node] = []
            if not self.at(T.RBRACK):
                items.append(self.expr())
                while self.at(T.COMMA):
                    self.take()
                    items.append(self.expr())
            self.expect(T.RBRACK)
            return Lst(items)
        if t.kind is T.LPAR:
            self.take()
            node = self.expr()
            self.expect(T.RPAR)
            return node
        if t.kind is T.OP and t.text == "-":
            self.take()
            return BinOp("-", Num(0), self.atom())
        if t.kind is T.NAME:
            self.take()
            if self.at(T.LPAR):
                self.take()
                args: List[Node] = []
                if not self.at(T.RPAR):
                    args.append(self.expr())
                    while self.at(T.COMMA):
                        self.take()
                        args.append(self.expr())
                self.expect(T.RPAR)
                return Call(t.text, args)
            return Var(t.text)
        raise ParseError(f"unexpected {t.text or 'end of input'} "
                         f"at line {t.line}")


class ParseError(Exception):
    pass


def parse(src: str) -> Tuple[Optional[Node], Optional[E]]:
    toks, err = lex(src)
    if err:
        return None, err
    try:
        return Parser(toks).program(), None
    except ParseError as exc:
        return None, e_z("parse", str(exc), Defect.UNBOUNDED)


# ═════════════════════════════════════════════
# 3. SEMANTIC ANALYSIS
# ═════════════════════════════════════════════

class Ty(Enum):
    NUM = "num"; TEXT = "text"; BOOL = "bool"; ANY = "any"; ERR = "err"


@dataclass
class Analysis:
    """What the semantic pass learned, before anything ran."""
    ty: Ty = Ty.ANY
    free: Set[str] = field(default_factory=set)
    calls: Set[str] = field(default_factory=set)
    recursive: bool = False
    measure: Optional[str] = None
    size: int = 0
    depth: int = 0
    shape: str = ""
    errors: List[str] = field(default_factory=list)
    per_def: Dict[str, "Analysis"] = field(default_factory=dict)

    @property
    def clean(self) -> bool:
        return not self.errors


class Semantic:
    """Stage 3. Scope resolution, arity checking and type inference,
    all before a single value is computed.

    EZR used to discover an unbound name at evaluation time, wrapped in
    a Z. That is not wrong, but it is late: it means a defect only
    surfaces on the input that reaches it. Catching it here means the
    binding is checked whether or not that branch ever runs.
    """

    NUMERIC_OPS = {"+", "-", "*", "/"}
    COMPARE_OPS = {"<", ">", "<=", ">=", "==", "!="}

    def __init__(self, known_fns: Optional[Dict[str, int]] = None):
        self.fns: Dict[str, int] = dict(known_fns or {})

    def analyse(self, node: Node,
                bound: Optional[Set[str]] = None) -> Analysis:
        a = Analysis()
        bound = set(bound or ())

        if isinstance(node, Prog):
            # Two passes. Every name and arity is registered before any
            # body is walked, so `def f(n) = g(n)` followed by
            # `def g(n) = n` resolves -- a single pass would report g
            # unbound purely because of the order they were written in.
            for d in node.defs:
                self.fns[d.name] = len(d.params)
            for d in node.defs:
                inner = self.analyse(d)
                a.per_def[d.name] = inner
                for msg in inner.errors:
                    tagged = f"in {d.name}: {msg}"
                    if tagged not in a.errors:
                        a.errors.append(tagged)
                a.calls |= inner.calls
            if node.expr is not None:
                inner = self.analyse(node.expr, bound)
                a.ty = inner.ty
                a.calls |= inner.calls
                for msg in inner.errors:
                    if msg not in a.errors:
                        a.errors.append(msg)
            elif len(node.defs) == 1:
                only = a.per_def[node.defs[0].name]
                a.ty, a.recursive, a.measure = only.ty, only.recursive, only.measure
            a.size = node.size()
            a.depth = node.depth()
            a.shape = " ; ".join(d.body.shape() for d in node.defs) \
                if node.defs else (node.expr.shape() if node.expr else "")
            return a

        if isinstance(node, FnDef):
            self.fns[node.name] = len(node.params)
            inner = self.analyse(node.body, set(node.params))
            a = inner
            a.recursive = node.name in inner.calls
            a.free -= set(node.params)
            if a.recursive:
                a.measure = self._measure(node)
            a.size = node.size(); a.depth = node.depth()
            a.shape = node.body.shape()
            for name in sorted(a.free):
                msg = f"unbound name '{name}'"
                if msg not in a.errors:
                    a.errors.append(msg)
            return a

        self._walk(node, bound, a)
        a.size = node.size(); a.depth = node.depth(); a.shape = node.shape()
        for name in sorted(a.free):
            msg = f"unbound name '{name}'"
            if msg not in a.errors:
                a.errors.append(msg)
        return a

    def _walk(self, node: Node, bound: Set[str], a: Analysis) -> Ty:
        if isinstance(node, Num):
            return Ty.NUM
        if isinstance(node, Str):
            return Ty.TEXT
        if isinstance(node, Bool):
            return Ty.BOOL

        if isinstance(node, Var):
            if node.name not in bound:
                a.free.add(node.name)
            return Ty.ANY

        if isinstance(node, BinOp):
            lt = self._walk(node.left, bound, a)
            rt = self._walk(node.right, bound, a)
            if node.op in self.COMPARE_OPS:
                if Ty.TEXT in (lt, rt) and lt != rt:
                    a.errors.append(
                        f"comparing {lt.value} with {rt.value}")
                a.ty = Ty.BOOL
                return Ty.BOOL
            # arithmetic
            for t, side in ((lt, "left"), (rt, "right")):
                if t is Ty.TEXT and node.op != "+":
                    a.errors.append(
                        f"cannot apply '{node.op}' to text on the {side}")
                if t is Ty.BOOL:
                    a.errors.append(
                        f"cannot apply '{node.op}' to a bool on the {side}")
            if node.op == "/" and isinstance(node.right, Num) \
                    and node.right.value == 0:
                a.errors.append("division by a literal zero")
            a.ty = Ty.NUM
            return Ty.NUM

        if isinstance(node, If):
            ct = self._walk(node.cond, bound, a)
            if ct is Ty.TEXT:
                a.errors.append("condition is text, not a truth value")
            tt = self._walk(node.then, bound, a)
            et = self._walk(node.els, bound, a)
            if tt is not Ty.ANY and et is not Ty.ANY and tt != et:
                a.errors.append(
                    f"branches disagree: then is {tt.value}, "
                    f"else is {et.value}")
            a.ty = tt if tt == et else Ty.ANY
            return a.ty

        if isinstance(node, Lst):
            for it in node.items:
                self._walk(it, bound, a)
            return Ty.ANY

        if isinstance(node, Let):
            self._walk(node.value, bound, a)
            return self._walk(node.body, bound | {node.name}, a)

        if isinstance(node, Call):
            a.calls.add(node.name)
            for arg in node.args:
                self._walk(arg, bound, a)
            expected = self.fns.get(node.name)
            if expected is not None and expected != len(node.args):
                a.errors.append(
                    f"{node.name} takes {expected} argument(s), "
                    f"given {len(node.args)}")
            return Ty.ANY

        return Ty.ANY

    @staticmethod
    def _measure(fn: FnDef) -> Optional[str]:
        """A parameter that strictly decreases in every self-call.

        On the AST this is a structural question rather than a regex
        one, so it sees through parentheses and nesting that the string
        version could not.
        """
        calls: List[Call] = []

        def collect(n: Node) -> None:
            if isinstance(n, Call) and n.name == fn.name:
                calls.append(n)
            for c in n.children():
                collect(c)

        collect(fn.body)
        if not calls:
            return None

        for idx, p in enumerate(fn.params):
            good = True
            for call in calls:
                if idx >= len(call.args):
                    good = False; break
                arg = call.args[idx]
                if isinstance(arg, BinOp) and isinstance(arg.left, Var) \
                        and arg.left.name == p and isinstance(arg.right, Num):
                    if arg.op == "-" and arg.right.value > 0:
                        continue
                    if arg.op == "/" and arg.right.value > 1:
                        continue
                good = False
                break
            if good:
                return p
        return None


# ═════════════════════════════════════════════
# 4. EXECUTION over the AST
# ═════════════════════════════════════════════

#: The whole standard library, stated. A list you cannot take apart is
#: not a list, so the three accessors come with the literal; `show` is
#: the only way a program has of being observed from outside.
#: Every one of them obeys the chain rule -- a result is no more
#: trusted than the argument it came from.
BUILTINS = ("show", "len", "head", "tail")


def _builtin(name: str, args: List[E]) -> Optional[E]:
    """A builtin call, or None when the name is not one."""
    if name not in BUILTINS:
        return None

    if name == "show":
        if len(args) != 1:
            return e_z("show", "show takes 1 argument", Defect.MISBOUND)
        a = args[0]
        print(f"{a.value}  @ {a.confidence}/256")
        return a                       # identity, so it composes

    if len(args) != 1:
        return e_z(name, f"{name} takes 1 argument", Defect.MISBOUND)
    a = args[0]
    if not isinstance(a.value, list):
        return e_z(name, f"{name} needs a list, got {a.type_name()}",
                   Defect.MISBOUND)

    if name == "len":
        return e_val("len", len(a.value), a.confidence)
    if not a.value:
        # An empty list has no head and no tail. That is a refusal, not
        # an exception and not a silent empty answer.
        return e_z(name, f"{name} of an empty list", Defect.UNBOUND)
    if name == "head":
        return e_val("head", a.value[0], a.confidence)
    return e_val("tail", a.value[1:], a.confidence)


def eval_ast(node: Node, env: Dict[str, E],
             fns: Dict[str, FnDef], depth: int = 0,
             limit: int = 3) -> E:
    """Stage 4, walking a tree instead of a string.

    Same semantics as abstract.py: chain by min, Z absorbs, a Z
    condition spans both branches, branches are lazy under a known
    condition.
    """
    if isinstance(node, Num):
        v = int(node.value) if node.value == int(node.value) else node.value
        return e_val("lit", v, E_CERTAIN)
    if isinstance(node, Str):
        return e_val("lit", node.value, E_CERTAIN)
    if isinstance(node, Bool):
        return e_val("lit", node.value, E_CERTAIN)

    if isinstance(node, Var):
        v = env.get(node.name)
        return v if v is not None else \
            e_z(node.name, f"{node.name} was never bound", Defect.UNBOUND)

    if isinstance(node, BinOp):
        a = eval_ast(node.left, env, fns, depth, limit)
        if a.is_z:
            return a
        b = eval_ast(node.right, env, fns, depth, limit)
        if b.is_z:
            return b
        conf = min(a.confidence, b.confidence)
        try:
            if node.op == "+":  v = a.value + b.value
            elif node.op == "-": v = a.value - b.value
            elif node.op == "*": v = a.value * b.value
            elif node.op == "/":
                if b.value == 0:
                    return e_z("div", "division by zero", Defect.MISBOUND)
                v = a.value / b.value
            elif node.op == "<":  v = a.value < b.value
            elif node.op == ">":  v = a.value > b.value
            elif node.op == "<=": v = a.value <= b.value
            elif node.op == ">=": v = a.value >= b.value
            elif node.op == "==": v = a.value == b.value
            elif node.op == "!=": v = a.value != b.value
            else:
                return e_z("op", f"unknown operator {node.op}",
                           Defect.MISBOUND)
        except TypeError:
            return e_z("op", f"cannot {node.op} {a.type_name()} "
                             f"with {b.type_name()}", Defect.MISBOUND)
        if isinstance(v, float) and v == int(v):
            v = int(v)
        return e_val("op", v, conf)

    if isinstance(node, If):
        cond = eval_ast(node.cond, env, fns, depth, limit)
        if not cond.is_z:
            taken = node.then if cond.value else node.els
            r = eval_ast(taken, env, fns, depth, limit)
            if r.is_z:
                return r
            return e_val("if", r.value, min(cond.confidence, r.confidence))
        # unknown condition: both arms, then span
        a = eval_ast(node.then, env, fns, depth, limit)
        b = eval_ast(node.els, env, fns, depth, limit)
        if a.is_z or b.is_z:
            return e_z("if", "condition unknown and a branch is Z",
                       Defect.UNBOUND)
        if a.value == b.value:
            return e_val("if", a.value, min(a.confidence, b.confidence))
        from ezr import e_equiv, E_PI_WIDTH_WARN
        if not isinstance(a.value, (int, float)) or \
           not isinstance(b.value, (int, float)):
            return e_z("if", "branches are not spannable", Defect.UNBOUNDED)
        lo, hi = sorted([int(a.value), int(b.value)])
        if hi - lo > E_PI_WIDTH_WARN:
            return e_z("if", f"branches span {hi - lo}, past the pi "
                             f"threshold", Defect.UNBOUNDED)
        r = e_equiv("if", lo, hi)
        r.confidence = min(a.confidence, b.confidence)
        return r

    if isinstance(node, Call):
        fn = fns.get(node.name)
        if fn is None:
            args = [eval_ast(a, env, fns, depth, limit) for a in node.args]
            for a in args:
                if a.is_z:
                    return a
            built = _builtin(node.name, args)
            if built is not None:
                return built
            return e_z(node.name, f"{node.name} was never defined",
                       Defect.UNBOUND)
        if depth > limit:
            return e_z(node.name, f"depth ceiling {limit} exceeded",
                       Defect.UNBOUNDED)
        args = [eval_ast(a, env, fns, depth, limit) for a in node.args]
        for a in args:
            if a.is_z:
                return a
        if len(args) != len(fn.params):
            return e_z(node.name, f"expected {len(fn.params)} argument(s), "
                                  f"got {len(args)}", Defect.MISBOUND)
        local = dict(zip(fn.params, args))
        r = eval_ast(fn.body, local, fns, depth + 1, limit)
        if r.is_z:
            return r
        return e_val(node.name, r.value,
                     min([r.confidence] + [a.confidence for a in args]))

    if isinstance(node, Lst):
        vals, confs = [], []
        for it in node.items:
            r = eval_ast(it, env, fns, depth, limit)
            if r.is_z:
                return r                       # Z absorbs, T1
            vals.append(r.value)
            confs.append(r.confidence)
        # the chain rule, over the elements
        return e_val("list", vals, min(confs) if confs else E_CERTAIN)

    if isinstance(node, Let):
        bound_val = eval_ast(node.value, env, fns, depth, limit)
        if bound_val.is_z:
            return bound_val
        inner = dict(env)
        inner[node.name] = bound_val
        return eval_ast(node.body, inner, fns, depth, limit)

    if isinstance(node, Prog):
        # Register every definition, then evaluate the expression if
        # there is one. A program that is only definitions has defined
        # them and produced nothing, which is Certain and true.
        for d in node.defs:
            fns[d.name] = d
        if node.expr is not None:
            return eval_ast(node.expr, env, fns, depth, limit)
        return e_val("prog", len(node.defs), E_CERTAIN)

    return e_z("eval", f"cannot evaluate {type(node).__name__}",
               Defect.MISBOUND)


# ═════════════════════════════════════════════
# The pipeline, end to end, returning E at every stage
# ═════════════════════════════════════════════

@dataclass
class Compiled:
    src: str
    tokens: List[Token] = field(default_factory=list)
    ast: Optional[Node] = None
    analysis: Optional[Analysis] = None
    error: Optional[E] = None
    stage: str = ""

    @property
    def ok(self) -> bool:
        return self.error is None and (self.analysis is None
                                       or self.analysis.clean)


def compile_ezr(src: str,
                 known_fns: Optional[Dict[str, int]] = None) -> Compiled:
    """1 -> 2 -> 3, stopping at the first stage that refuses."""
    c = Compiled(src=src)

    toks, err = lex(src)
    c.tokens = toks
    if err:
        c.error, c.stage = err, "lex"
        return c

    try:
        c.ast = Parser(toks).program()
    except ParseError as exc:
        c.error, c.stage = e_z("parse", str(exc), Defect.UNBOUNDED), "parse"
        return c

    c.analysis = Semantic(known_fns).analyse(c.ast)
    c.stage = "semantic" if c.analysis.errors else "ready"
    return c


# ═════════════════════════════════════════════
# Grammar coverage — the gap the notebook batch exposed
# ═════════════════════════════════════════════

def shapes_of(nodes: List[Node]) -> Dict[str, int]:
    """How many genuinely distinct structures, ignoring constants.

    Cell 7 of the notebook batch returned three 'independent' candidates
    that were the same formula with different base cases. On strings
    they looked different. On shapes they are one, and one candidate
    cannot corroborate itself.
    """
    counts: Dict[str, int] = {}
    for n in nodes:
        s = n.shape()
        counts[s] = counts.get(s, 0) + 1
    return counts


def skeleton(node: Node) -> str:
    """Shape with comparison operators and constants collapsed.

    `if n < 1 then 1 else ...` and `if n <= 0 then 1 else ...` are the
    same idea with the base case nudged. Counting them as two
    independent solutions was what let a single overfitted formula look
    like a consensus in the notebook batch.
    """
    if isinstance(node, (Num, Str, Bool)):
        return "K"
    if isinstance(node, Var):
        return "V"
    if isinstance(node, BinOp):
        op = "CMP" if node.op in Semantic.COMPARE_OPS else node.op
        return f"({skeleton(node.left)} {op} {skeleton(node.right)})"
    if isinstance(node, If):
        return (f"if {skeleton(node.cond)} then {skeleton(node.then)} "
                f"else {skeleton(node.els)}")
    if isinstance(node, Call):
        return f"CALL({', '.join(skeleton(a) for a in node.args)})"
    if isinstance(node, FnDef):
        return skeleton(node.body)
    if isinstance(node, Prog):
        return " ; ".join(skeleton(k) for k in node.children())
    return "?"


def distinct_skeletons(bodies: List[str]) -> Tuple[int, Dict[str, int]]:
    """How many genuinely different ideas, not how many strings."""
    counts: Dict[str, int] = {}
    for b in bodies:
        node, err = parse(b)
        if node is None:
            continue
        k = skeleton(node)
        counts[k] = counts.get(k, 0) + 1
    return len(counts), counts


def distinct_shapes(bodies: List[str]) -> Tuple[int, Dict[str, int]]:
    asts: List[Node] = []
    for b in bodies:
        node, err = parse(b)
        if node is not None:
            asts.append(node)
    counts = shapes_of(asts)
    return len(counts), counts


if __name__ == "__main__":
    print("\n" + "=" * 68)
    print("EZR — the pipeline, all four stages")
    print("=" * 68)

    src = "def fact(n) = if n <= 1 then 1 else n * fact(n - 1)"
    print(f"\nsource: {src}\n")

    toks, _ = lex(src)
    print(f"1. LEXER    {len(toks)} tokens")
    print("            " + " ".join(t.text for t in toks[:14]) + " ...")

    c = compile_ezr(src)
    print(f"\n2. PARSER   {type(c.ast).__name__}, "
          f"{c.ast.size()} nodes, depth {c.ast.depth()}")
    print(f"            {c.ast}")

    a = c.analysis
    print(f"\n3. SEMANTIC type={a.ty.value} recursive={a.recursive} "
          f"measure={a.measure}")
    print(f"            calls={sorted(a.calls)} free={sorted(a.free)}")
    print(f"            errors={a.errors or 'none'}")
    print(f"            shape={a.shape}")

    fns = definitions(c.ast)
    print("\n4. EXECUTE")
    for n in (1, 3, 5):
        r = eval_ast(Call("fact", [Num(n)]), {}, fns, 0, limit=99)
        print(f"            fact({n}) = {r.value}  @ {r.confidence}/256")
    print()
