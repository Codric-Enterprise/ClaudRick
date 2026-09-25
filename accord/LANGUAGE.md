# Accord — v0.7

**One language for a person and an AI to write one program together.**

You write what you want: the header, how far you trust each input, and
the Checks. The AI writes the body. The body is a claim, and your Checks
are its witnesses. Accord runs the body only after the Checks hold,
after they have tried every decision it makes, and once they have
earned enough trust. Each refusal quotes your own program back to you.

```
cd accord
python3 accord_test.py                                  # the gate: 186 assertions
python3 finish.py                                       # the gate and everything around it
python3 accord.py check examples/classify.accord        # verify a program
python3 accord.py run examples/classify.accord 200      # run it, if accepted
python3 accord.py tac examples/fact.accord              # the compiled TAC
python3 accord.py build examples/stats.accord --out stats.py   # a standalone Python module
python3 accord.py fill examples/clamp.intent.accord     # you write intent, Claude writes the body
python3 accord.py run examples/stats.accord --fn mean the list of 1, 2 and 3   # a program
```

## One program, two authors

```
# You write the header, the trust you give each input, and the Checks.
# The AI writes the body. It is a claim until your Checks witness it.
To classify given signal, answering a Text:                    ← you
  signal is a Float, trusted 100 of 256.                        ← you
  It never repeats.                                             ← the AI
  Make sure signal is not void.                                 ← the AI
  Let threshold be a Float, trusted 256 of 256, equal to 128.   ← the AI
  If the signal is greater than the threshold:                  ← the AI
    Answer "Certain".                                           ← the AI
  Otherwise:                                                    ← the AI
    Answer "Uncertain".                                         ← the AI
Check: classify of 200 gives "Certain", trusted 100.            ← you
Check: classify of 50 gives "Uncertain", trusted 100.           ← you
Check: classify of 128 gives "Uncertain", trusted 100.          ← you
```

```
$ python3 accord.py check examples/classify.accord
accepted: classify
  3 Checks hold, so its answers are trusted at most 217 of 256
  every decision was tried both ways, and every comparison at its edge
```

Suppose the AI writes `at least` where you meant `greater than`. Your
edge Check catches it, and you get the reason in your own words:

```
refused: classify does not do what its Checks say
  classify of 128 should give "Uncertain", trusted 100; it gave "Certain", trusted 100
```

Without that third Check, Accord would not accept the program at all.
It asks the question you had not answered:

```
refused: the Checks leave part of classify untried; add a Check for each
  no Check tries signal equal to threshold, the edge of 'signal is greater than threshold'
```

## Programs: several functions

A file can hold several functions (`examples/stats.accord`). Each has its
own header, trust lines, body and Checks, and they call each other by
name, as `total of xs`.

- **Each function is witnessed by its own Checks, helpers first.** Its
  coverage (R6), floor and earned trust are its own. A caller's Checks
  never count toward a helper's coverage, and a caller does not have to
  cover its helper's decisions.
- **A caller is refused when anything it uses was refused**, and the
  refusal names the helper: `mean uses total, which was refused`.
- **An answer is capped by every function it passed through.** A call
  answers at no more than the helper's earned trust (`SEMANTICS.md` §4.3,
  applied to each call).
- **Functions may not call each other in a cycle.** A measure proves only
  that a function calling *itself* stops, so mutual recursion is refused
  (R5). A call to an undefined function, a call with the wrong number of
  arguments, and two functions with the same name are refused (R3).
- `run FILE --fn NAME args` runs one function. The default is the last
  one in the file.

`fill` handles programs too. You write every function's header, trust
lines and Checks; Claude replies with one block per function, labelled
` ```accord NAME `; a missing, unknown or unlabelled body is sent back.

## Filling a body with Claude: `fill`

You write only your part: the header, one trust line per parameter, and
the Checks (`examples/clamp.intent.accord`). Then:

```
python3 accord.py fill examples/clamp.intent.accord --out clamp.accord
python3 accord.py fill examples/clamp.intent.accord --fast        # Opus 5 fast mode
```

`fill` is headless. The program goes to stdout (or `--out`), progress to
stderr, and the exit code says who acts next:

| Exit | Meaning |
|---|---|
| 0 | accepted: the body satisfies your Checks, and they cover it |
| 1 | Claude could not satisfy your Checks within `--attempts` (default 4) |
| 2 | usage |
| 3 | environment: no SDK, no credentials, or the API refused the request |
| 4 | **your turn**: your Checks leave a decision untried, or earn too little trust |

The loop:

1. It sends Claude a card describing the language, plus your part verbatim.
2. It takes back only a body.
3. **It assembles the program itself**, from your exact text plus that body, so your Checks cannot be edited by the AI. A reply containing a header or a `Check:` line is refused.
4. A body that is wrong (it doesn't parse, breaks R1–R5, or fails a Check) goes back to Claude with the refusal in Accord's words, and Claude tries again.
5. A coverage or floor refusal is never sent to Claude, because only you can add Checks. It stops with exit 4 and asks you the question.

The request uses `claude-opus-5` (change it with `--model`), adaptive
thinking, and server-side refusal fallbacks. `--fast` adds fast mode and
falls back to the standard speed on a rate limit. `fill` needs the
`anthropic` SDK and a credential (`ANTHROPIC_API_KEY` or `ant auth
login`). Nothing else in Accord does: the gate tests `fill` against a
scripted stand-in and passes with the SDK absent.

Verified live once, by hand: `fill examples/clamp.intent.accord --fast`
sent the header, trust lines and five Checks to Claude, which returned
only a body (a two-level `If`/`Otherwise` clamp). `fill` assembled the
program and Accord accepted it on attempt 1, trust 245 of 256. The
saved program was then re-checked and re-run independently of `fill`,
on arguments outside its Checks (`clamp of negative 3 and 0 and 10`
gave `0`; `clamp of 12 and 0 and 10` gave `10`), confirming `fill`'s own
verdict rather than trusting it. This was a manual run against a real
key, not a CI step — CI still has no SDK and no key, so this is not
re-verified automatically.

## Building: `build`

```
python3 accord.py build examples/leap.accord --out leap.py
python3 -c "import leap; print(leap.leap(2024), leap.trusted('leap', 1900))"
# True (False, 120)
```

`build` compiles an accepted program's TAC into one Python module that
imports nothing from Accord. Its semantics are `core.py`'s own
functions, copied in by source. Before the module is written, every
Check runs through it at trust 120 and again at 256, and it must give
the interpreter's value, trust and reason exactly. A program that was
refused does not build, and neither does a module that disagrees with
the interpreter (exit 1). `f(*values)` returns the answer, and
`trusted(name, *values)` returns `(answer, trust)`. Both raise
`Refused` instead of returning void. `SEMANTICS.md` §8 gives the full
contract.

## How a program is accepted

Five stages, in order. The first refusal wins.

| Stage | Refused when | Source |
|---|---|---|
| parse | a sentence is not Accord | this file |
| rules | R1–R5 below are broken | the checker in `core.py` |
| checks | any Check fails, on value or on trust | R4 |
| coverage | a decision was never tried both ways, or an ordering comparison never at its edge | R6, Accord's own |
| floor | the Checks earn less than 128 | `SEMANTICS.md` §0; ezr's `E_EXECUTE_FLOOR` |

**Trust is earned, and the rule is ezr's.** `SEMANTICS.md` §4.1: "A
definition is a claim, not a verification." It begins at 120. §4.2:
each passing Check is an independent witness at intake strength, and
the witnesses corroborate:

| Checks held | Trust earned | |
|---|---|---|
| 1 of 1 | 120 | below the floor: one case proves nothing |
| 2 of 2 | 183 | runs |
| 3 of 3 | 217 | |
| 4 of 4 | 235 | |

§4.3: an answer is never more trusted than the function that gave it,
so `run` caps every answer at the trust its Checks earned. Arguments you
type in enter at literal trust 120, which is already below any accepted
program's trust, so the cap bites only when inputs arrive trusted
higher than that.

## Six rules

| Rule | Says | Where it came from |
|---|---|---|
| **R1** | every parameter and binding states its trust (0–256) | behaviour that depended on an unstated default: awesome-llm-apps `0c49942`, git output decoded as cp1252 on Windows |
| **R2** | a parameter is used only after `Make sure … is not void` | ezr landmine: Z must be checked *before* arithmetic |
| **R3** | types are closed (`Int Float Text Bool`, and `List of` any of them); `Int` is bounded at ±2^53 | ezr `differential.py`: Python's `int` and Java's `double` disagree past 2^53 |
| **R4** | there are Checks, and they are run, not asserted | a test that simulated its subject and could not fail |
| **R5** | every path answers; recursion names an `Int` or `List` measure that must shrink | ezr `FINDINGS.md` §3: 84% of defects were *unbounded* |
| **R6** | the Checks try every decision both ways, and every ordering comparison at its edge | a boundary slip (`>` written as `>=`) that example Checks away from the edge never see |

R6 counts everything a Check executes, including recursive calls. A
Check on `the list of 1, 2 and 3` reaches the empty-list case on its
way down, so that case counts as tried.

Every rule has tests that must be **refused**, and the gate was
mutation-checked. Each of these sabotages turns it red: the §4.2
formula, the floor, the coverage rule's edges, sides and Bool
decisions, the trace through recursion, the answer cap, ignoring a
failed Check, running a refused program, the chain rule, literal trust,
R2, R4, R5, the measure, the Int bound, `require`, the depth limit,
division by zero, and each list rule below.

## Trust semantics, inherited from ezr rather than invented

From `ezr/SEMANTICS.md`, unchanged:

- A written literal enters at **120** (§3.1 [LIT]), never 256.
- **Chain**: a result is no more trusted than its weakest input, `min` (§2.1).
- A known condition is **lazy**: only the chosen arm runs, and the answer
  is `min(condition, arm)` (§5.1 [IF-T]). A decision is never more
  trusted than what it was decided on.
- **Z** (void, trust 0) is checked before arithmetic and carries its reason;
  division by zero and type mismatch are `misbound` (§3.3).
- A function earns trust from its examples (§4.2) and caps its answers (§4.3).

Accord's own additions, stated as such:

- A declared trust is a **ceiling** on what enters a parameter or binding.
- `Int` past ±2^53 is `misbound`, never rounded.
- A recursive call whose measure does not strictly decrease toward 0 is
  `unbounded`. A call chain 256 deep is also `unbounded`. That is an
  implementation limit, so the answer is Z rather than a host stack overflow.
- R6, coverage.
- `and`, `or` and `not` (ezr has none). A side that is skipped never
  runs and never counts, so `false and x` answers at the trust of that
  `false`. When both sides run, the answer takes the `min`. Each side is
  a decision that R6 requires the Checks to try both ways.
- `modulo` takes whole numbers, and its answer has the divisor's sign.

`SEMANTICS.md` states every rule, with the source of each and the
function that carries it out.

## The syntax: one sentence form per construct

| Construct | Accord |
|---|---|
| header | `To total given xs, answering an Int:` |
| trust (R1) | `xs is a List of Int, trusted 256 of 256.` |
| measure (R5) | `It never repeats.` or `It shrinks by xs.` |
| check before use (R2) | `Make sure xs is not void.` |
| binding | `Let limit be an Int, trusted 256 of 256, equal to 10.` |
| decision | `If … :` then `Otherwise:`, and both must answer |
| answer | `Answer the first of xs plus total of the rest of xs.` |
| Check | `Check: total of the list of 1, 2 and 3 gives 6, trusted 120.` |
| comparison | `is greater than`, `is less than`, `is at least`, `is at most`, `is equal to`, `is not equal to` |
| logic | `a and b`, `a or b`, `not a`: Bools only, and a side that is skipped never runs |
| arithmetic | `plus`, `minus`, `times`, `divided by`, `modulo`, `negative 3` |
| lists | `the list of 1, 2 and 3`, `the empty list`, `a List of Int` |
| builtins | `the length of xs`, `the first of xs`, `the rest of xs` |
| call | `total of xs`; more arguments with `and`: `f of a and b` |

`the list of …` takes every `, item` and `and item` that follows, so a
second argument after a list needs parentheses:
`f of (the list of 1 and 2) and 3`. A call takes every `and` too, so
`f of x and y` is `f` given two arguments; write `(f of x) and y` for
the conjunction. `or` binds looser than `and`, and `not` takes a whole
comparison: `not x is equal to 0`. The words listed in `GRAMMAR.ebnf`
are reserved, among them `list`, `empty`, `length`, `first`, `rest`,
`trusted`, `or` and `modulo`, so no function or parameter may use them
as a name. `GRAMMAR.ebnf` is the whole grammar.

## Lists

From ezr's `CORE.md` §1.2 and its Java runtime (`Eval.java`), unchanged:

- A list's trust is the `min` over its elements, and a Z element makes
  the whole list Z.
- `the length of`, `the first of` and `the rest of` answer with the
  **list's** trust.
- The first or the rest of the empty list is a refusal (`unbound`), not
  an exception and not a silent empty answer.

**One decision, recorded.** ezr's `CLAUDE.md` says indexing should read
an element's own trust. That rule belongs to ezr's statement surface,
where each element keeps its own trust. ezr's core keeps one trust for
the whole list, and Accord follows the core: the first of the rest of
`[a@100, b@120]` answers at 100, not 120. That is conservative, so it
never over-trusts. Revisit it if Accord ever gains indexing.

Accord's own list rules:

- A written empty list enters at 120, like any literal. A non-empty list
  takes the `min` of its elements.
- A recursive measure may be a `List`, measured by its length.
- Equality is strict at every depth: `[1]` is not equal to `[true]`.
- `plus` joins two lists, left then right, at the `min` of both sides'
  trust. **This departs from ezr**, whose `Eval.java` refuses it; it
  extends ezr's own Text rule. A list joined with a number or Text is
  refused, and so is a mixed result bound to a `List of Int`.

## What v0.7 does not do

- **Coverage is not correctness.** R6 makes the Checks try every decision
  and every edge. An arithmetic slip that crosses no decision, such as
  `plus 2` written for `plus 1`, is caught only if some Check's expected
  answer depends on it. Accord cannot tell which Checks you *should*
  have written. It can only refuse a program whose decisions you have
  not examined.
- Records, loops, modules, indexing, higher-order functions and I/O.
  Programs can have many functions, but they cannot call each other in
  a cycle.
- **[IF-Z] and [IF-AGREE]** (§5.2): a Z condition returns Z. No spans yet.
- Trust is an **ordering, not a calibrated probability**. That is
  `SEMANTICS.md`'s own largest open claim, and Accord inherits it.
- Roles are enforced only by `fill`, which assembles the program from
  your text and refuses a reply that touches it. A file edited by hand
  records no authorship.
- `fill` is tested in the gate only against a scripted stand-in. It has
  also been verified once, by hand, against the live API (see "Filling
  a body with Claude" above) — that run is not repeated automatically,
  since CI has no SDK and no key.

## Finishing a change: `finish`

`python3 finish.py` runs everything a change must pass, and exits 0
only if every step passes. CI's `languages` job runs the same command.
`--quick` leaves out the mutants.

| Step | Fails when |
|---|---|
| gate | `accord_test.py` fails; its tally is read back for the next step |
| no-sdk | the gate fails with `anthropic` unimportable, as it is in CI |
| counts | a document that states the gate's size (this file, `CLAUDE.md`, `ci.yml`) states a different number |
| examples | an example is refused, will not build, or its built module fails when run alone |
| mutants | a deliberate bug in `mutants.py` gets past the gate, or its text is no longer in the code (stale) |
| lint | `ruff check` or `ruff format --check` fails, or ruff is not installed |

It has been shown to fail on each of these: a drifted count, a broken
Check, a broken operator, a stale mutant, a surviving mutant, and a
missing ruff.

**What stays with a person:**

- **Whether the Checks are the right ones.** `finish` proves that the
  gate refuses the bugs listed in `mutants.py`. It cannot know which
  bugs are missing from that list. When you add a rule, add a mutant for
  it.
- **A surviving mutant.** It is either a gap in the gate or an
  equivalent change that means the same program. Only a reader can tell
  which. Fix the gate, or delete the mutant; never keep a survivor.
- **Opening and merging the PR.** The repo opens PRs only when asked.
- **`fill` against the live API.** It needs a key and costs money, so
  `finish` does not run it. It has been verified once by hand (see
  "Filling a body with Claude" above); the gate itself still uses a
  scripted stand-in, and CI has neither the SDK nor a key.

## Why there is one syntax, not two

v0.1–v0.3 made you write every program twice, once in a symbolic form
("Emit") and once in this form, and accepted a program only if the two
agreed. That is two languages, which is the thing Accord exists to
avoid. And when one author writes both versions, they agree with each
other and prove nothing. The one thing the second version really caught,
a boundary slip that examples miss, is what R6 now catches directly,
by asking you the question.

## Files

| | |
|---|---|
| `parse.py` | the syntax: reads Accord, and writes expressions and values back in it |
| `core.py` | the tree, the checker (R1–R5), lowering to TAC, the interpreter, and `verify`: Checks, coverage (R6), earned trust, the floor |
| `accord.py` | the `check`, `run`, `tac`, `build` and `fill` commands, and `explain`, which words each verdict |
| `build.py` | compiles an accepted program to a standalone Python module, and refuses one that disagrees with the interpreter |
| `GRAMMAR.ebnf` | the grammar; the gate holds it to `parse.py` |
| `SEMANTICS.md` | what a program means, rule by rule, each with its source and the code that carries it out |
| `fill.py` | the headless loop: your part, Claude's body, Accord's verdict; the only code that calls the API |
| `accord_test.py` | the gate: a plain script that reports its own tally, like `realm_test.py` |
| `finish.py` | the gate and everything around it, in one command, as CI runs it |
| `mutants.py` | the deliberate bugs the gate must catch |
| `examples/` | `classify`, `fact`, `total`, `reverse`, `leap` (`and`/`or`/`modulo`), `odd` (`not`); `stats`, a two-function program; and `clamp.intent`/`leap.intent`, a person's part awaiting `fill` |

`core.py` never imports `parse.py`, and the gate asserts it. The
semantics don't depend on the syntax, so a second syntax could never
quietly change what a program means.
