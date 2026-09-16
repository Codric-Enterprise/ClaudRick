# Ever

**A language where every value carries how much you trust it, and the
runtime refuses to compute with data that isn't trusted enough.**

Data from outside — an API, a scanner, a form — enters at 120 out of
256. The execute floor is 128. So it does not silently become a
plausible wrong number: it stays below the line until something
corroborates it.

```bash
python3 2-interpreter-python/ever_cli.py run examples/weekly_sales.ever
```
```
total = z [0/256]          # Thursday was never recorded
best = 610 [256/256]
third_day = 380 [256/256]
```

Not a weekly total quietly missing a day. Put a real number in
Thursday's place and the same program gives `2615` at full confidence.

## The 30-second version: evidence buys confidence

This is the part that makes Ever different from `NULL` and `NaN`, and
it is worth the thirty seconds. A definition is a *claim*, so it starts
below the floor — unverified:

```bash
cd 2-interpreter-python
python3 ezrun.py ../examples/earned_trust.ever --call 'growth(100, 3)'
```
```
133.1  @ 120/256
```

The answer is right. It is just not worth anything yet, because nothing
has checked it. Supply witnesses — cases you claim it already gets right:

| witnesses supplied | result |
|---|---|
| none | `133.1  @ 120/256` |
| `growth(100,0) = 100` | `133.1  @ 120/256` — one proves nothing |
| `+ growth(100,1) = 110` | `133.1  @ 183/256` — **clears the floor** |
| `+ growth(100,2) = 121` | `133.1  @ 217/256` |
| one of the three wrong | `133.1  @ 122/256` — back below |
| the same case three times | `133.1  @ 120/256` — one witness, thrice |
| two answers for one case | refused, exit 2 |

The value never changes. What changes is what it is *worth*, and you
change that only with evidence from outside the program. Source code
does not get to vouch for itself.

Then there is depth. Unanchored recursion stops at ⌊π⌋ = 3:

```bash
python3 ezrun.py ../examples/earned_trust.ever -d 3 --call 'growth(100, 20)'
```
```
Z(unbounded) — depth ceiling 3 exceeded
  to lift it: growth decreases n in every self-call, so it can be
  anchored -- but anchoring needs the execute floor first, and it sits
  at 120/256. 2 more passing Examples clears 128, then pass -a growth
```

The refusal tells you what would lift it. Do those two things and it
runs to 20 levels and returns `672.7499949325598  @ 217/256`.

Confidence is evidence about *correctness*, which is not termination —
a function can sit at 240/256 and still loop forever. So depth is
bought separately, with a proof that some parameter decreases.

Every number on this page is pinned by `tests/examples_test.py`.

## What's actually here

**The language** is [`2-interpreter-python/`](2-interpreter-python/README.md) —
lexer, parser, semantic pass, evaluator, REPL, CLI. That is the thing.

It has **two runners**, and they are not rivals:

| | drives | use it for |
|---|---|---|
| `ever_cli.py run` | `runtime.run_source` | the front door: statements, lists, loops, indexing, externs |
| `ezrun.py` | `syntax.py`'s `eval_ast` | the confidence algebra: `[EXAMPLE]`, `[ANCHOR]` |

They implement overlapping but different subsets, which is a real wart
and is documented rather than hidden — see `FINDINGS.md` §7.4 and §7.6.
`examples/earned_trust.ever` sits in the subset both accept.

**Everything else in this tree exists to cross-check that language**,
not to be used directly:

- `0-atom-c/`, `1-phase-cpp/` — the value domain and phase engine in C and C++
- `3-dsl-ruby/`, `4-archive-sql/` — the algebra as a Ruby DSL; the audit archive
- `5-runtime-java/` — a second full implementation sharing no code, plus
  `differential.py`, which runs one corpus through both as processes
- `7-forge/` — four lexers × five parsers against a shared corpus;
  converged at generation 72 over 564,600 fuzzed programs
- `edapt/` — the same "forgive, don't guess" discipline pointed at other languages

## The honest parts

- **Two lineages share this tree.** `differential.py` measures the split:
  **124 programs, 97 agreed, 27 diverged.** Every divergence is
  `let ... in`, list literals, or `len`/`head`/`tail` — in `CORE.md` and
  the Java runtime, not in what `eval_ast` implements. It is red on
  purpose. Which lineage the project keeps is an open decision.
- **`examples/core-lineage/`** holds four programs written for that other
  lineage. They run under the Java runtime and not under `ever run`.
- **Not production-ready for anything that isn't a demonstration.**
- **Not the first system to propagate uncertainty.** `NULL` and `NaN` do
  the mechanically same thing; `Uncertain<T>` (Bornholt et al.) and
  Julia's `Measurements.jl` do it with real statistical rigor —
  distributions, not one integer. Ever trades that rigor for a number
  anyone can read at a glance, and pushes the simplification further than
  the rigorous versions bothered to: into recursion depth, into foreign
  calls, into training loops.

## Verification

```bash
python3 tests/run_all.py          # 29 suites, the gate
python3 tests/examples_test.py    # 37 — every example does what it says
./run.sh                          # the layers, skipping absent toolchains
```

Measured on the last run, not transcribed:

| | |
|---|---|
| `tests/run_all.py` | 29 suites |
| `tests/examples_test.py` | 37 passed |
| `tests/test_edapt.py` | 32 passed |
| `tests/test_backends.py` | 36 passed — **3 of 5 targets** (go, js, rust); R and Kotlin skip when `Rscript`/`kotlinc` are absent |
| `5-runtime-java/differential.py` | 124 programs, 97 agreed, 27 diverged — red on purpose |

`tests/assertion_counts.py --check` runs in the gate and fails it when a
document's assertion count stops matching a real run. That check exists
because five documents once transcribed the same number and four of them
were wrong.

Codric Enterprise · Ricky (Dreid) · 2026
