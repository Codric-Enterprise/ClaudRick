"""The gate. Every rule is shown to refuse something, not only to accept the examples."""

from __future__ import annotations

from pathlib import Path

import emit
import prose
from accord import agree
from core import INT_BOUND, AccordError, Thread, check, equal, lower, run, tac_hash

HERE = Path(__file__).parent
EX = HERE / "examples"
passed, failed = 0, []


def ok(cond: bool, label: str):
    global passed
    if cond:
        passed += 1
    else:
        failed.append(label)


def src(name: str) -> str:
    return (EX / name).read_text()


def parse_error(parse, source: str) -> str:
    try:
        parse(source)
    except AccordError as err:
        return err.message
    return ""


def call(source_parse, source: str, *args) -> Thread:
    return run(lower(source_parse(source)), tuple(Thread(a, 120) for a in args))


# ── the two example pairs agree end to end ───────────────────────────────────
for stem in ("classify", "fact", "total", "reverse"):
    r = agree(src(f"{stem}.emit"), src(f"{stem}.prose"))
    ok(r["stage"] == "agreed", f"{stem}: agreed ({r['stage']}: {r['errors']})")
    ok(r["examples"] == (2, 2), f"{stem}: both examples ran and held")
    ok(emit.parse(src(f"{stem}.emit")) == prose.parse(src(f"{stem}.prose")), f"{stem}: one tree")

# ── the agreement is not a tautology: a one-token change is caught ──────────
r = agree(src("classify.emit"), src("classify.prose").replace("equal to 128", "equal to 127"))
ok(r["stage"] == "agree: tree", "threshold 127 vs 128 is refused at the tree")
ok("body" in r["errors"][0], "the refusal names the part that differs")
r = agree(src("classify.emit"), src("classify.prose").replace("greater than", "at least"))
ok(r["stage"] == "agree: tree", "> vs >= is refused at the tree")
h1, h2 = (tac_hash(lower(emit.parse(src(f)))) for f in ("classify.emit", "fact.emit"))
ok(h1 != h2, "different programs hash differently")
ok(h1 == tac_hash(lower(prose.parse(src("classify.prose")))), "same program, same hash")

# ── examples are executed, not asserted ─────────────────────────────────────
wrong = agree(
    src("classify.emit").replace('"Certain" @ 100', '"Certain" @ 200'),
    src("classify.prose").replace('"Certain", trusted 100', '"Certain", trusted 200'),
)
ok(wrong["stage"] == "examples", "a wrong expected trust is caught by running it")
ok(len(wrong["errors"]) == 2, "both surfaces ran it and both reported it")

# ── trust follows SEMANTICS.md: literals 120, chain is min, [IF-T] ──────────
got = call(emit.parse, src("classify.emit"), 200)
ok(got.value == "Certain" and got.trust == 100, "answer trust = min(literal 120, cap 100)")
got = call(emit.parse, src("fact.emit"), 5)
ok(got.value == 120 and got.trust == 120, "fact(5) = 120 at literal trust 120")
got = call(emit.parse, src("fact.emit"), 0)
ok(got.value == 1, "base case answers without evaluating the recursive arm")

# ── R1: trust must be written ───────────────────────────────────────────────
e = parse_error(emit.parse, src("classify.emit").replace(" [trust: 100]", ""))
ok(e.startswith("R1"), f"emit: a parameter without trust is refused ({e})")
p = parse_error(prose.parse, src("classify.prose").replace(", trusted 100 of 256.", "."))
ok(p.startswith("R1"), f"prose: a parameter without trust is refused ({p})")
p = parse_error(
    prose.parse, src("classify.prose").replace("  signal is a Float, trusted 100 of 256.\n", "")
)
ok(p != "", "prose: an undeclared parameter is refused")
e = parse_error(emit.parse, src("classify.emit").replace("Float [trust: 256] = 128", "Float = 128"))
ok(e.startswith("R1"), "emit: a let without trust is refused")
p = parse_error(
    prose.parse,
    src("classify.prose").replace("a Float, trusted 256 of 256, equal", "a Float equal"),
)
ok(p.startswith("R1"), "prose: a let without trust is refused")

# ── R2: a parameter is checked before it is used ────────────────────────────
for label, parse, text, line in (
    ("emit", emit.parse, src("classify.emit"), "  require: not_void(signal)\n"),
    ("prose", prose.parse, src("classify.prose"), "  Make sure signal is not void.\n"),
):
    errors = check(parse(text.replace(line, "")))
    ok(
        any(x.startswith("R2: signal is used before") for x in errors),
        f"{label}: use before require",
    )
errors = check(emit.parse(src("classify.emit").replace("signal > threshold", "signal > limit")))
ok(any("limit is never bound" in x for x in errors), "an unbound name is refused")

# ── R3: types are closed and Int is bounded where runtimes stop agreeing ────
errors = check(
    emit.parse(src("classify.emit").replace("Float [trust: 100]", "Number [trust: 100]"))
)
ok(any(x.startswith("R3") for x in errors), "an unknown type is refused")
got = call(emit.parse, src("fact.emit"), INT_BOUND + 1)
ok(got.void and "Int bound" in got.reason, "an Int argument past 2^53 is refused, not rounded")
got = call(emit.parse, src("fact.emit"), 19)
ok(got.void and "Int bound" in got.reason, "19! overflows the bound and is refused")
got = call(emit.parse, src("fact.emit"), 18)
ok(got.value == 6402373705728000, "18! is inside the bound and exact")
got = call(emit.parse, src("classify.emit"), "loud")
ok(got.void and "misbound" in got.reason, "Text where a Float is declared is refused")

# ── R4: no examples, no program ─────────────────────────────────────────────
no_examples = "\n".join(x for x in src("fact.emit").splitlines() if not x.startswith("example"))
ok(any(x.startswith("R4") for x in check(emit.parse(no_examples))), "a function with no examples")

# ── R5: every path answers, and recursion carries a shrinking measure ───────
for label, parse, text, old, new in (
    ("emit", emit.parse, src("fact.emit"), "measure: n", "measure: none"),
    ("prose", prose.parse, src("fact.prose"), "It shrinks by n.", "It never repeats."),
):
    errors = check(parse(text.replace(old, new)))
    ok(
        any("calls itself but names no measure" in x for x in errors),
        f"{label}: recursion unmeasured",
    )
e = parse_error(emit.parse, src("fact.emit").replace("  else:\n    return n * fact(n - 1)\n", ""))
ok(e.startswith("R5"), "emit: an if without else is refused")
p = parse_error(
    prose.parse,
    src("fact.prose").replace("  Otherwise:\n    Answer n times fact of (n minus 1).\n", ""),
)
ok(p.startswith("R5"), "prose: an If without Otherwise is refused")
stuck = src("fact.emit").replace("fact(n - 1)", "fact(n)")
got = call(emit.parse, stuck, 3)
ok(got.void and "did not decrease" in got.reason, "a measure that does not shrink is stopped")
grows = src("fact.emit").replace("fact(n - 1)", "fact(n + 1)")
ok(call(emit.parse, grows, 3).void, "a measure that grows is stopped")

deep = call(emit.parse, src("fact.emit"), 5000)
ok(
    deep.void and "calls deep" in deep.reason,
    "a deep but shrinking recursion is refused, not crashed",
)
seven = "def seven(x: Int [trust: 256]) -> Int\n  measure: none\n  return 7\n"
seven += "example: seven(1) == 7 @ 120\n"
ok(call(emit.parse, seven, 1).trust == 120, "a literal answer carries literal trust 120, not 256")

guard = (
    "def pick(x: Int [trust: 256]) -> Int\n  measure: none\n  require: not_void(x)\n  return 7\n"
)
held = run(
    lower(emit.parse(guard + "example: pick(1) == 7 @ 120\n")), (Thread(None, 0, "unbound: x"),)
)
ok(held.void and held.reason == "unbound: x", "require stops a void input the answer never reads")

# ── Z is checked before arithmetic, and it is contagious along the chain ────
zero = src("classify.emit").replace("= 128", "= 128 / 0")
got = call(emit.parse, zero, 200)
ok(got.void and "division by zero" in got.reason, "Z from a division reaches the answer")


# ── lists: CORE.md 1.2, with every refusal it names ─────────────────────────
def program(signature: str, *body: str, example: str) -> str:
    lines = [f"def {signature}", "  measure: none", *[f"  {b}" for b in body]]
    return "\n".join(lines) + f"\nexample: {example}\n"


first = program(
    "first(xs: List[Int] [trust: 256]) -> Int",
    "require: not_void(xs)",
    "return head(xs)",
    example="first([7]) == 7 @ 120",
)
got = call(emit.parse, first, ())
ok(got.void and got.reason == "unbound: head of an empty list", "head of [] is a refusal")
rest = first.replace("-> Int", "-> List[Int]").replace("head(xs)", "tail(xs)")
got = call(emit.parse, rest, ())
ok(got.void and got.reason == "unbound: tail of an empty list", "tail of [] is a refusal")
ok(equal(call(emit.parse, rest, (1, 2, 3)).value, (2, 3)), "tail drops exactly the first")
got = call(emit.parse, first.replace("List[Int]", "Int"), 5)
ok(got.void and "needs a list" in got.reason, "head of a number is refused")

e = parse_error(emit.parse, src("total.emit").replace("[1, 2, 3]", "[1, 2, 3,]"))
ok("trailing comma" in e, "emit: a trailing comma in a list is refused (CORE ruling 7)")
p = parse_error(prose.parse, src("total.prose").replace("1, 2 and 3", "1, 2, and 3"))
ok("final 'and'" in p, "prose: one list form only, so no comma before 'and'")
e = parse_error(emit.parse, src("total.emit").replace("List[Int] [trust", "List [trust"))
ok(e.startswith("R3"), "emit: a List without an element type is refused")
p = parse_error(prose.parse, src("total.prose").replace("a List of Int,", "a List,"))
ok(p.startswith("R3"), "prose: a List without an element type is refused")

got = call(emit.parse, src("total.emit"), ("a",))
ok(got.void and "element 0" in got.reason, "a Text element in a List[Int] is refused")
got = call(emit.parse, src("total.emit"), (1, INT_BOUND + 1))
ok(got.void and "Int bound" in got.reason, "an element past 2^53 is refused, not rounded")
ok(call(emit.parse, src("total.emit"), 5).void, "a number where a list is declared is refused")

pair = program(
    "pair(a: Int [trust: 100], b: Int [trust: 256]) -> List[Int]",
    "require: not_void(a)",
    "require: not_void(b)",
    "return [a, b]",
    example="pair(1, 2) == [1, 2] @ 100",
)
got = call(emit.parse, pair, 1, 2)
ok(equal(got.value, (1, 2)) and got.trust == 100, "a list is as trusted as its weakest element")
got = call(emit.parse, pair.replace("[a, b]", "[]"), 1, 2)
ok(got.value == () and got.trust == 120, "the empty list is a written literal: 120")
got = call(emit.parse, pair.replace("[a, b]", "[a, b / 0]"), 1, 2)
ok(got.void and "division by zero" in got.reason, "a Z element makes the whole list Z")
second = pair.replace("-> List[Int]", "-> Int").replace("[a, b]", "head(tail([a, b]))")
got = call(emit.parse, second, 1, 2)
ok(got.value == 2 and got.trust == 100, "tail keeps the whole list's trust, as CORE does")
# + joins lists: Accord's own rule (ezr refuses it), extending Text's, so trust is min
got = call(emit.parse, pair.replace("[a, b]", "[a] + [b]"), 1, 2)
ok(equal(got.value, (1, 2)) and got.trust == 100, "[a] + [b] joins, at the weaker side's trust")
got = call(emit.parse, pair.replace("[a, b]", "[b] + [a]"), 1, 2)
ok(equal(got.value, (2, 1)), "joining keeps the left list first")
widen = pair.replace("[trust: 100]", "[trust: 256]")
got = run(lower(emit.parse(widen.replace("[a, b]", "[] + [a]"))), (Thread(1, 256), Thread(2, 256)))
ok(equal(got.value, (1,)) and got.trust == 120, "joining a written [] costs literal trust 120")
got = call(emit.parse, pair.replace("[a, b]", "[a] + [b / 0]"), 1, 2)
ok(got.void and "division by zero" in got.reason, "a Z side makes the join Z")
got = call(emit.parse, pair.replace("[a, b]", "[a] + b"), 1, 2)
ok(got.void and "needs numbers" in got.reason, "a list plus a number is refused")
got = call(emit.parse, pair.replace("[a, b]", '"a" + [b]'), 1, 2)
ok(got.void and "needs numbers" in got.reason, "Text plus a list is refused")
got = call(emit.parse, pair.replace("[a, b]", '[a] + ["x"]'), 1, 2)
ok(got.void and "element 1" in got.reason, "a joined Text element is refused at List[Int]")
grow = program(
    "grow(xs: List[Int] [trust: 256]) -> Int",
    "require: not_void(xs)",
    "if len(xs) > 5:",
    "  return 0",
    "else:",
    "  return grow(xs + [1])",
    example="grow([]) == 0 @ 120",
).replace("measure: none", "measure: xs")
got = call(emit.parse, grow, ())
ok(got.void and "did not decrease (0 -> 1)" in got.reason, "a list measure that grows is stopped")
same = pair.replace("-> List[Int]", "-> Bool").replace("[a, b]", "[a] == [true]")
ok(call(emit.parse, same, 1, 2).value is False, "[1] == [true] is false at any depth")

stuck = src("total.emit").replace("total(tail(xs))", "total(xs)")
got = call(emit.parse, stuck, (1, 2))
ok(got.void and "did not decrease" in got.reason, "a list measure must shrink too")
text_measure = program(
    "t(s: Text [trust: 256]) -> Int", "require: not_void(s)", "return 1", example="t(1) == 1 @ 120"
).replace("measure: none", "measure: s")
errors = check(emit.parse(text_measure))
ok(any("must be an Int or List" in x for x in errors), "a Text measure is refused")
errors = check(emit.parse(src("total.emit").replace("len(xs)", "len(xs, xs)")))
ok(any("len takes 1 argument" in x for x in errors), "a builtin called with two arguments")
errors = check(emit.parse(src("total.emit").replace("total", "len")))
ok(any("cannot be redefined" in x for x in errors), "a function may not be named len")

r = agree(src("total.emit"), src("total.prose").replace("List of Int", "List of Float"))
ok(r["stage"] == "agree: tree", "List[Int] against List of Float is refused at the tree")
nested_emit = program(
    "count(xss: List[List[Int]] [trust: 256]) -> Int",
    "require: not_void(xss)",
    "return len(xss)",
    example="count([[1], []]) == 2 @ 120",
)
nested_prose = """To count given xss, answering an Int:
  xss is a List of List of Int, trusted 256 of 256.
  It never repeats.
  Make sure xss is not void.
  Answer the length of xss.
Check: count of the list of (the list of 1) and the empty list gives 2, trusted 120.
"""
r = agree(nested_emit, nested_prose)
ok(r["stage"] == "agreed", f"nested lists agree across both surfaces ({r['errors']})")

rest_emit = program(
    "drop(xs: List[Int] [trust: 256]) -> List[Int]",
    "require: not_void(xs)",
    "return tail(xs)",
    example="drop([2, 3]) == [3] @ 120",
)
rest_prose = """To drop given xs, answering a List of Int:
  xs is a List of Int, trusted 256 of 256.
  It never repeats.
  Make sure xs is not void.
  Answer the rest of xs.
Check: drop of the list of 2 and 3 gives the list of 3, trusted 120.
"""
r = agree(rest_emit, rest_prose)
ok(r["stage"] == "agreed", f"a one-item list ends at ', trusted' ({r['errors']})")
r = agree(rest_emit.replace("drop", "rest"), rest_prose.replace("drop", "rest"))
ok(r["stage"] == "prose: parse", "Prose reserves 'rest', so a function named rest is refused")

# ── the two front ends are independent: neither imports the other ───────────
ok("prose" not in (HERE / "emit.py").read_text(), "emit.py does not touch prose")
ok("import emit" not in (HERE / "prose.py").read_text(), "prose.py does not import emit")

total = passed + len(failed)
for label in failed:
    print(f"FAIL  {label}")
print(f"accord: {passed}/{total} passed")
raise SystemExit(0 if not failed else 1)
