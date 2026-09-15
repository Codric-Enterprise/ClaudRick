# The core lineage (`.ezr`)

These four programs are **not** written in the language that
`ever run` implements. They are written in the core the forge settled
on (`../../CORE.md`), which the Java runtime implements.

Run them with the Java runtime:

```bash
cd ../..            # ezr/
5-runtime-java/build.sh
5-runtime-java/ezr examples/core-lineage/trust.ezr
```

Measured, all four:

| file | output |
|---|---|
| `trust.ezr` | `big  @ 120/256` (twice) |
| `largest.ezr` | `42  @ 120/256` |
| `readings.ezr` | `6  @ 256/256`, `63  @ 120/256` |
| `sum.ezr` | `15  @ 120/256` |

They will **not** run under `ever run` or `ezrun.py`. Three of them use
`let ... in`, which is not v4.10 grammar; `sum.ezr` uses a list literal,
which `syntax.py`'s `eval_ast` returns `Z("cannot evaluate ListLit")`
for. That is not a bug in either runner — it is the fork that
`5-runtime-java/differential.py` reports as 27 divergences over 124
programs, and it is an open decision recorded in `../../FINDINGS.md`.

If you want the language this project leads with, use `../` instead.
