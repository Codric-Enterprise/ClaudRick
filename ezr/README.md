# EZR

A language where every value carries **how much it is trusted**.

A binding does not just hold `7`. It holds `7` at some confidence out of
256, in some state, with a record of why it is trusted that much — and
nothing executes below a stated floor. Uncertainty is not a comment or
a convention here; it is part of the value, and it propagates through
every operation by rules that are written down and tested.

```ezr
def fact(n) = if n <= 1 then 1 else n * fact(n - 1)
```

Unanchored, that function is capped at depth ⌊π⌋ = 3 — it can compute
`fact(3)` and refuses `fact(8)`, because confidence is evidence about
*correctness* and correctness is not termination. Give it three passing
Examples and it earns 217/256. Anchor it with a decreasing measure and
the ceiling lifts: `fact(100)` computes, and every result comes back at
217/256, floored by the function that produced it.

---

## Running it in VS Code

Open this folder as the workspace root. Then **⇧⌘B** (or **Ctrl+Shift+B**)
runs the default build task, which verifies all twelve layers.

Everything else is in the command palette under **Tasks: Run Task**:

| Task | What it does |
|---|---|
| **verify everything** | All twelve layers — C, C++, Python, Ruby, SQL, forge |
| **forge tests** | Layer 7 alone: 61 assertions over all sixteen front ends |
| **forge — converge** | Run until nothing is left to settle |
| **forge — exploration cycles** | N cycles at fixed budget, rotating fuzz depth |
| **re-emit GRAMMAR.ebnf** | Regenerate the grammar from the parser's own rules |
| **run the pipeline demo** | Lexer → parser → semantic pass → execution |
| **serve the live interpreter** | Then open `http://localhost:8088/ezr-live.html` |

Three debug configurations are set up too (**F5**), including one that
debugs whichever Python file you have open.

### Why `.vscode/settings.json` sets `extraPaths`

Each numbered directory is its own toolchain, and the Python layers
import their siblings directly — `from ezr import E, State`. That
resolves at runtime because the working directory is that layer, but
Pylance analyses from the workspace root and would mark every one of
those imports unresolved. `python.analysis.extraPaths` tells it where
to look. The code is fine without it; only the editor needs telling.

### From a terminal instead

```bash
./run.sh                                  # everything, 12 layers
cd 7-forge && python3 forge_test.py       # the forge alone
docker compose run --rm verify            # everything, in a container
```

`run.sh` skips any layer whose toolchain is missing rather than
failing, so it is useful even without gcc or ruby installed. The
container image verifies itself at build time.

---

## The layers

Each directory is a distinct language and toolchain, and they do not
bleed into each other.

| | |
|---|---|
| `0-atom-c` | the atom — the value that carries its own trust |
| `1-phase-cpp` | the phase engine |
| `2-interpreter-python` | lexer, parser, semantic pass, evaluator, the laws, the auditor |
| `3-dsl-ruby` | the DSL surface |
| `4-archive-sql` | the archive — nothing is deleted, only superseded |
| `5-runtime-java` | reserved; not yet implemented |
| `6-interface-html` | the live interpreter, in a browser |
| `7-forge` | twenty front ends, run against each other; generates a parser and repairs itself |

## Where to start reading

1. **`CORE.md`** — the core the forge settled on, and who settled each
   question. Start here.
2. **`SEMANTICS.md`** — the operational semantics. Every rule is
   implemented and exercised; where the spec and the implementation
   disagree, the spec is wrong and gets fixed.
3. **`7-forge/GRAMMAR.ebnf`** — the grammar, emitted from the chart
   parser's own rule table so it cannot drift from the code.
4. **`VOWELS.md`** — the operator families, and the self-generating
   loop.
5. **`7-forge/README.md`** — how sixteen front ends get used to find
   out what the language never actually specified.

## A note on the name

The language is **EZR**. In code it is `ezr` — module names, the
`Lang.EZR` tag, `compile_ezr`, `EzrError`. It was called Ever through
V3.0, and the documents describe that history in the past tense where
it is load-bearing (the reserved-word finding in `CORE.md`, for one).

---

## What is verified

| | |
|---|---|
| Layers passing | **15 / 15** |
| Forge assertions | **81** |
| Physics assertions | **56** |
| Pipeline assertions | **87** |
| Programs fuzzed | **520,600** over 61 generations, 60 clean |
| Front ends agreeing | **20** (4 lexers × 5 parsers — one of them generated) |
| Counterexamples carried | 46, each one permanent |

Convergence is a statement about a search, not a proof. No
counterexample was found; that is not the same as none existing, and
`CORE.md` says so at more length.

*Codric Enterprise*
