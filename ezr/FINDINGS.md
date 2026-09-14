# Ever / Tapestry — Research Findings

Codric Enterprise · Ricky (Dreid) · 2026

Everything below was computed, not asserted. Run `python3 research.py`.

---

## 1. The First Law, applied to Z

**Confidence is not the conserved quantity. Uncertainty is.**

Let `u = (256 − confidence) / 256` — normalized ignorance.
Z has `u = 1`. Certain has `u = 0`.

Excel — the corroboration formula — is *identically* multiplicative
uncertainty combination:

```
u_result = u_a × u_b
```

Verified across the full grid: **1020 / 1089**, and the 69 gaps are the
interesting part.

That number used to read 1089 / 1089, and it was measuring nothing.
`research.py` carried its own copy of `excel` — the **uncapped** formula,
`min(256, a + b − ab/256)` — and compared it against the closed form of
the same uncapped rule. A formula agreeing with itself. The cap that this
very section reports as "fixed in C, Python and Ruby" had never reached
the copy here, so `research.excel(250, 250)` still returned 256: the
manufactured-Certain bug, alive in the file that reports it as dead.

`research.py` now imports `excel` from `ever.py`. One formula, one place.
Against the language's actual function the grid is 1020 / 1089, and every
one of the 69 disagreements is the cap firing:

| gap | count | what it is |
|---|---:|---|
| two imperfect witnesses rounding up to Certain | 5 | what the cap is for |
| one witness already Certain | 64 | `u = 1 × 0 = 0` says 256; the cap says 255 |
| both Certain | 0 | agree |

The 64 are worth a decision. T3 says `u = 0` requires **some** `u_i = 0`
— one witness already at zero ignorance is enough. The shipped cap
requires **both** inputs at Certain and returns 255 otherwise, so
`excel(Z, Certain) = 255` where the algebra says 256. Either T3 is loose
and the language means both, or the cap is one notch too strict. Recorded
rather than decided; it changes what `EXCEL` means.

Nothing tests it, on any side. `kitchen_sink.c` checks
`e_excel_formula(CERTAIN, CERTAIN)`, then a sweep of `e_excel_formula(c,
c)` for matching pairs — never an asymmetric pairing with one Certain
input. So the 64 points where the cap and the algebra disagree are
untested in C, untested in Python, and were unmeasurable here because
this file held an uncapped copy. Three independent reasons nobody saw
them, which is usually how a question stays open without anyone deciding
it was open.

That is the standard rule for combining independent evidence: the chance
both witnesses are wrong is the product of each being wrong. It was
derived here from first principles and landed on the correct formula.

### Three consequences that were never designed in

**Excel creates nothing.** Two witnesses agreeing does not manufacture
confidence. It multiplies two ignorances into a smaller one. The
confidence was already distributed across the witnesses; corroboration
only revealed it. Conservation holds.

**Z-contagion is arithmetic — but not this arithmetic.** The claim
printed here for a long time was: `u = 1`, and `1 × x = 1` for every x,
so Z is the absorbing element under multiplication. Two of those three
statements are false. `1 × x = x`, not 1; and Z is the **identity** of
corroboration, not its absorbing element. Measured:

```
excel(0, b)   == b     for every b in 0..256     Z is the identity
excel(256, b) == 256   for every b in 0..256     CERTAIN is what absorbs
```

That is the right behaviour and always was the code's behaviour —
corroborating with a witness who knows nothing leaves what you had
exactly as it was. Only the description was wrong.

Z-contagion is real, and it is a theorem — of the **chain rule**, which
is `min`, where `min(0, b) = 0` for every b. So Z is contagious along a
chain of dependence and inert under corroboration. A computation that
consumed an unknown is unknown; a witness who abstains has not testified.
Conflating the two operations made a true statement about `min` read as a
false one about `excel`, and the function cited as proof
(`Thermo.z_absorbs`) was in fact asserting `excel(0, b) == b` — the
identity law, under a name promising absorption. It returned True and was
read as confirming a claim it never made.

Now split into three functions that each say what they check, and each
reports a count rather than a bool, because two of the three laws do not
hold everywhere in the shipped `excel`:

| law | shipped | pure algebra |
|---|---:|---:|
| `excel(Z, b) == b` — Z is the identity | 256/257 | 257/257 |
| `excel(Certain, b) == Certain` — Certain absorbs | 1/257 | 257/257 |
| `min(Z, b) == Z` — Z absorbs along the chain | 257/257 | 257/257 |

The cap breaks both `EXCEL` laws at the Certain boundary and nowhere
else. That is a real cost of the cap, and nothing reported it, because
the file that would have was measuring the uncapped formula where nothing
breaks. The chain rule is untouched — Z-contagion holds everywhere, which
is the one thing the original claim got right about the language even
while getting the algebra wrong.

**Certain is unreachable by combination.** `u = 0` requires some
`u_i = 0` exactly. A product of non-zero terms is never zero. No stack of
imperfect witnesses, at any strength or count, reaches certainty.

### The bug this found

The integer scale used to round the last fraction away:

```
excel(250, 250) → 256     manufactured Certain from evidence
excel(255, 255) → 256
```

True values were 255.78 and 255.94 — never 256. The language was
inferring Certain from accumulated evidence, contradicting its own rule
that Certain is earned at runtime and never guessed.

Fixed in C, Python and Ruby. Combination now caps at 255. Only two
already-verified inputs (both exactly 256) return 256.

```
excel(250, 250) → 255
excel(256, 256) → 256
```

### Where thermodynamics stops being a good analogy

The Third Law says absolute zero is unreachable in finite steps. Ever's Z
is reachable instantly, by contagion. The analogy holds for the First Law
(conservation) and breaks for the Third. Worth saying plainly rather than
stretching the metaphor.

---

## 2. The corpus weighed against φ

**φ does not govern the archive. 1 of 6 ratios land near 1.618, which is
what chance would give.**

| ratio | value | vs φ | |
|---|---|---|---|
| patterns : errors | 1.263 | 0.781 | |
| mean confidence : execute floor | 1.039 | 0.642 | |
| Certain : execute floor | 2.000 | 1.236 | |
| π-warn : π-squared | 3.240 | 2.002 | |
| execute floor : π-warn | 1.580 | 0.977 | **at φ** |
| intake : π-warn | 1.481 | 0.916 | |

φ earns its place as the **output equalizer**, where it is applied
deliberately to flag outliers against a set mean. It is not a law the
corpus obeys on its own.

The three constants do three different jobs, and only two are structural:

- **256** is load-bearing. 4⁴, the states of a byte, the whole scale.
- **π** sets widths. ⌊256/π⌋ = 81, ⌊256/π²⌋ = 25, ⌊π⌋ = 3.
- **φ** equalizes output. Applied, not obeyed.

Claiming φ governs the system would be decoration, and a technical
investor would find that in ten minutes.

---

## 3. Defect profile

Every finding across every layer classifies into the five binding
defects. Nothing fell outside the taxonomy.

| defect | count | share |
|---|---|---|
| unbounded | 16 | 84.2% |
| orphaned | 2 | 10.5% |
| misbound | 1 | 5.3% |

**Unbounded dominates at 84%.** Extent-not-delimited — missing
terminators, unclosed structures, unbounded writes. That is the single
highest-value defect class to target, and it is the one most amenable to
static detection.

Three of five classes appeared. `unbound` and `overbound` did not surface
in this corpus, which is a statement about the corpus, not the taxonomy.

---

## 4. Witnesses required to converge

From equal independent evidence, to reach a target:

| each | →128 | →200 | →240 | →255 |
|---|---|---|---|---|
| 60 | 3 | 6 | 11 | 24 |
| 100 | 2 | 4 | 6 | 13 |
| 128 | 1 | 3 | 4 | 9 |
| 150 | 1 | 2 | 4 | 8 |
| 180 | 1 | 2 | 3 | 6 |
| 200 | 1 | 1 | 2 | 5 |
| 240 | 1 | 1 | 1 | 3 |

256 appears nowhere. That column does not exist, and its absence is the
formal reason Certain must come from outside the corpus.

---

## 5. Executed verification

Everything below is emitted by `python3 tests/assertion_counts.py`, which
runs every suite and reads the tally each one prints. Nothing here is
typed by hand, and `--check` (wired into `run_all.py`) fails the gate if
this block stops matching a real run.

<!-- assertion-counts:begin -->
| suite | assertions | failed |
|---|---:|---:|
| C atom         | 88 | 0 |
| C bridge       | ran | 0 |
| EValue (C)     | 98 | 0 |
| IR+arena (C)   | 70 | 0 |
| Phase (C++)    | 50 | 0 |
| Lexer          | 91 | 0 |
| Parser         | 74 | 0 |
| ABI            | 46 | 0 |
| EValue (Py)    | 85 | 0 |
| Interpreter    | 83 | 0 |
| IR bridge      | 7 | 0 |
| Pipeline       | 65 | 0 |
| Abstraction    | 70 | 0 |
| Runner         | 46 | 0 |
| Vowels         | 79 | 0 |
| Teaching       | 41 | 0 |
| SQL archive    | 56 | 0 |
| Kitchen sink   | ran | 0 |
| Form IR (C99)  | ran | 0 |
| Profiler       | 99 | 0 |
| Native (C99)   | ran | 0 |
| Integration    | ran | 0 |
| Gold standard  | ran | 0 |
| Golden master  | 31 | 0 |
| Notebook       | ran | 0 |
| Research       | ran | 0 |
| Algebra parity | ran | 0 |
| **total** | **1179** | **0** |

The total covers the 18 suites that report a tally. 9 more run and pass without counting assertions (C bridge, Kitchen sink, Form IR (C99), Native (C99), Integration, Gold standard, Notebook, Research, Algebra parity); they are verified, not quantified, and inventing a number for them is what this table exists to prevent.
<!-- assertion-counts:end -->

### Why this is generated now

The table this replaces said the Python interpreter had **81** assertions.
It has 83, and has for a while. Four other documents — `PIPELINE.md`,
`ABI.md`, `VOWELS.md`, `TEACHING.md` — carried their own copies of the
same row and all four said 83, so the tree disagreed with itself in five
places about one number.

The 81 was not a typo. The old table totalled 88 + 50 + **81** + 56 =
275, and printed 275 — self-consistent, and therefore right when it was
written. `ever_test.py` then gained two assertions and no document
noticed, because nothing compared them. That is the whole failure mode: a
transcribed number cannot go stale loudly.

Three unrelated 81s in this project made it harder to spot rather than
easier. ⌊256/π⌋ = 81 is `PI_WARN`, the forge reports 81 passing
assertions, and this table claimed 81 — so the wrong number looked
familiar every time anyone read past it.

The four duplicate tables are gone; they point here. One number, one
place, generated.

### What is not counted

Eight suites pass without reporting a tally (`C bridge`, `Kitchen sink`,
`Form IR`, `Native`, `Integration`, `Gold standard`, `Notebook`,
`Research`). They are listed as `ran`. An earlier draft of the generator
scanned their output for anything shaped like a count and reported
`Integration` as 12, `Gold standard` as 8, `Notebook` as 6 and `Research`
as 1089 — that last being the excel verification grid, not an assertion
count at all. Four invented numbers, produced by the script written to
stop numbers being invented. The heuristic is gone: a canonical tally, or
nothing.

### Layers not in that table

Layer 3 (Ruby) **does** run here: `cd 3-dsl-ruby && ruby ever.rb` reports
69 passed, 0 failed. The claim that it had never been executed for want
of a toolchain was true when written and is not now.

Layer 5 (Java) runs too — `RuntimeTest`, 98 assertions — as does
`7-forge` at 81. Neither is in `run_all.py`, so neither appears above;
that is a gap in the gate, recorded in §7.4, not an absence of tests.

---

## 6. What is safe to claim

**Supported:**
- Excel is multiplicative uncertainty combination at 1020/1089 grid
  points; the 69 gaps are all the 255 cap, 64 of them where one witness
  is already Certain (§1). The old "1089/1089 exact" compared a stale
  local copy of the uncapped formula against itself.
- Z-contagion is a theorem of the CHAIN rule, `min(0, b) = 0` — not of
  corroboration, where Z is the identity and `excel(0, b) = b` (§1)
- Certain is formally unreachable by combination at any strength, and is
  the absorbing element of corroboration
- Every finding classifies into five binding defects
- The assertion totals in §5, which are generated from a run rather than
  transcribed
- Anchored threads cross five languages with zero loss; unanchored drift
  is measurable and the database refuses to record an anchored loss

**Not supported:**
- φ governing the corpus
- Self-correction. The system teaches and verifies; it does not yet
  rewrite broken source.

---

## 7. Three evaluators, one rule, three answers

Everything in this section was produced by running the code, not by
reading it. Each claim names the command that produces it.

### 7.1 [APP] dropped its c_f term in two of the three evaluators

SEMANTICS.md §4.3 gives application as `min(c_f, c_args, c_result)`.
Three evaluators implement it and only one had all three terms:

| evaluator | file | c_f present |
|---|---|---|
| `Lambda` | `abstract.py` | yes |
| `eval_ast` | `syntax.py` | **no** |
| `eval_confidence` | `runtime.py` | **no** |

`runtime.py` is the one `ever run` uses. Its own docstring named the
omission and called it an honest approximation, but the consequence was
not stated: nothing anywhere read `ScopeEntry.confidence` for an `SK.FN`
entry, so a function's confidence was a field that could be written and
never read. Measured before the fix, on that exact path:

```
def dbl(n) = n * 2        with dbl's scope entry forced to 1/256
dbl(21)  ->  42 @ 256/256          [APP] wants min(1, 256) = 1
```

Both are now complete. The 26-suite gate is unchanged by the
`runtime.py` fix, and that is the point: it is a no-op for every program
that does not set a function's confidence, and it is what makes earned
confidence mean anything at all. Guarded by `ezrun_test.py`, which fails
in exactly one assertion if the term is removed again.

### 7.2 The two evaluators still disagree about [DEF], by 136 points

`eval_ast` enters an undefined name at `E_INTAKE` (120), per [DEF]: a
definition is a claim, not a verification, and 120 is below the execute
floor of 128. `runtime.run_source` registers functions at `EV_CERTAIN`
(256) via `EvScope.set_fn`'s default. Three runners, one program, one
outlier:

```
def dbl(n) = n * 2
def main() = dbl(21)

ezrun.py            (syntax.py eval_ast)   42 @ 120/256
5-runtime-java/ezr  (Java, CORE.md)        42 @ 120/256
ever run            (runtime.run_source)   42 @ 256/256
```

The Java runtime matters here because it shares no code, no type system
and no habits with either Python evaluator, and it was written against
`CORE.md` rather than against `runtime.py`. Two independent
implementations reading the rule the same way, and the third differing
by 136 points, is the shape of a defect rather than of a disagreement.

**Not fixed.** Aligning the runtime path on 120 would change the
confidence printed by every program that calls a function, which is a
decision about the language rather than a repair to it.

### 7.3 run.sh could not report a failing layer

Every layer in `run.sh` ran as

```
( cd DIR && test | tail -2 ) && pass "L" || fail "L"
```

The subshell's status is the pipeline's, which is `tail`'s, which is 0
whatever the test did. Measured: `vowels_test.py` patched to
`raise SystemExit(1)` was reported `PASSED`. The only failure the script
could ever surface was one where `cd` itself failed before the pipe —
which is why a missing `3-dsl-ruby/` showed up and a failing test would
not have. Fixed with `set -o pipefail`; the same deliberately-broken run
then reported `FAILED Vowels` and exit 1, with every other layer still
passing.

### 7.4 The tree carries two lineages, and the split is measurable

`5-runtime-java/differential.py` runs one corpus through both runners as
processes and compares value, exit code, refusing stage and binding
defect:

```
128 programs, 97 agreed, 31 diverged
```

Every one of the 31 is the same fork, not 31 separate bugs:

| cause | count |
|---|---|
| list literals (`cannot evaluate ListLit`) | 7 |
| `len` / `head` / `tail` (`never defined`) | 9 |
| `let ... in` is not v4.10 grammar | 9 |
| other parse splits | 6 |

The Java runtime and `7-forge/` implement `CORE.md`; `eval_ast`
implements a subset of `SEMANTICS.md`. Both sides pass their own suites
(98 and 81 assertions, 26 gate suites). A divergence here is a finding
about two lineages sharing a tree, and which one the project keeps is an
owner's decision, not something to settle by editing one side to match
the other.

### 7.5 A witness repeated was counted as a second witness

[EXAMPLE] multiplies uncertainty across independent witnesses:
`u_f = ((256-120)/256)^p`, then `c_f = floor(256 * (1 - u_f) * p/t)`.
Independence is the load-bearing word, and `ezrun`'s `--example` did
not check it. Measured, before the fix:

```
-x 'growth(100, 0) = 100'                          120/256
-x 'growth(100, 0) = 100'  (the same case twice)    183/256
-x 'growth(100, 0) = 100'  (the same case thrice)   217/256
```

Identical to what three *distinct* cases buy — real confidence for no
new evidence, which is the one thing T2 (corroboration creates nothing)
says the algebra must never permit. Examples are now keyed on the
call's own AST rendering, so `f(1,2)` and `f( 1 , 2 )` are correctly one
witness and `f(1)` and `f(2)` are correctly two. The same call given two
different answers is refused outright rather than silently resolved:
evidence that contradicts itself is not evidence.

Fixing one runner and not the other would only have moved the defect, so
the Java runtime was mirrored in the same change — `Ast.render`, a
faithful re-rendering to sit beside `Ast.skeleton`, which deliberately
erases literal values and under which `f(1)` and `f(2)` are both
`CALL(K)`. Before the mirror the two split exactly here, which is what a
corpus is for:

| | python | java |
|---|---|---|
| the same case ×3 | 120/256 | **217/256** |
| one call, two answers | refused, exit 2 | **60/256, exit 0** |

Three cases were added to the differential corpus so it reaches this
ground: 128 programs, 97 agreed. The corpus had never reached it because
every evidence case in it was already distinct.

### 7.6 `ezrun` cannot run any file in `examples/`

Nine example programs, nine refusals, measured one by one:

| file | ezrun says |
|---|---|
| `*.ever` (5 files) | `Z(misbound) — cannot evaluate Show` |
| `largest.ezr`, `readings.ezr`, `trust.ezr` | `parse: unexpected let` |
| `sum.ezr` | `Z(misbound) — cannot evaluate ListLit` |

Not a fault in the runner: it is 7.4 seen from the directory listing.
The `.ever` examples are written in the v4.10 statement surface and the
`.ezr` examples in the forge's core, and `eval_ast` implements neither
in full. `examples/earned_trust.ever` was added as one program that sits
in the subset both lineages share, so it runs under `ezrun` and under
the Java runtime and they agree — which is also what makes it a usable
demonstration of [DEF], [EXAMPLE] and [ANCHOR] rather than a description
of one.

### 7.7 Every refusal was a solved equation with the answer thrown away

The confidence algebra runs forwards: given evidence, here is what a
result is worth; below the floor, or without a proven measure, refuse.
Every one of those refusals is computed from a rule that is just as
solvable the other way round, and the machinery was discarding the
solution at the moment it had it.

`Semantic._measure` searches the parameters for one that strictly
decreases. When it returns `None` it knows, at that instant, that `i`
went *up* by one and `n` never moved — and returns a bare `None`.
`confidence_from_examples(1, 1)` returns 120 and the caller compares it
to 128; the same monotone rule answers "one more witness" and nobody
asked. So the language could say what it would not do, and never what
would make it willing.

Both directions now exist and are the same rule:

| forwards | backwards |
|---|---|
| `confidence_from_examples(p, t)` -> score | `witnesses_needed(p, t, target)` -> k |
| `Semantic._measure(fn)` -> name or None | `Semantic.movements(fn)` -> how each moves |

Nothing is inverted analytically because nothing needs to be: the
forward rule is monotone in k and saturates one short of CERTAIN, so
walking k up from 0 finds the least sufficient k or establishes there is
none. A failure already recorded cannot be withdrawn, so the answer
accounts for it — 1 of 9 needs eight more, not one.

Measured, following the language's own instructions:

```
$ ezrun fact.ever -d 3 --call 'fact(20)'
Z(unbounded) — depth ceiling 3 exceeded
       to lift it: fact decreases n in every self-call, so it can be
       anchored -- but anchoring needs the execute floor first, and it
       sits at 120/256. 2 more passing Examples clears 128, then -a fact

$ ... -x 'fact(1) = 1' -x 'fact(2) = 2'
Z(unbounded) — depth ceiling 3 exceeded
       to lift it: fact decreases n in every self-call and sits at
       183/256, above the floor. Pass -a fact to buy the depth

$ ... -x 'fact(1) = 1' -x 'fact(2) = 2' -a fact
2432902008176640000  @ 183/256                               exit 0
```

Three steps, each one the refusal naming its own cure, ending in the
answer. Mirrored in the Java runtime in the same change (`Laws
.witnessesNeeded`, `Semantic.movements`, `Ezr.lift`) and guarded by four
differential cases, so the two runners cannot drift on *which*
requirement they name.

A refusal with no cure stays silent. `1 / 0` gets no suggestion, because
no evidence makes dividing by zero work and inventing one would be worse
than saying nothing.

### 7.8 `weekly_sales.ever` has never computed its total, for a reason its own comment denies

v4.10's shipped example says its summing function is "(anchored, so it
isn't capped at 3 levels)". It is not anchored. `sum_from(xs, i)`
recurses on `i + 1`, and anchoring needs a parameter that strictly
*decreases*, so it stays at floor(pi) = 3 and a five-element list
overruns it.

The program reports `total = z [0/256]`, which reads as the intended
lesson — one `z` reading poisons the sum. Measured with that reading
replaced by a number:

```
let thu = 500        (420 + 610 + 380 + 500 + 705 = 2615)
total = z [0/256]
```

Still `z`. The `z` was never about the missing reading. Counting the
other way round is the whole fix:

```
def up(a, i, n) = if i >= n then 0 else a[i] + up(a, i + 1, n)
def down(a, i)  = if i < 0 then 0 else a[i] + down(a, i - 1)

up(xs, 0, 6)   ->  z [0/256]
down(xs, 5)    ->  63 [256/256]
```

**Not fixed** — it is a v4.10 example and rewriting it is the owner's
call. `examples/readings.ever` counts down and says why in a comment,
and 7.7's guidance names the parameter that went the wrong way when
asked through `ezrun`.

### 7.9 One rule, four languages, two implementations

The standing rule is that whatever is written in Python is written in
every language the system implements. Measured against the tree, it had
already rotted:

| piece | C | Python | Ruby | Java |
|---|:-:|:-:|:-:|:-:|
| `excel` / corroboration | yes | yes | yes | yes |
| `from_examples` — the [EXAMPLE] ladder | **no** | yes | **no** | yes |
| `witnesses_needed` — its inverse | **no** | yes | **no** | yes |
| `movements` — the measure inversion | n/a | yes | n/a | yes |

Nothing reported it. Three pieces of the confidence algebra lived in two
of four implementations and the gate was green the whole time, because
every suite checks its own language against itself.

C and Ruby now carry both arithmetic pieces, and all four produce the
identical ladder and the identical inverse:

```
p of p     0   1    2    3    4    5    6
           0 120  183  217  235  245  250
2 of 3   122
witnesses needed at the floor, from (0,0) (1,1) (2,3) (1,9):  2  1  1  8
```

`tests/algebra_parity.py` runs those vectors through all four as
processes and fails the gate on any disagreement — proven by changing
Ruby's intake constant from 120 to 128 and watching it report the split.
It is in `run_all.py` and in `run.sh`.

`movements` is marked n/a rather than missing: it needs an AST with call
nodes. Ruby is a DSL with no parser, and C's `measure` is structural
metrics (`ev_node_measure` fills size and depth) — C has no termination
measure and no anchoring at all, which `CLAUDE.md` already said. A gap
with a reason is not the same as a gap.

### 7.10 `E_INTAKE` was defined five times

Found while giving C the ladder, which needed the constant: `E_INTAKE`
was not in `tapestry.h` at all. It was `#define`d, `#ifndef`-guarded, in
`form.c`, `form_lower.c`, `tac.c`, `kitchen_sink.c` and `tac_test.c` —
five copies of 120, in a language where the other eight scale constants
all live in the header. Three of those files did not include
`tapestry.h`, so the guards were not even redundant; they were the only
definition each file had.

Nothing would have caught a drift. The guards mean a file that disagreed
would compile silently and quietly enter its values at a different floor.

Now declared once, in `tapestry.h` beside `E_EXECUTE_FLOOR`, and the five
local copies are gone. Verified: `kitchen_sink` 573 assertions / 31
suites, `tac_test` 56 assertions, no new compiler warnings (the two that
remain are pre-existing and in `ev_test.h`).
