# Layer 7 — the forge

Four lexers, four parsers, sixteen front ends, one language.

EZR V3.0 arrived with a working front end and no specification of it.
`syntax.py` was the lexer, the parser and — by default — the only
statement of what the language accepted. That is a stable arrangement
right up to the moment somebody writes a second implementation, at
which point there is nothing to check it against.

So this layer writes the second implementation. And the third, and the
fourth, and then pairs every scanner with every parser and runs the
matrix against the same cases. Where sixteen independently derived
front ends agree, the answer belongs to the language. Where they split,
the language never said, and the split is the finding.

## Running it

```bash
python3 forge_test.py                 # verify the settled core (61 assertions)
python3 forge.py                      # continue from the current rulings
python3 forge.py --reset              # start again from unratified
python3 grammar_doc.py                # re-emit GRAMMAR.ebnf
```

`--floor` sets how many programs must be fuzzed before convergence may
be declared; the budget doubles after every clean generation, so a
quiet run keeps getting more expensive to stay quiet.

## The pieces

| File | What it is |
|---|---|
| `contract.py` | tokens, AST, canonical forms — the only thing shared |
| `lexers.py` | L1 master regex · L2 hand scanner · L3 DFA table · L4 operator trie |
| `parsers.py` | P1 recursive descent · P2 Pratt · P3 shunting-yard · P4 Earley |
| `corpus.py` | golden cases from the published docs, probes, the fuzzer |
| `laws.py` | the seven properties every input must satisfy |
| `coverage.py` | asks stage 4 what it holds that stages 1–3 cannot say |
| `spec.py` | the ratified decision table |
| `forge.py` | the loop, and the four tiers of arbitration |
| `grammar_doc.py` | emits `GRAMMAR.ebnf` from the parser's own rules |
| `ratified.json` | the rulings, with the reason for each |
| `ledger.json` | what the last run did, generation by generation |

## Why four of each

Precedence lives somewhere different in each parser: in P1 it is the
call graph, in P2 a number in a table, in P3 a stack discipline, in P4
the shape of the rules. Four encodings of one claim. Agreement between
them is evidence about the claim; agreement between four copies of one
parser is evidence about copying.

The same goes for the scanners, and it paid immediately: the four
disagreed about which token kind carries a bare `<` before a single
test had been written, because nobody had ever written that down.

## The four tiers

A disagreement is not settled by a vote if something better is
available.

1. **Doctrine** — SEMANTICS.md or PIPELINE.md already says. A vote
   cannot overturn a published document, so this tier runs first.
2. **Coverage** — stage 4 demonstrably holds something stages 1–3
   cannot express. Consensus cannot see this: all four front ends can
   agree, sincerely, on a limitation the rest of the language does not
   have.
3. **Finding** — one of the laws settles it. A law violation is
   evidence about the language, not about one implementation.
4. **Consensus** — VOWELS.md's oracle, unchanged: at least ⌊π⌋ = 3
   agreeing and at least two thirds of those that answered.

Below all four it withholds and says so. Inventing an answer there
would teach the corpus a fact nobody verified.

See `../CORE.md` for what the forge settled and why.
