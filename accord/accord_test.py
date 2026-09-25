"""The gate. Every rule is shown to refuse something, not only to accept the examples."""

from __future__ import annotations

from pathlib import Path

import emit
import prose
from accord import agree
from core import INT_BOUND, AccordError, Thread, check, lower, run, tac_hash

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
for stem in ("classify", "fact"):
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

# ── the two front ends are independent: neither imports the other ───────────
ok("prose" not in (HERE / "emit.py").read_text(), "emit.py does not touch prose")
ok("import emit" not in (HERE / "prose.py").read_text(), "prose.py does not import emit")

total = passed + len(failed)
for label in failed:
    print(f"FAIL  {label}")
print(f"accord: {passed}/{total} passed")
raise SystemExit(0 if not failed else 1)
