# Ever

A programming language where every value carries how much you can
trust it — and an unmeasured input poisons whatever it touches
instead of quietly becoming a plausible wrong number.

```
def sum_from(xs, i) = if i < 0 then 0 else xs[i] + sum_from(xs, i - 1)

let sales = [420, 610, 380, z, 705]   # Thursday was never recorded
ever total = sum_from(sales, 4)

show total
```
```
total = z [0/256]
```

Not 2115 with Thursday quietly skipped. The whole computation
correctly refuses to guess — and with a real Thursday number in place
of `z`, the same program correctly gives `2670`, not another `z`
hiding an unrelated architectural limit. Every claim in this README
was run, not just written down; see the bottom section.

## Try the idea in 30 seconds — no install of the language required

The same rule, as a plain Python library:

```bash
pip install ./everconf
```
```python
from everconf import C, UNKNOWN, mse

preds  = [C(0.9), C(0.2), C(0.6)]
actual = [C(1), C(0), UNKNOWN]        # one label never recorded

mse(preds, actual)   # UNKNOWN — not the mse of the two points you had
```

A model evaluated against partly-missing labels doesn't get to report
a loss number as if it saw the whole dataset. See
[`everconf/README.md`](everconf/README.md).

## Try the full language

```bash
pip install -e 2-interpreter-python
ever run examples/train_logistic.ever
```

That example trains a real 1D logistic regression by gradient descent
— sigmoid, mse, indexing, anchored recursion — checked bit-for-bit
against an independent from-scratch implementation. Make one training
label `z` and the entire trained weight correctly comes back unknown,
not a number quietly learned from the data that was there.

Five other examples in [`examples/`](examples/): a grade calculator, a
compound-interest projection, calling real compiled C code through
FFI (`sqrt`, `pow`, `sin` — actual `libm`, not reimplementations, and
capped at 120/256 trust because Ever can't audit what foreign code
did), and more.

## What's actually in here

- **The language** — parser, semantic pass, evaluator, REPL, CLI.
  [`2-interpreter-python/`](2-interpreter-python/README.md)
- **Five verified compile targets** — Go, Rust, R, Kotlin, JavaScript.
  Every one checked against its own real compiler, matched
  value-for-value and confidence-for-confidence against the
  reference. Not "should work" — compiled, run, diffed.
  [`2-interpreter-python/emit.py`](2-interpreter-python/emit.py)
- **`everconf`** — the confidence-value core, as a standalone Python
  library. [`everconf/`](everconf/README.md)
- **Edapt** — the same "forgive, don't guess" discipline pointed at
  Python, JavaScript, Go, Rust, and Java: fixes common mistakes,
  refuses to invent structure it can't verify.
  [`edapt/`](edapt/)
- **A native C runtime** — the original interpreter layer, C99,
  ASAN-clean. [`0-atom-c/`](0-atom-c/)

## What this is not

Not the first system to propagate uncertainty through computation —
NULL in SQL and NaN in floating point do the mechanically same thing,
and `Uncertain<T>` (Bornholt et al., Microsoft Research) and Julia's
`Measurements.jl` do it with real statistical rigor: distributions,
not a single int. Ever trades that rigor for a number anyone can read
at a glance, and takes the simplification further than the rigorous
versions bothered to: into recursion depth, into foreign function
calls, into training loops.

Not production-ready for anything that isn't a demonstration.

## Verification discipline

Every claim above is checked before it ships:
`python3 tests/run_all.py` (25/25), `python3 tests/test_backends.py`
(60/60 across five languages), `python3 tests/test_edapt.py` (32/32),
`pytest everconf/tests/` (47/47). Nothing in this README describes
behavior that wasn't run and confirmed.

Codric Enterprise · Ricky (Dreid) · 2026
