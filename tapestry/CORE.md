# Ever — The Core

**Version 1.0 · Codric Enterprise · Ricky (Dreid) · 2026**

The language that sixteen independently derived front ends agree on.
Where they disagreed, this document records who settled it and on what
authority. Nothing here was decided by preference.

---

## 0. What this is, and what it is not

Ever V3.0 shipped a working front end and no specification of it.
`2-interpreter-python/syntax.py` was the lexer, the parser, and — by
default — the only statement of what the language accepted. That is
stable until somebody writes a second implementation, at which point
there is nothing to check it against.

So layer 7 wrote the second implementation, and the third, and the
fourth. Four scanners, four parsers, every pairing run over the same
corpus. **Sixteen front ends agreeing is evidence about the language.
One front end agreeing with itself is evidence about nothing** — which
is SEMANTICS.md 2.2's independence requirement applied to the front end
rather than to values.

This document is **not** a new language. Every rule below was already
implied by SEMANTICS.md or PIPELINE.md, or already implemented in
`abstract.py`. What the forge did was find the seven places where the
implication had never been written down, and write them down.

---

## 1. The grammar

Stated in full in [`7-forge/GRAMMAR.ebnf`](7-forge/GRAMMAR.ebnf), which
is **emitted from the chart parser's own rule table** rather than
typed. A hand-written grammar agrees with the code on the day it is
written; an emitted one cannot disagree.

```
program        = definitions | expression ;
definitions    = definition , { definition } ;
definition     = "def" , name , "(" , [ parameters ] , ")" , "=" , expression ;
parameters     = name , { "," , name } ;

expression     = conditional | comparison ;
conditional    = "if" , expression , "then" , expression , "else" , expression ;
comparison     = additive , [ compare-op , additive ] ;
additive       = additive , add-op , multiplicative | multiplicative ;
multiplicative = multiplicative , mul-op , unary | unary ;
unary          = "-" , unary | atom ;
atom           = number | string | "true" | "false"
               | "(" , expression , ")"
               | name , "(" , [ arguments ] , ")"
               | name ;
arguments      = expression , { "," , expression } ;
```

The additive and multiplicative rules are **left-recursive on
purpose**. Associativity is then a property of the grammar rather than
of a loop somebody wrote, and the chart parser can be asked whether the
grammar is ambiguous — which is how finding 5 below was caught.

This closes the first line of SEMANTICS.md section 7:

> | Formal grammar (EBNF) | parsing is regex-based |

### 1.1 Token kinds

The table nobody had written, now measured rather than asserted — every
kind below is one all four scanners assign.

| Kind | Members |
|---|---|
| `NUM` | a number |
| `STR` | a string |
| `NAME` | a name that is not a keyword |
| `KW` | `def` `else` `false` `if` `then` `true` |
| `CMP` | `<` `>` `<=` `>=` `==` `!=` |
| `OP` | `+` `-` `*` `/` |
| `EQ` | `=` |
| `LPAR` `RPAR` `COMMA` | `(` `)` `,` |
| `EOF` | end of input |

---

## 2. The seven rulings

Each was open, in the sense that independent implementations answered
differently or the answer existed nowhere. Each is now closed, with the
authority that closed it.

| # | Question | Ruling | Settled by |
|---|---|---|---|
| 1 | which kind carries a bare `<` | `CMP` | doctrine |
| 2 | defect for an unclosed string | `unbounded` | doctrine |
| 3 | which words are reserved | the six the grammar uses | doctrine |
| 4 | several definitions per text | yes | coverage gap |
| 5 | a trailing expression after them | no | law `unambiguous` |
| 6 | chained comparison `a < b < c` | no | doctrine |
| 7 | trailing comma in a list | no | consensus 16/16 |

### 2.1 Arbitration has an order, and a vote is not the top of it

1. **Doctrine.** SEMANTICS.md or PIPELINE.md already says. A vote
   cannot overturn a published document, so this tier runs before
   anybody is counted.
2. **Coverage.** Stage 4 demonstrably holds something stages 1–3 cannot
   express. **Consensus is blind to this**: all four front ends can
   agree, sincerely and unanimously, on a limitation that the rest of
   the language does not have, and a vote would then write that
   limitation into the specification.
3. **Finding.** One of the laws settles it. A law violation is evidence
   about the language, not about one implementation, so it outranks a
   vote among implementations that might share the defect.
4. **Consensus.** VOWELS.md's oracle, unchanged: at least ⌊π⌋ = 3
   agreeing and at least two thirds of those that answered.

Below all four it **withholds**. Inventing an answer there would teach
the corpus a fact nobody verified, which is the one thing the language
exists to prevent.

### 2.2 The rulings, in full

**1 — a bare `<` is `CMP`.** The four scanners split two-two before a
single test was written: the master-regex and trie scanners inherited
the incumbent's table, where `<` sits under `OP`; the hand scanner and
the DFA put it under `CMP`, because both decide `<` and `<=` in the
same branch. Consensus **withheld** — two against two is below ⌊π⌋ = 3.
Doctrine settled it: PIPELINE.md prints `compare := additive [ CMP
additive ]`, so a bare `<` that scans as `OP` cannot satisfy the rule
the project already published.

**2 — an unclosed string is `unbounded`, not `misbound`.** PIPELINE.md
classifies running out of input (`1 +`) as `Z(unbounded)` and an
illegal character (`a $ b`) as `Z(misbound)`. A string with no closing
quote ran out of input. The incumbent reported `misbound`, and its own
guard for the case —

```python
if kind is T.STR and not text.endswith('"'):
```

— **can never fire**, because the pattern `"[^"\n]*"` requires the
closing quote in order to match at all. Three of the four new scanners
found `unbounded` independently; doctrine agreed with them.

**3 — six reserved words, not nineteen.** The incumbent reserves 19;
the grammar reaches 6. The other 13 — `anchor` `ascend` `assimilate`
`by` `equiv` `ever` `example` `expect` `learn` `let` `show` `to` `z` —
appear in no rule, so they reserve names against a syntax that does not
exist. `def area(to) = to * 2` failed to parse for no semantic reason.
PIPELINE.md settles it directly: *"This is the whole language. Anything
not derivable here is outside the grammar."*

**4 — several definitions in one text.** All sixteen front ends refused
`def f(n) = n` followed by `def g(n) = n + 1`, unanimously, and the
unanimity was wrong. `abstract.py`'s `Lambda.globals` is a dictionary;
the probe defines `double` and `triple`, holds both, and evaluates
`double(4) = 8` and `triple(4) = 12`. SEMANTICS.md 7 calls the
namespace it is missing a module system for *"one flat global
namespace"* — a namespace the runtime already populates and the grammar
could not address. That is a gap in the **grammar**, and no number of
parsers agreeing changes it.

**5 — no trailing expression after the definitions.** Closing gap 4 the
obvious way — `program := definitions [ expression ]` — makes the
grammar **ambiguous**, and the chart parser said so on the third
generation. `def f(n) = 1 - 1` has two derivations: a body of `1 - 1`,
or a body of `1` followed by the expression `- 1` under prefix minus.
The three deterministic parsers resolve it greedily and never mention
it; only a parser driven by the written grammar can report that the
grammar itself does not decide. Dropping the trailing expression
removes the ambiguity and still closes gap 4, which was about holding
several definitions and never about a trailing expression.

**6 — chained comparison does not parse.** `compare := additive [ CMP
additive ]`: the brackets are optional-once, not repeated.

**7 — no trailing comma.** All sixteen refused it and no document
contradicts them, so this one is genuinely a consensus ruling — the
only one of the seven.

---

## 3. Two defects the laws caught

Not questions about the language; straightforward bugs, found because
the properties were stated universally rather than case by case.

**A conditional is not an operand.** The Pratt and shunting-yard
parsers both handled `if` in operand position, because that is where a
table-driven parser naturally puts a prefix construct. So both accepted
`if a then 1 else 2 != 3` as a comparison whose *left side* was the
conditional. PIPELINE.md puts `ifexpr` as an alternative of `expr`, not
a member of `atom`, so a conditional is never an operand — on the left
or the right. `1 + if a then 2 else 3` is outside the grammar;
`(if a then 1 else 2) != 3` is inside it, and parentheses are the only
thing that makes a conditional an atom.

**The incumbent discarded everything after a definition.**
`syntax.py`'s `program()` returned from the definition branch without
checking that it had reached the end of the input, while the
expression branch checked. So `1 2` was refused and

```
def f(n) = n ) ) )
def f(n) = n garbage
```

both came back `stage="ready"` with the tail silently dropped. All
sixteen forge front ends refuse those texts; the incumbent did not,
and the asymmetry between its own two branches is what gives it away.
Fixed in `2-interpreter-python/syntax.py`; its 212 assertions pass
unchanged, so no test had been asserting the defect.

**The DFA scanner raised on a bare `.`.** A `.` reaching the table in
start position is in no row, so the lookup raised `KeyError` instead of
refusing. Found by the fuzzer inside `let9.1`. SEMANTICS.md G1 says
evaluation is total — *"no exceptions, no undefined behavior"* — and a
scanner that raises makes that a property of whoever remembered to
catch it. It now refuses with `misbound`.

**The trie scanner used `$` as its end-of-token marker.** `$` is a
character a source text may contain, so a `$` in the input walked into
the marker, and the next character indexed a tuple:
`TypeError: tuple indices must be integers`. Found at generation 7 on
`false =$= 35`, which is to say: found because the fuzz budget doubles
after every clean generation, and the seventh generation was the first
one big enough. The fix is a sentinel that cannot collide with the
alphabet it indexes, not a guard against the one character that
happened to break it.

---

## 4. The laws

Stated over all inputs, which is the only kind of statement a fuzzer
can attack.

| Law | Requires |
|---|---|
| `total` | no scanner and no parser ever raises |
| `agreement` | all sixteen reach one verdict |
| `unambiguous` | no text has two trees |
| `roundtrip` | printing a tree and reading it back is the identity |
| `determinism` | the same text twice gives the same answer |
| `position` | every refusal points inside the text it refused |
| `token-stream` | one `EOF`, last; positions never go backwards |

A **verdict** is the tree when the text is accepted, otherwise the
stage and the binding defect. The *position* of a refusal is
deliberately not part of it: a chart parser reports the furthest column
its grammar reached and a recursive-descent parser reports the token it
choked on. Both are honest, they are not the same number, and neither
is a claim about the language. Position is still checked — it must land
inside the text — it just does not decide whether two front ends agree.

---

## 5. What is not claimed

- **Semantics are untouched.** The forge settles stages 1–3. Every rule
  in SEMANTICS.md — the chain rule, corroboration, anchoring, the
  execute floor — is exactly as it was. The four layers keep their own
  sides of the line.
- **No new language features.** Multi-definition is the one place the
  grammar grew, and it grew to reach a capability the runtime already
  had and a document already named. Everything else the forge did was
  subtract, correct, or write down.
- **Convergence is a statement about a search, not a proof.** No
  counterexample was found; that is not a proof that none exists.
  `undermine` in VOWELS.md returns **Z** for exactly this reason, and
  the same honesty applies here.
- **The gaps SEMANTICS.md 7 still names remain open.** Composite data,
  higher-order functions, pattern matching, a static type system, a
  module system, transpiler back-ends, a soundness proof. The formal
  grammar is the one line of that table this work crosses off.

---

## 6. Which front end is which

Two front ends now exist, and they are not the same thing.

| | |
|---|---|
| `2-interpreter-python/syntax.py` | **Ever V3.0's front end.** Still `program := fndef \| expr` — one definition per text. One fix applied: it now checks for end of input in both branches. |
| `7-forge/` | **The reference front end for the core.** Four scanners and four parsers, all sixteen pairings agreeing on the grammar in section 1. |

So `syntax.py` refuses a two-definition text and the core accepts one.
**Adopting the core grammar in `syntax.py` is the obvious next step and
is not done here** — it would be a change to the seed's own parser
rather than a finding about the language, and it belongs in its own
change with the pipeline's 63 assertions re-derived against the new
rules.

---

## 7. What the emitted grammar makes possible

PIPELINE.md ends by naming what stage 4 does not have:

> **A compiler.** The right-hand branch of the diagram — `Interpreter
> OR Compiler` — is still only the left one.

An emitter is a printer with a different target, and `roundtrip` is
already the law that a printer must satisfy. The core now has a written
grammar, a canonical tree, a printer verified against sixteen readers,
and a corpus that says what every one of them must produce. That is the
input a back-end needs.
