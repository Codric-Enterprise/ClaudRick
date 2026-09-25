# Accord semantics — v0.7

What an Accord program means. `GRAMMAR.ebnf` says what it can say.
`core.py` is the implementation, and every rule below names the function
that carries it out. `build.py` copies those same functions into each
built module, so the interpreter and the built code share one
definition.

Rules marked **ezr** are taken from `ezr/SEMANTICS.md` (section cited)
or from `ezr/CORE.md`. Rules marked **Accord** are this language's own.
None of them is implied by ezr, so each is labelled.

## 1. Values

A value travels as a **thread**, `⟨v, c⟩`: a value `v` and a trust `c`
in `0..256`. **Z** is the void thread, `⟨none, 0⟩`, and it carries a
reason. Each reason begins with one of three words (**ezr** §3.3):

| Reason | Means |
|---|---|
| `misbound` | a value of the wrong kind, a bound crossed, division or modulo by zero |
| `unbound` | a name, a function or an element that is not there (the first of the empty list) |
| `unbounded` | a measure that did not shrink, or a call chain `DEPTH_LIMIT` (256) deep |

Types are closed: `Int`, `Float`, `Text`, `Bool`, and `List of T`.
`Int` is bounded at ±2^53, and any `Int` past the bound is `misbound`
(**Accord**, R3: past 2^53, ezr's Python and Java runtimes disagree).
A `Bool` is never a number, at any depth: `true` is not `1`, and `[1]`
is not `[true]` (`equal`).

## 2. Trust

| Rule | Meaning | Source | In `core.py` |
|---|---|---|---|
| literal | a written value is `⟨v, 120⟩` | **ezr** §3.1 [LIT] | `const` |
| admit | a value entering a parameter or `Let` declared `trusted d` is `⟨v, min(c, d)⟩`, and is `misbound` if it is not of the declared type | **Accord**: a declaration is a ceiling | `_bind`, `_admit` |
| chain | an operation's result has the `min` of its inputs' trust | **ezr** §2.1 | `_binop` |
| list | `the list of a, b` has the `min` of its elements; one Z element makes the list Z; the empty list is a literal (120) | **ezr** CORE §1.2 | `_list` |
| builtin | `length`, `first` and `rest` answer at the **list's** trust; `first`/`rest` of the empty list is `unbound` | **ezr** CORE §1.2 | `_builtin` |
| path | every condition passed on the way to an `Answer` caps it: the answer is `min(answer, conditions…)`, and only the chosen arm runs | **ezr** §5.1 [IF-T] | `br`, `_answer` |
| void | Z is checked before any operation and passes through unchanged | **ezr** §3.3 | every op |

## 3. Operators

| Accord | Op | Takes | Answers |
|---|---|---|---|
| `a plus b` | `+` | two numbers; two Texts; two Lists | the sum (bounded, as below); the Texts joined; the Lists joined, left then right (**Accord**: ezr's `Eval.java` refuses list joining. This extends its Text rule.) |
| `a minus b`, `a times b` | `-` `*` | two numbers | an `Int` result past ±2^53 is `misbound` |
| `a divided by b` | `/` | two numbers | always a `Float`; by zero is `misbound` |
| `a modulo b` | `%` | two `Int`s | **Accord**: `a − b·⌊a/b⌋`, so the answer has the divisor's sign (`negative 7 modulo 3` is 2, `7 modulo negative 3` is −2); by zero is `misbound`; a `Float` is `misbound` |
| `is equal to`, `is not equal to` | `==` `!=` | two numbers, or two values of one kind | strict at every depth (`equal`) |
| `is less than`, `greater than`, `at least`, `at most` | `<` `>` `<=` `>=` | two numbers or two Texts | anything else is `misbound` |
| `negative x` | — | a number | written `0 minus x`; a negative literal is folded |

The chain rule sets the trust of every result above.

## 4. Logic

The three rules below are all **Accord**. ezr has no `and`, `or` or `not`.
Each one is a decision, so it is lazy for the same reason [IF-T] is.

| Accord | Rule |
|---|---|
| `a and b` | `a` runs first. If it is `false`, the answer is `a` itself and `b` **never runs**. Otherwise `b` runs, and the answer is `⟨b, min(c_a, c_b)⟩` |
| `a or b` | the same, stopping when `a` is `true` |
| `not a` | `⟨¬a, c_a⟩` |

- **The side that is skipped never counts.** It does not run, so it
  cannot fail, and its trust does not enter the answer. `false and x`
  answers at the trust of that `false`, however little `x` is trusted.
  This is [IF-T] read as `if a then b else a`. The "else" arm is `a`
  itself, which is already decided, so there is no new literal and no
  120 cap.
- Every side that runs must be a `Bool`. Anything else is `misbound`,
  and Z passes through (`_truth`).
- Coverage (§7) treats each side of `and`/`or` as a decision.

## 5. Functions and calls

On entry (`_enter`), in this order: a call chain `DEPTH_LIMIT` deep is
`unbounded`; each argument is admitted (§2); and a recursive call's
measure must satisfy `0 ≤ m < m_caller`, or the call is `unbounded`.
The measure of an `Int` is its value, and of a `List` its length
(`_size`). `Make sure x is not void.` answers Z at once if `x` is Z.

A call to **another** function of the program answers at most that
function's earned trust: `⟨v, min(c, earned_f)⟩` (**ezr** §4.3 [APP],
`_cap`). A function's own answers are capped the same way when it is
applied from outside (`apply`, `apply_program`). They are **not**
capped while its own Checks are run, because that is how its trust is
earned.

## 6. TAC

Every function lowers to three-address code (`lower`). The interpreter
(`run`) and the builder (`build.py`) both work from it, never from the
tree.

| Instruction | Does |
|---|---|
| `fn name T`, `param x T d`, `measure m` | the signature |
| `const t kind v`, `load t x` | a literal at 120; a bound name |
| `bin t op a b`, `list t items`, `builtin t f a` | §2, §3 |
| `call t f args` | §5 |
| `require not_void x`, `let x T d a` | R2; admit (§2) |
| `not t a` | §4 |
| `short t op a L` … `join t op a b` … `mark L` | §4: `short` decides from `a` and jumps to `L`, or falls into the instructions for `b`; `join` combines |
| `br c Lt Le`, `label L` | a decision; both arms end in `ret` |
| `ret a` | answer, capped by the path (§2) |

A TAC listing's SHA-256 (`tac_hash`) identifies the function a built
module was made from.

## 7. Acceptance

A program is verified helpers first (`verify_program`). If a helper is
refused, every caller of it is refused at stage `depends`. Functions
that call each other in a cycle are refused (R5), because a measure
only proves that self-recursion stops. Each function goes through five
stages, and the first refusal wins:

1. **check**: R1–R5 (`check`).
2. **checks**: every Check runs from literal arguments (trust 120) and
   must give its value and its trust exactly (R4).
3. **coverage** (R6, **Accord**): across all the Checks, including the
   recursive calls they make, every comparison has been both true and
   false, and every ordering comparison has run with its sides equal.
   Every `If` whose condition is not itself a comparison, and every
   side of `and`/`or` that is not a comparison, has been both `true` and
   `false`. A side that is a comparison is covered by that comparison's
   own entry.
4. **earned**: `earned(p, t) = min(⌊256 · (1 − (136/256)^p) · p/t⌋, 255)`
   (**ezr** §4.2). All Checks hold at this stage, so `p = t`, which
   gives 1 → 120, 2 → 183, 3 → 217, 4 → 235.
5. **floor**: a function earning less than 128 is refused (**ezr** §0,
   `E_EXECUTE_FLOOR`). One Check is never enough.

## 8. Build

`accord build` turns an accepted program into one Python module
(`build.py`). The module's contract:

- It holds the functions §1–§5 name (`Thread`, `Z`, `_admit`, `_binop`,
  `_list`, `_short`, `_join`, `_not`, `_cap`, `_enter`, …), copied from
  `core.py`'s source rather than rewritten. It imports only
  `dataclasses`.
- Each function's TAC becomes structured Python: `br` becomes
  `if`/`else`, and `short`…`join` becomes an `if` around the second
  side.
- `f(*values)` returns the answer, and `trusted(name, *values,
  trust=120)` returns `(answer, trust)`. Both cap the answer at `f`'s
  earned trust, and both raise `Refused(reason)` rather than return Z.
  Python lists are accepted as Accord lists.
- Before the module is handed back, every Check runs through it twice,
  at trust 120 and at 256, and must match the interpreter's value, trust
  and reason exactly. The public `trusted` must match `apply_program`,
  and the module's table of arities and earned trusts must match the
  verification. A module that disagrees is not written.

## 9. Not yet

[IF-Z] and [IF-AGREE] (**ezr** §5.2), records, loops, indexing, I/O,
higher-order functions, mutual recursion. Trust is an ordering, not a
calibrated probability. That is ezr's own largest open claim, and
Accord inherits it.
