# Accord — v0.2

A program is written twice: once in **Emit**, a dense surface an AI can
produce without ambiguity, and once in **Prose**, controlled English a
person can read and check. Two independent front ends parse them. The
program is accepted only if both produce **the same tree**, that tree
passes the checker, it lowers to **the same TAC** (compared by SHA-256),
and **every example actually runs** on that TAC and holds.

Where the two versions disagree, one of them says something the other
does not. That disagreement is the point: it is found before anything
runs.

```
cd accord
python3 accord_test.py                                          # the gate: 70 assertions
python3 accord.py agree examples/classify.emit examples/classify.prose
python3 accord.py tac examples/fact.prose                       # print the lowered TAC
```

## The same function, twice

```
def fact(n: Int [trust: 256]) -> Int          To fact given n, answering an Int:
  measure: n                                    n is an Int, trusted 256 of 256.
  require: not_void(n)                          It shrinks by n.
  if n <= 0:                                    Make sure n is not void.
    return 1                                    If n is at most 0:
  else:                                           Answer 1.
    return n * fact(n - 1)                      Otherwise:
example: fact(5) == 120 @ 120                     Answer n times fact of (n minus 1).
                                              Check: fact of 5 gives 120, trusted 120.
```

## Five rules, each from a failure that happened

| Rule | Says | Refused by | Where it came from |
|---|---|---|---|
| **R1** | every parameter and binding states its trust (0–256) | both parsers, then the checker | behaviour that depended on an unstated default: awesome-llm-apps `0c49942`, git output decoded as cp1252 on Windows |
| **R2** | a parameter is used only after a `require` checks it | the checker | ezr landmine: Z must be checked *before* arithmetic |
| **R3** | types are closed (`Int Float Text Bool`, and `List[T]` of any of them); `Int` is bounded at ±2^53 | the checker; the interpreter at runtime | ezr `differential.py`: Python's `int` and Java's `double` disagree past 2^53 |
| **R4** | at least one example; examples are executed, not asserted | the checker; `run_examples` | a test that simulated its subject and could not fail |
| **R5** | every path answers; recursion names an `Int` or `List` measure that must shrink | both parsers (if needs else), the checker, the interpreter | ezr `FINDINGS.md` §3: 84% of defects were *unbounded* |

Every rule has at least one test that must be **refused**, and the gate
was mutation-checked: sabotaging the chain rule, the branch rule, R2, R4,
R5, the measure, the Int bound, literal trust, `require`, the depth
limit, or division-by-zero each turns it red. The same holds for each
list rule below: empty `head`/`tail`, the trust of a list and of the
empty list, Z absorption, element types, the list measure, the builtins'
trust, strict equality, builtin arity and names, the trailing comma, and
Prose's `, trusted` lookahead.

## Trust semantics — inherited, not invented

From `ezr/SEMANTICS.md`, unchanged:

- A written literal enters at **120** (§3.1 [LIT]), never 256.
- **Chain**: a result is no more trusted than its weakest input, `min` (§2.1).
- A known condition is **lazy**: only the chosen arm runs, and the answer
  is `min(condition, arm)` (§5.1 [IF-T]). A decision is never more
  trusted than what it was decided on.
- **Z** (void, trust 0) is checked before arithmetic and carries its reason;
  division by zero and type mismatch are `misbound` (§3.3).

Accord's own additions, stated as such:

- A declared trust is a **ceiling** on what enters a parameter or binding.
- `Int` past ±2^53 is `misbound`, never rounded.
- A recursive call whose measure does not strictly decrease toward 0 is
  `unbounded`. A call chain 256 deep is also `unbounded`. That is an
  implementation limit, so the answer is Z rather than a host stack overflow.

## Lists

```
def total(xs: List[Int] [trust: 256]) -> Int    To total given xs, answering an Int:
  measure: xs                                     xs is a List of Int, trusted 256 of 256.
  require: not_void(xs)                           It shrinks by xs.
  if len(xs) == 0:                                Make sure xs is not void.
    return 0                                      If the length of xs is equal to 0:
  else:                                             Answer 0.
    return head(xs) + total(tail(xs))             Otherwise:
example: total([1, 2, 3]) == 6 @ 120                Answer the first of xs plus total of the rest of xs.
                                                Check: total of the list of 1, 2 and 3 gives 6, trusted 120.
```

| | Emit | Prose |
|---|---|---|
| type | `List[Int]`, `List[List[Int]]` | `a List of Int`, `a List of List of Int` |
| literal | `[1, 2, 3]`, `[]` | `the list of 1, 2 and 3`, `the empty list` |
| builtins | `len(xs)` `head(xs)` `tail(xs)` | `the length of xs`, `the first of xs`, `the rest of xs` |

From ezr's `CORE.md` §1.2 and its Java runtime (`Eval.java`), unchanged:

- The builtins are `len`, `head` and `tail`. Accord omits `show`
  because it has no output.
- A list's trust is the `min` over its elements (the chain rule applied
  to elements), and a Z element makes the whole list Z.
- `len`, `head` and `tail` answer with the **list's** trust.
- `head([])` and `tail([])` are refusals (`unbound`). They are neither
  exceptions nor a silent empty answer.
- No trailing comma (`CORE.md` ruling 7, consensus 16/16).

**One decision, recorded.** ezr's `CLAUDE.md` says indexing should
read an element's own trust, not the container's. That rule belongs to
the statement surface, where each element keeps its own trust. The
ratified core keeps one trust for the whole list, and Accord follows
the core: `head(tail([a@100, b@120]))` answers at 100, not 120. That is
conservative, so it never over-trusts. Revisit it if Accord ever gains
indexing.

Accord's own list rules, stated as such:

- A written `[]` enters at 120, like any literal. A non-empty list takes
  the `min` of its elements, with no literal floor.
- A recursive measure may be a `List` parameter. Its size is the list's
  length, and like an `Int` measure it must strictly decrease.
- Equality is strict at every depth: `[1] == [true]` is false.
- `+` does not join lists. Nothing in the core does, so v0.2 lists can
  be built from literals and taken apart, but not concatenated.
- Prose's list has one form: commas between items, and `and` before the
  last, with no comma before it. `the list of …` takes every `, item` and
  `and item` that follows, so a second argument after a list needs
  parentheses: `f of (the list of 1 and 2) and 3`.
- Prose reserves `list`, `empty`, `length`, `first`, `rest` and
  `trusted`. A function or parameter with one of those names parses in
  Emit and is refused in Prose, so the pair is refused, never silently
  split.

## What v0.2 leaves out, deliberately

- **[IF-Z] and [IF-AGREE]** (§5.2): a Z condition returns Z. No spans yet.
- **Corroboration** (§2.2): nothing in v0.1 combines independent evidence.
- One function per program, self-calls only; no records, loops, modules,
  or I/O.
- No way to build a list of computed length: no cons, concatenation, map
  or indexing.
- Trust is an **ordering, not a calibrated probability**. That is
  `SEMANTICS.md`'s own largest open claim, and Accord inherits it.

## Files

| | |
|---|---|
| `core.py` | the tree, the checker, lowering to TAC, the TAC interpreter |
| `emit.py` | Emit lexer and parser, which imports nothing from `prose.py` |
| `prose.py` | Prose lexer and parser, which imports nothing from `emit.py` |
| `accord.py` | the `agree` and `tac` commands |
| `accord_test.py` | the gate: a plain script that reports its own tally, like `realm_test.py` |
| `examples/` | each program as a `.emit` / `.prose` pair |

The two front ends share only `core.py`'s tree types. A defect in
`core.py` is therefore common to both and the agreement check cannot
catch it. That is why the checker and interpreter have their own
refusal tests.
