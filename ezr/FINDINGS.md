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

Verified exactly across the full grid: **1089 / 1089**.

That is the standard rule for combining independent evidence: the chance
both witnesses are wrong is the product of each being wrong. It was
derived here from first principles and landed on the correct formula.

### Three consequences that were never designed in

**Excel creates nothing.** Two witnesses agreeing does not manufacture
confidence. It multiplies two ignorances into a smaller one. The
confidence was already distributed across the witnesses; corroboration
only revealed it. Conservation holds.

**Z-contagion is not a rule — it is arithmetic.** `u = 1`, and
`1 × x = 1` for every x. Z is the absorbing element under multiplication.
Anything mixed with total ignorance yields total ignorance. This was
written into the language as a design decision; it turns out to be a
theorem.

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

| layer | assertions |
|---|---|
| 0 · C — the atom | 88 |
| 1 · C++ — the phase engine | 50 |
| 2 · Python — the interpreter | 81 |
| 4 · SQL — the archive | 56 |
| **total** | **275** |

Layer 3 (Ruby) is written and inspected clean at 228/256 by Ever's own
Ruby checker, but has not been executed — no Ruby toolchain in the build
container. It runs on macOS.

Layers 5 (Java) and 6 (HTML) are not yet ported to the v2 atom.

---

## 6. What is safe to claim

**Supported:**
- Excel is exactly multiplicative uncertainty combination (1089/1089)
- Z-contagion is a consequence of that algebra, not an imposed rule
- Certain is formally unreachable by combination at any strength
- Every finding classifies into five binding defects
- 275 assertions execute and pass across four layers
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
