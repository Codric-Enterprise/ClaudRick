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
LOGIC = ("and", "or")  # Accord's own: ezr has neither; each is an If whose skipped side never runs
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
class Not:
    expr: object


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


def check(fn: Function, known: dict | None = None) -> list[str]:
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

    _check_block(fn, known or {}, fn.body, set(names), set(), errors)
    return errors


def _check_block(fn, known, block, params, required, errors, locals_=None):
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
            _check_expr(fn, known, stmt.expr, params, required, locals_, errors)
            locals_.add(stmt.name)
        elif isinstance(stmt, If):
            if not last:
                errors.append("R5: an if must be the last statement of its block")
            _check_expr(fn, known, stmt.cond, params, required, locals_, errors)
            _check_block(fn, known, stmt.then, params, required, errors, locals_)
            _check_block(fn, known, stmt.orelse, params, required, errors, locals_)
        elif isinstance(stmt, Return):
            if not last:
                errors.append("R5: statements after an answer can never run")
            _check_expr(fn, known, stmt.expr, params, required, locals_, errors)


def _check_expr(fn, known, e, params, required, locals_, errors):
    if isinstance(e, Name):
        if e.id in params and e.id not in required:
            errors.append(f"R2: {e.id} is used before any require checks it")
        elif e.id not in params and e.id not in locals_:
            errors.append(f"R2: {e.id} is never bound")
    elif isinstance(e, Bin):
        _check_expr(fn, known, e.left, params, required, locals_, errors)
        _check_expr(fn, known, e.right, params, required, locals_, errors)
    elif isinstance(e, Not):
        _check_expr(fn, known, e.expr, params, required, locals_, errors)
    elif isinstance(e, ListLit):
        for item in e.items:
            _check_expr(fn, known, item, params, required, locals_, errors)
    elif isinstance(e, Call):
        if e.fn in BUILTINS:
            if len(e.args) != 1:
                errors.append(f"R3: {e.fn} takes 1 argument, given {len(e.args)}")
        elif e.fn == fn.name:
            if len(e.args) != len(fn.params):
                given, takes = len(e.args), len(fn.params)
                errors.append(f"R3: {e.fn} called with {given} args, takes {takes}")
        elif e.fn in known:
            if len(e.args) != known[e.fn]:
                given, takes = len(e.args), known[e.fn]
                errors.append(f"R3: {e.fn} called with {given} args, takes {takes}")
        else:
            errors.append(f"R3: {e.fn!r} is not defined in this program")
        for a in e.args:
            _check_expr(fn, known, a, params, required, locals_, errors)


def _calls(node, name) -> bool:
    if isinstance(node, tuple):
        return any(_calls(n, name) for n in node)
    if isinstance(node, Call):
        return node.fn == name or _calls(node.args, name)
    if isinstance(node, ListLit):
        return _calls(node.items, name)
    if isinstance(node, Bin):
        return _calls(node.left, name) or _calls(node.right, name)
    if isinstance(node, (Let, Return, Not)):
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
        if isinstance(e, Bin) and e.op in LOGIC:
            a = expr(e.left)
            t, skip = temp(), label()
            if notes is not None:
                notes[len(out)] = e.left
            out.append(("short", t, e.op, a, skip))
            b = expr(e.right)
            if notes is not None:
                notes[len(out)] = e.right
            out.append(("join", t, e.op, a, b))
            out.append(("mark", skip))
        elif isinstance(e, Not):
            a = expr(e.expr)
            t = temp()
            out.append(("not", t, a))
        elif isinstance(e, Bin):
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


def _whole(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


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
    if op == "%":  # Accord's own: whole numbers only, and the answer takes the divisor's sign
        if not (_whole(x) and _whole(y)):
            return Z(f"misbound: modulo needs whole numbers, got {x!r} and {y!r}")
        if y == 0:
            return Z("misbound: modulo by zero")
        return Thread(x % y, trust)
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


def _list(items: list) -> Thread:
    # CORE.md 1.2: a list carries one trust, the min of its elements; a void element absorbs it.
    void = next((i for i in items if i.void), None)
    if void is not None:
        return void
    return Thread(tuple(i.value for i in items), min((i.trust for i in items), default=LITERAL))


def _truth(word: str, a: Thread) -> Thread | None:
    """A refusal if `a` cannot be a condition, else None."""
    if a.void:
        return a
    if not isinstance(a.value, bool):
        return Z(f"misbound: {word} needs a Bool, got {a.value!r}")
    return None


def _short(op: str, a: Thread) -> Thread | None:
    """`and` stops at false, `or` at true. The skipped side never runs; its trust never counts."""
    refused = _truth(op, a)
    if refused is not None:
        return refused
    return a if a.value == (op == "or") else None


def _join(op: str, a: Thread, b: Thread) -> Thread:
    """Both sides ran: the answer is the second side's, at the chain rule's min."""
    refused = _truth(op, b)
    return refused if refused is not None else Thread(b.value, min(a.trust, b.trust))


def _not(a: Thread) -> Thread:
    refused = _truth("not", a)
    return refused if refused is not None else Thread(not a.value, a.trust)


def _bind(src: Thread, kind: str, trust: int) -> Thread:
    """A declared trust is a ceiling: a value is admitted at the lower of the two."""
    return src if src.void else _admit(src.value, kind, min(src.trust, trust))


def _cap(got: Thread, cap: int) -> Thread:
    """SEMANTICS.md 4.3 [APP]: an answer is never more trusted than the function that gave it."""
    return got if got.void else Thread(got.value, min(got.trust, cap), got.reason)


def _answer(r: Thread, kind: str, path: int) -> Thread:
    # [IF-T]: every condition passed on the way to an Answer caps it.
    return r if r.void else _admit(r.value, kind, min(r.trust, path))


def _enter(name: str, params: tuple, measure, args: tuple, prior, depth: int):
    """The environment for one call, or the refusal that stops it before it starts."""
    if depth >= DEPTH_LIMIT:
        return Z(f"unbounded: {name} is {DEPTH_LIMIT} calls deep")
    env = {p: _bind(arg, kind, trust) for (p, kind, trust), arg in zip(params, args, strict=True)}
    if measure is not None and prior is not None:
        if env[measure].void:
            return env[measure]
        m = _size(env[measure].value)
        if m < 0 or m >= prior:
            return Z(f"unbounded: measure {measure} did not decrease ({prior} -> {m})")
    return env


def run(
    tac: list[tuple],
    args: tuple[Thread, ...],
    _measure: int | None = None,
    _depth: int = 0,
    trace: dict | None = None,
    program: dict | None = None,
) -> Thread:
    name = tac[0][1]
    params = tuple(ins[1:] for ins in tac if ins[0] == "param")
    measure = next(ins[1] for ins in tac if ins[0] == "measure")
    labels = {ins[1]: i for i, ins in enumerate(tac) if ins[0] in ("label", "mark")}
    env = _enter(name, params, measure, args, _measure, _depth)
    if isinstance(env, Thread):
        return env
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
                trace.setdefault(("cmp", name, pc - 1), set()).add(result.value)
                if ins[2] in ORDERING and equal(left.value, right.value):
                    trace[("edge", name, pc - 1)] = True
        elif op == "list":
            temps[ins[1]] = _list([temps[t] for t in ins[2]])
        elif op == "builtin":
            temps[ins[1]] = _builtin(ins[2], temps[ins[3]])
        elif op == "call":
            call_args = tuple(temps[t] for t in ins[3])
            if ins[2] == name:
                here = _size(env[measure].value) if measure is not None else None
                temps[ins[1]] = run(tac, call_args, here, _depth + 1, trace, program)
            elif program and ins[2] in program:
                callee, cap = program[ins[2]]  # SEMANTICS.md 4.3: min(c_f, ...)
                temps[ins[1]] = _cap(run(callee, call_args, None, _depth + 1, None, program), cap)
            else:
                temps[ins[1]] = Z(f"unbound: {ins[2]} is not a verified function here")
        elif op == "require":
            if env[ins[2]].void:
                return env[ins[2]]
        elif op == "let":
            env[ins[1]] = _bind(temps[ins[4]], ins[2], ins[3])
        elif op == "br":
            c = temps[ins[1]]
            refused = _truth("a condition", c)
            if refused is not None:
                return refused
            path = min(path, c.trust)
            if trace is not None:
                trace.setdefault(("br", name, pc - 1), set()).add(c.value)
            pc = labels[ins[2]] + 1 if c.value else labels[ins[3]] + 1
        elif op == "short":
            a = temps[ins[3]]
            if trace is not None and _truth(ins[2], a) is None:
                trace.setdefault(("br", name, pc - 1), set()).add(a.value)
            decided = _short(ins[2], a)
            if decided is not None:
                temps[ins[1]] = decided
                pc = labels[ins[4]] + 1
        elif op == "join":
            b = temps[ins[4]]
            if trace is not None and _truth(ins[2], b) is None:
                trace.setdefault(("br", name, pc - 1), set()).add(b.value)
            temps[ins[1]] = _join(ins[2], temps[ins[3]], b)
        elif op == "not":
            temps[ins[1]] = _not(temps[ins[2]])
        elif op == "mark":
            pass
        elif op == "ret":
            return _answer(temps[ins[1]], tac[0][2], path)
        elif op == "label":
            raise RuntimeError(f"{name}: fell into {ins[1]}; the checker should have refused this")
    raise RuntimeError(f"{name}: ran off the end; the checker should have refused this")


@dataclass
class Verdict:
    passed: list = field(default_factory=list)
    failed: list = field(default_factory=list)


def run_examples(
    fn: Function, tac: list[tuple], trace: dict | None = None, program: dict | None = None
) -> Verdict:
    verdict = Verdict()
    for ex in fn.examples:
        got = run(tac, tuple(Thread(a, LITERAL) for a in ex.args), trace=trace, program=program)
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
    name = tac[0][1]
    produced_by_comparison = {ins[1] for ins in tac if ins[0] == "bin" and ins[2] in COMPARISONS}
    gaps = []
    for i, ins in enumerate(tac):
        if ins[0] == "bin" and ins[2] in COMPARISONS:
            for outcome in (True, False):
                if outcome not in trace.get(("cmp", name, i), set()):
                    gaps.append(("never", i, outcome))
            if ins[2] in ORDERING and ("edge", name, i) not in trace:
                gaps.append(("edge", i, None))
        elif ins[0] in ("br", "short", "join") and _operand(ins) not in produced_by_comparison:
            for outcome in (True, False):
                if outcome not in trace.get(("br", name, i), set()):
                    gaps.append(("never", i, outcome))
    return gaps


def _operand(ins: tuple) -> str:
    """The temp a decision tests: a branch's condition, or the side of and/or just evaluated."""
    return ins[{"br": 1, "short": 3, "join": 4}[ins[0]]]


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


def verify(fn: Function, known: dict | None = None, program: dict | None = None) -> Report:
    """Checker, then the Checks, then their coverage, then the floor. First refusal wins."""
    report = Report(stage="check", fn=fn)
    report.errors = check(fn, known)
    if report.errors:
        return report
    report.tac = lower(fn, report.notes)
    trace: dict = {}
    verdict = run_examples(fn, report.tac, trace, program)
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
    return _cap(run(report.tac, tuple(Thread(a, trust) for a in args)), report.trust)


# ── programs: several functions, each witnessed by its own Checks ────────────


def callees(fn: Function) -> set[str]:
    """The other functions `fn` calls. Builtins and `fn` itself are not included."""
    found: set[str] = set()

    def walk(node):
        if isinstance(node, tuple):
            for n in node:
                walk(n)
        elif isinstance(node, Call):
            if node.fn not in BUILTINS and node.fn != fn.name:
                found.add(node.fn)
            walk(node.args)
        elif isinstance(node, ListLit):
            walk(node.items)
        elif isinstance(node, Bin):
            walk(node.left)
            walk(node.right)
        elif isinstance(node, (Let, Return, Not)):
            walk(node.expr)
        elif isinstance(node, If):
            walk(node.cond)
            walk(node.then)
            walk(node.orelse)

    walk(fn.body)
    return found


@dataclass
class ProgramReport:
    functions: tuple
    reports: dict = field(default_factory=dict)  # name -> Report, in the order verified
    errors: list = field(default_factory=list)

    @property
    def accepted(self) -> bool:
        return not self.errors and all(r.accepted for r in self.reports.values())

    @property
    def stage(self) -> str:
        if self.errors:
            return "program"
        refused = [r.stage for r in self.reports.values() if not r.accepted]
        return refused[0] if refused else "accepted"


def verify_program(functions: tuple) -> ProgramReport:
    """Helpers first. A function is refused if anything it uses was refused."""
    report = ProgramReport(functions)
    names = [f.name for f in functions]
    for n in sorted({n for n in names if names.count(n) > 1}):
        report.errors.append(f"R3: two functions are named {n}")
    if report.errors:
        return report
    arity = {f.name: len(f.params) for f in functions}
    graph = {f.name: callees(f) & set(arity) for f in functions}
    order: list[str] = []
    state: dict[str, str] = {}

    def visit(n: str, path: list[str]):
        if state.get(n) == "done":
            return
        if state.get(n) == "active":
            loop = " -> ".join([*path[path.index(n) :], n])
            report.errors.append(
                f"R5: {loop} call each other; only a function calling itself carries a measure"
            )
            return
        state[n] = "active"
        for m in sorted(graph[n]):
            visit(m, [*path, n])
        state[n] = "done"
        order.append(n)

    for n in names:
        visit(n, [])
    if report.errors:
        return report
    by_name = {f.name: f for f in functions}
    verified: dict[str, tuple] = {}
    for n in order:
        fn = by_name[n]
        refused = sorted(m for m in graph[n] if not report.reports[m].accepted)
        if refused:
            report.reports[n] = Report(
                stage="depends", fn=fn, errors=[f"{n} uses {m}, which was refused" for m in refused]
            )
            continue
        others = {k: v for k, v in arity.items() if k != n}
        report.reports[n] = verify(fn, others, verified)
        if report.reports[n].accepted:
            verified[n] = (report.reports[n].tac, report.reports[n].trust)
    return report


def apply_program(report: ProgramReport, name: str, args: tuple, trust: int = LITERAL) -> Thread:
    """Run one function of a program. It, and everything it uses, must have been accepted."""
    fn_report = report.reports.get(name)
    if fn_report is None:
        return Z(f"unbound: {name} is not a function of this program")
    if not fn_report.accepted:
        return Z(f"unbound: {name} was refused at {fn_report.stage}")
    program = {n: (r.tac, r.trust) for n, r in report.reports.items() if r.accepted}
    got = run(fn_report.tac, tuple(Thread(a, trust) for a in args), program=program)
    return _cap(got, fn_report.trust)
