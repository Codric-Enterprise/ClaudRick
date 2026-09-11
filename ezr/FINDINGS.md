# EZR / Tapestry — Research Findings

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

The Third Law says absolute zero is unreachable in finite steps. EZR's Z
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

Layer 3 (Ruby) is written and inspected clean at 228/256 by EZR's own
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

## 7. What a second runtime found

Layer 5 is EZR implemented again, in Java. Three things surfaced that the
nine Python front ends could not have surfaced, because they share an
interpreter and therefore share its habits.

### A guard that could never fire

`2-interpreter-python/syntax.py` carried this check:

```python
if kind is T.STR and not text.endswith('"'):
    return toks, e_z("lex", f"unterminated string at line {line}",
                     Defect.UNBOUNDED)
```

Its regex was `"[^"\n]*"`, which only matches when a closing quote is
present. `text` therefore always ended with `"` and the condition was
never true. A lone `"` never matched as a string at all — it fell
through to "unexpected character" and came back **misbound**.

The forge had already ruled on this. `GRAMMAR.ebnf` records
`unterminated_string_defect = 'unbounded'`, settled by doctrine, and all
four forge lexers implement it:

| Implementation | `"never closed` |
|---|---|
| L1 regex-master | `unbounded` |
| L2 hand-rolled | `unbounded` |
| L3 DFA | `unbounded` |
| L4 trie | `unbounded` |
| Java (from the grammar) | `unbounded` |
| **`syntax.py` (the runner's lexer)** | **`misbound`** |

The ruling was never carried back into the lexer the runner uses. Writing
the sixth implementation from `GRAMMAR.ebnf` rather than from `syntax.py`
is what exposed it, and the differential harness reported it as a split
on the first run. Now fixed; six implementations agree.

**The general shape:** a settled question is only settled where somebody
applied it. The forge records rulings, and nothing was checking that the
production code had adopted them.

### Rendering was never specified

```
"hello"          -> hello        both runners
["a", "b"]       -> ['a', 'b']   python
["a", "b"]       -> [a, b]       java, before it was made to match
```

The same value renders two ways depending on nesting. That came from
formatting a list through CPython's `repr`, which quotes its elements —
inherited, not chosen, the same class of accident as `"ab" * 2` returning
`"abab"` until stage 3 started refusing it.

Arbitration **withholds**: no document specifies rendering, no law
settles it, and two implementations is below the ⌊π⌋ = 3 consensus
needs. So the incumbent stands, Java reproduces it, and the question is
recorded here rather than decided by whoever wrote the second runtime.

**Open.** Either answer is defensible — one keeps a value's rendering
independent of where it sits, the other keeps `["1"]` distinguishable
from `[1]`. What is not defensible is having both at once and calling it
specified.

### "Equivalently" was carrying a rounding convention

SEMANTICS.md §2.2 states `u(a⊕b) = u(a)×u(b)` and adds "Equivalently
`c = a + b − ⌊ab/256⌋`. Verified identical across the full grid:
1089/1089."

True — under the **ceiling**, and only under the ceiling:

| Reading of `256·(1−u_a·u_b)` | Cells agreeing, of 1089 |
|---|---|
| `floor` | 582 |
| `round` | 835 |
| **`ceil`** | **1089** |

`corroborate(120, 120)` is 183.75 exactly; the integer form gives 184.
The claim stands. The word "equivalently" was doing work that a reader
reaching for `floor` would get wrong on 507 cells, so the convention is
now pinned by an assertion in `RuntimeTest.java` instead of waiting to be
rediscovered.

### What the layer is checked against

| | |
|---|---|
| `RuntimeTest.java` | 98 assertions against SEMANTICS.md |
| `differential.py` | 108 programs through both runners as processes |
| Agreement | 108 of 108 on value, exit code, stage and defect |
| Wording | 12 cases differ in prose; not a divergence |

Agreement over a corpus is not a proof. It means no counterexample was
found where the corpus looked.
