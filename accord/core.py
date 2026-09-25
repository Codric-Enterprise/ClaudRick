"""Accord core: the tree, the checker, TAC, its interpreter, and how Checks earn trust."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from fractions import Fraction

CERTAIN = 256
LITERAL = 120  # SEMANTICS.md 3.1 [LIT]: a written value is Confident, not Certain
INT_BOUND = 2**53  # past this, a double-backed runtime and an int-backed one disagree
DEPTH_LIMIT = 256  # an implementation limit, reported as Z rather than a host stack overflow
EXECUTE_FLOOR = 128  # SEMANTICS.md 0 / ir.py E_EXECUTE_FLOOR: nothing runs below it
ORDERING = ("<", ">", "<=", ">=")
COMPARISONS = ("==", "!=", *ORDERING)
TYPES = ("Int", "Float", "Text", "Bool")
PREDICATES = ("not_void",)
BUILTINS = ("len", "head", "tail")  # ezr CORE.md 1.2, less `show`: Accord has no output


class AccordError(Exception):
    def __init__(self, line: int, message: str):
        super().__init__(f"line {line}: {message}")
        self.line = line
        self.message = message


def element_type(kind: str) -> str | None:
    if kind.startswith("List[") and kind.endswith("]"):
        return kind[5:-1]
    return None


def valid_type(kind: str) -> bool:
    inner = element_type(kind)
    return valid_type(inner) if inner is not None else kind in TYPES


# ── the tree ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Lit:
    value: int | float | str | bool


@dataclass(frozen=True)
class ListLit:
    items: tuple


@dataclass(frozen=True)
class Name:
    id: str


@dataclass(frozen=True)
class Bin:
    op: str
    left: object
    right: object


@dataclass(frozen=True)
class Call:
    fn: str
    args: tuple


@dataclass(frozen=True)
class Require:
    pred: str
    name: str


@dataclass(frozen=True)
class Let:
    name: str
    type: str
    trust: int
    expr: object


@dataclass(frozen=True)
class If:
    cond: object
    then: tuple
    orelse: tuple


@dataclass(frozen=True)
class Return:
    expr: object


@dataclass(frozen=True)
class Param:
    name: str
    type: str
    trust: int


@dataclass(frozen=True)
class Example:
    args: tuple
    value: object
    trust: int


@dataclass(frozen=True)
class Function:
    name: str
    params: tuple
    returns: str
    measure: str | None
    body: tuple
    examples: tuple


# ── the checker: R1 R2 R3 R4 R5, identical for both surfaces ─────────────────


def check(fn: Function) -> list[str]:
    errors: list[str] = []
    names = [p.name for p in fn.params]
    if fn.name in BUILTINS:
        errors.append(f"R3: {fn.name!r} is a builtin and cannot be redefined")
    if len(set(names)) != len(names):
        errors.append("R3: a parameter is declared twice")
    for p in fn.params:
        if not valid_type(p.type):
            errors.append(f"R3: {p.name} has unknown type {p.type!r}")
        if not 0 <= p.trust <= CERTAIN:
            errors.append(f"R1: {p.name} trust {p.trust} is outside 0..256")
    if not valid_type(fn.returns):
        errors.append(f"R3: unknown return type {fn.returns!r}")

    recursive = _calls(fn.body, fn.name)
    if recursive and fn.measure is None:
        errors.append(f"R5: {fn.name} calls itself but names no measure")
    if fn.measure is not None:
        kind = {p.name: p.type for p in fn.params}.get(fn.measure, "")
        if kind != "Int" and element_type(kind) is None:
            errors.append(f"R5: measure {fn.measure!r} must be an Int or List parameter")
    if not fn.examples:
        errors.append("R4: no examples; nothing shows the function does what it says")
    for ex in fn.examples:
        if len(ex.args) != len(fn.params):
            errors.append(
                f"R4: example gives {len(ex.args)} args, {fn.name} takes {len(fn.params)}"
            )

    _check_block(fn, fn.body, set(names), set(), errors)
    return errors


def _check_block(fn, block, params, required, errors, locals_=None):
    locals_ = set() if locals_ is None else set(locals_)
    required = set(required)
    if not block or not isinstance(block[-1], (Return, If)):
        errors.append(f"R5: a path through {fn.name} ends without answering")
    for i, stmt in enumerate(block):
        last = i == len(block) - 1
        if isinstance(stmt, Require):
            if stmt.pred not in PREDICATES:
                errors.append(f"R2: unknown check {stmt.pred!r}")
            if stmt.name not in params:
                errors.append(f"R2: require names {stmt.name!r}, which is not a parameter")
            required.add(stmt.name)
        elif isinstance(stmt, Let):
            if not valid_type(stmt.type):
                errors.append(f"R3: {stmt.name} has unknown type {stmt.type!r}")
            if not 0 <= stmt.trust <= CERTAIN:
                errors.append(f"R1: {stmt.name} trust {stmt.trust} is outside 0..256")
            if stmt.name in params or stmt.name in locals_:
                errors.append(f"R3: {stmt.name} is already bound")
            _check_expr(fn, stmt.expr, params, required, locals_, errors)
            locals_.add(stmt.name)
        elif isinstance(stmt, If):
            if not last:
                errors.append("R5: an if must be the last statement of its block")
            _check_expr(fn, stmt.cond, params, required, locals_, errors)
            _check_block(fn, stmt.then, params, required, errors, locals_)
            _check_block(fn, stmt.orelse, params, required, errors, locals_)
        elif isinstance(stmt, Return):
            if not last:
                errors.append("R5: statements after an answer can never run")
            _check_expr(fn, stmt.expr, params, required, locals_, errors)


def _check_expr(fn, e, params, required, locals_, errors):
    if isinstance(e, Name):
        if e.id in params and e.id not in required:
            errors.append(f"R2: {e.id} is used before any require checks it")
        elif e.id not in params and e.id not in locals_:
            errors.append(f"R2: {e.id} is never bound")
    elif isinstance(e, Bin):
        _check_expr(fn, e.left, params, required, locals_, errors)
        _check_expr(fn, e.right, params, required, locals_, errors)
    elif isinstance(e, ListLit):
        for item in e.items:
            _check_expr(fn, item, params, required, locals_, errors)
    elif isinstance(e, Call):
        if e.fn in BUILTINS:
            if len(e.args) != 1:
                errors.append(f"R3: {e.fn} takes 1 argument, given {len(e.args)}")
        elif e.fn != fn.name:
            errors.append(f"R3: {e.fn!r} is not defined (only self-calls and {BUILTINS})")
        elif len(e.args) != len(fn.params):
            errors.append(f"R3: {e.fn} called with {len(e.args)} args, takes {len(fn.params)}")
        for a in e.args:
            _check_expr(fn, a, params, required, locals_, errors)


def _calls(node, name) -> bool:
    if isinstance(node, tuple):
        return any(_calls(n, name) for n in node)
    if isinstance(node, Call):
        return node.fn == name or _calls(node.args, name)
    if isinstance(node, ListLit):
        return _calls(node.items, name)
    if isinstance(node, Bin):
        return _calls(node.left, name) or _calls(node.right, name)
    if isinstance(node, (Let, Return)):
        return _calls(node.expr, name)
    if isinstance(node, If):
        return _calls(node.cond, name) or _calls(node.then, name) or _calls(node.orelse, name)
    return False


# ── lowering to TAC ──────────────────────────────────────────────────────────


def lower(fn: Function, notes: dict | None = None) -> list[tuple]:
    out: list[tuple] = [("fn", fn.name, fn.returns)]
    out += [("param", p.name, p.type, p.trust) for p in fn.params]
    out.append(("measure", fn.measure))
    counter = {"t": 0, "L": 0}

    def temp():
        counter["t"] += 1
        return f"t{counter['t']}"

    def label():
        counter["L"] += 1
        return f"L{counter['L']}"

    def expr(e):
        if isinstance(e, Bin):
            a, b = expr(e.left), expr(e.right)
            t = temp()
            if notes is not None:
                notes[len(out)] = e
            out.append(("bin", t, e.op, a, b))
        elif isinstance(e, Call):
            args = tuple(expr(a) for a in e.args)
            t = temp()
            if e.fn in BUILTINS:
                out.append(("builtin", t, e.fn, args[0]))
            else:
                out.append(("call", t, e.fn, args))
        elif isinstance(e, ListLit):
            items = tuple(expr(i) for i in e.items)
            t = temp()
            out.append(("list", t, items))
        elif isinstance(e, Lit):
            t = temp()
            out.append(("const", t, type(e.value).__name__, e.value))
        else:
            t = temp()
            out.append(("load", t, e.id))
        return t

    def block(stmts):
        for s in stmts:
            if isinstance(s, Require):
                out.append(("require", s.pred, s.name))
            elif isinstance(s, Let):
                out.append(("let", s.name, s.type, s.trust, expr(s.expr)))
            elif isinstance(s, Return):
                out.append(("ret", expr(s.expr)))
            elif isinstance(s, If):
                c, lt, le = expr(s.cond), label(), label()
                if notes is not None:
                    notes[len(out)] = s.cond
                out.append(("br", c, lt, le))
                out.append(("label", lt))
                block(s.then)
                out.append(("label", le))
                block(s.orelse)

    block(fn.body)
    return out


def tac_hash(tac: list[tuple]) -> str:
    return hashlib.sha256(repr(tac).encode()).hexdigest()


def format_tac(tac: list[tuple]) -> str:
    return "\n".join(" ".join(str(x) for x in ins) for ins in tac)


# ── the interpreter: runs TAC, never the tree ────────────────────────────────


@dataclass(frozen=True)
class Thread:
    value: object
    trust: int
    reason: str = ""

    @property
    def void(self) -> bool:
        return self.trust == 0 and self.value is None


def Z(reason: str) -> Thread:
    return Thread(None, 0, reason)


def _admit(value, kind: str, trust: int) -> Thread:
    inner = element_type(kind)
    if inner is not None:
        if not isinstance(value, tuple):
            return Z(f"misbound: expected {kind}, got {value!r}")
        items = []
        for i, item in enumerate(value):
            admitted = _admit(item, inner, trust)
            if admitted.void:
                return Z(f"{admitted.reason} (element {i} of {kind})")
            items.append(admitted.value)
        return Thread(tuple(items), trust)
    if kind == "Int":
        if isinstance(value, bool) or not isinstance(value, int):
            return Z(f"misbound: expected Int, got {value!r}")
        if abs(value) > INT_BOUND:
            return Z(f"misbound: {value} is past the Int bound 2^53")
        return Thread(value, trust)
    if kind == "Float":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return Z(f"misbound: expected Float, got {value!r}")
        return Thread(float(value), trust)
    if kind == "Text":
        return Thread(value, trust) if isinstance(value, str) else Z(f"misbound: {value!r}")
    if kind == "Bool":
        return Thread(value, trust) if isinstance(value, bool) else Z(f"misbound: {value!r}")
    return Z(f"misbound: unknown type {kind}")


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def equal(x, y) -> bool:
    """Equality that never lets True stand in for 1, at any depth of nesting."""
    if isinstance(x, tuple) or isinstance(y, tuple):
        return (
            isinstance(x, tuple)
            and isinstance(y, tuple)
            and len(x) == len(y)
            and all(equal(a, b) for a, b in zip(x, y, strict=True))
        )
    if isinstance(x, bool) or isinstance(y, bool):
        return type(x) is type(y) and x == y
    return x == y


def _binop(op: str, a: Thread, b: Thread) -> Thread:
    if a.void:
        return a
    if b.void:
        return b
    trust = min(a.trust, b.trust)
    x, y = a.value, b.value
    if op in ("==", "!="):
        same_kind = (_num(x) and _num(y)) or type(x) is type(y)
        if not same_kind:
            return Z(f"misbound: cannot compare {x!r} with {y!r}")
        return Thread(equal(x, y) == (op == "=="), trust)
    if op in ("<", ">", "<=", ">="):
        if not ((_num(x) and _num(y)) or (isinstance(x, str) and isinstance(y, str))):
            return Z(f"misbound: cannot order {x!r} and {y!r}")
        result = {"<": x < y, ">": x > y, "<=": x <= y, ">=": x >= y}[op]
        return Thread(result, trust)
    if op == "+" and isinstance(x, str) and isinstance(y, str):
        return Thread(x + y, trust)
    if op == "+" and isinstance(x, tuple) and isinstance(y, tuple):
        return Thread(x + y, trust)  # Accord's own: ezr refuses this; Text's rule, extended
    if not (_num(x) and _num(y)):
        return Z(f"misbound: {op} needs numbers, got {x!r} and {y!r}")
    if op == "/":
        if y == 0:
            return Z("misbound: division by zero")
        return Thread(x / y, trust)
    result = {"+": x + y, "-": x - y, "*": x * y}[op]
    if isinstance(result, int) and abs(result) > INT_BOUND:
        return Z(f"misbound: {result} is past the Int bound 2^53")
    return Thread(result, trust)


def _builtin(name: str, a: Thread) -> Thread:
    # CORE.md 1.2: each obeys the chain rule, so the answer carries the list's own trust.
    if a.void:
        return a
    if not isinstance(a.value, tuple):
        return Z(f"misbound: {name} needs a list, got {a.value!r}")
    if name == "len":
        return Thread(len(a.value), a.trust)
    if not a.value:
        return Z(f"unbound: {name} of an empty list")
    if name == "head":
        return Thread(a.value[0], a.trust)
    return Thread(a.value[1:], a.trust)


def _size(value) -> int:
    return len(value) if isinstance(value, tuple) else value


def run(
    tac: list[tuple],
    args: tuple[Thread, ...],
    _measure: int | None = None,
    _depth: int = 0,
    trace: dict | None = None,
) -> Thread:
    name = tac[0][1]
    if _depth >= DEPTH_LIMIT:
        return Z(f"unbounded: {name} is {DEPTH_LIMIT} calls deep")
    params = [ins for ins in tac if ins[0] == "param"]
    measure = next(ins[1] for ins in tac if ins[0] == "measure")
    labels = {ins[1]: i for i, ins in enumerate(tac) if ins[0] == "label"}
    env: dict[str, Thread] = {}
    for (_, pname, kind, trust), arg in zip(params, args, strict=True):
        env[pname] = arg if arg.void else _admit(arg.value, kind, min(arg.trust, trust))
    if measure is not None and _measure is not None:
        if env[measure].void:
            return env[measure]
        m = _size(env[measure].value)
        if m < 0 or m >= _measure:
            return Z(f"unbounded: measure {measure} did not decrease ({_measure} -> {m})")
    temps: dict[str, Thread] = {}
    path = CERTAIN
    pc = next(i for i, ins in enumerate(tac) if ins[0] == "measure") + 1
    while pc < len(tac):
        ins = tac[pc]
        op = ins[0]
        pc += 1
        if op == "const":
            temps[ins[1]] = Thread(ins[3], LITERAL)
        elif op == "load":
            temps[ins[1]] = env.get(ins[2]) or Z(f"unbound: {ins[2]}")
        elif op == "bin":
            left, right = temps[ins[3]], temps[ins[4]]
            temps[ins[1]] = result = _binop(ins[2], left, right)
            if trace is not None and ins[2] in COMPARISONS and not result.void:
                trace.setdefault(("cmp", pc - 1), set()).add(result.value)
                if ins[2] in ORDERING and equal(left.value, right.value):
                    trace[("edge", pc - 1)] = True
        elif op == "list":
            items = [temps[t] for t in ins[2]]
            void = next((i for i in items if i.void), None)
            if void is not None:
                temps[ins[1]] = void
            else:
                trust = min((i.trust for i in items), default=LITERAL)
                temps[ins[1]] = Thread(tuple(i.value for i in items), trust)
        elif op == "builtin":
            temps[ins[1]] = _builtin(ins[2], temps[ins[3]])
        elif op == "call":
            call_args = tuple(temps[t] for t in ins[3])
            here = _size(env[measure].value) if measure is not None else None
            temps[ins[1]] = run(tac, call_args, here, _depth + 1, trace)
        elif op == "require":
            if env[ins[2]].void:
                return env[ins[2]]
        elif op == "let":
            src = temps[ins[4]]
            env[ins[1]] = src if src.void else _admit(src.value, ins[2], min(src.trust, ins[3]))
        elif op == "br":
            c = temps[ins[1]]
            if c.void:
                return c
            if not isinstance(c.value, bool):
                return Z(f"misbound: condition is {c.value!r}, not a Bool")
            path = min(path, c.trust)
            if trace is not None:
                trace.setdefault(("br", pc - 1), set()).add(c.value)
            pc = labels[ins[2]] + 1 if c.value else labels[ins[3]] + 1
        elif op == "ret":
            r = temps[ins[1]]
            if r.void:
                return r
            return _admit(r.value, tac[0][2], min(r.trust, path))
        elif op == "label":
            raise RuntimeError(f"{name}: fell into {ins[1]}; the checker should have refused this")
    raise RuntimeError(f"{name}: ran off the end; the checker should have refused this")


@dataclass
class Verdict:
    passed: list = field(default_factory=list)
    failed: list = field(default_factory=list)


def run_examples(fn: Function, tac: list[tuple], trace: dict | None = None) -> Verdict:
    verdict = Verdict()
    for ex in fn.examples:
        got = run(tac, tuple(Thread(a, LITERAL) for a in ex.args), trace=trace)
        ok = not got.void and equal(got.value, ex.value) and got.trust == ex.trust
        (verdict.passed if ok else verdict.failed).append((ex, got))
    return verdict


# ── the bridge: the body is a claim, the Checks are its witnesses ────────────


def earned(passed: int, total: int) -> int:
    """SEMANTICS.md 4.2 [EXAMPLE]: each passing Check corroborates at intake strength."""
    if passed == 0 or total == 0:
        return 0
    doubt = Fraction(CERTAIN - LITERAL, CERTAIN) ** passed
    return min(math.floor(CERTAIN * (1 - doubt) * Fraction(passed, total)), CERTAIN - 1)


def coverage(tac: list[tuple], trace: dict) -> list[tuple]:
    """Accord's own rule: every decision seen both ways, every ordering tried at its edge."""
    produced_by_comparison = {ins[1] for ins in tac if ins[0] == "bin" and ins[2] in COMPARISONS}
    gaps = []
    for i, ins in enumerate(tac):
        if ins[0] == "bin" and ins[2] in COMPARISONS:
            for outcome in (True, False):
                if outcome not in trace.get(("cmp", i), set()):
                    gaps.append(("never", i, outcome))
            if ins[2] in ORDERING and ("edge", i) not in trace:
                gaps.append(("edge", i, None))
        elif ins[0] == "br" and ins[1] not in produced_by_comparison:
            for outcome in (True, False):
                if outcome not in trace.get(("br", i), set()):
                    gaps.append(("never", i, outcome))
    return gaps


@dataclass
class Report:
    stage: str
    fn: Function | None = None
    tac: list = field(default_factory=list)
    notes: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    failed: list = field(default_factory=list)
    gaps: list = field(default_factory=list)
    trust: int = 0

    @property
    def accepted(self) -> bool:
        return self.stage == "accepted"


def verify(fn: Function) -> Report:
    """Checker, then the Checks, then their coverage, then the floor. First refusal wins."""
    report = Report(stage="check", fn=fn)
    report.errors = check(fn)
    if report.errors:
        return report
    report.tac = lower(fn, report.notes)
    trace: dict = {}
    verdict = run_examples(fn, report.tac, trace)
    report.trust = earned(len(verdict.passed), len(fn.examples))
    if verdict.failed:
        report.stage, report.failed = "checks", verdict.failed
        return report
    report.gaps = coverage(report.tac, trace)
    if report.gaps:
        report.stage = "coverage"
        return report
    if report.trust < EXECUTE_FLOOR:
        report.stage = "floor"
        return report
    report.stage = "accepted"
    return report


def apply(report: Report, args: tuple, trust: int = LITERAL) -> Thread:
    """SEMANTICS.md 4.3 [APP]: an answer is never more trusted than the function that gave it."""
    if not report.accepted:
        return Z(
            f"unbound: {report.fn.name if report.fn else 'program'} was refused at {report.stage}"
        )
    got = run(report.tac, tuple(Thread(a, trust) for a in args))
    return got if got.void else Thread(got.value, min(got.trust, report.trust), got.reason)
