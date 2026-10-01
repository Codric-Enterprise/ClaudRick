# Rime

A postfix language whose **well-formedness condition is rhyme**.

```
3 4 grow
12 slow

7 align
combine
```

That program is legal. This one is not:

```
3 4 grow
7 12 keep      ← unrhymed: -ow answered by -eep
```

## The one idea

A program is a sequence of **couplets**. A couplet is two **lines**. A
line is some operands followed by a **verb**, and because the verb ends
the line, the verb is what the line rhymes on. A couplet is well formed
only when its two verbs rhyme.

That would be decoration if rhyme classes were arbitrary. They are not.
The vocabulary is built so that **a rhyme class is exactly an operation
family**:

| Class | Family | Verbs |
|---|---|---|
| `-ow` | the numbers themselves | `grow` `slow` `throw` `mow` |
| `-ine` | two becoming one, or one becoming two | `twine` `divine` `align` `combine` |
| `-eep` | the store, and the shape of the stack | `keep` `peep` `heap` `sweep` |
| `-ight` | anything said out loud | `light` `sight` `write` `cite` |

So the rhyme rule is a **typing discipline written as verse**. A couplet
that rhymes is a couplet that stayed on one topic, and the checker
enforcing rhyme is enforcing exactly that. You can tell what a couplet
does from how it sounds, before you know what any single word means.

## The rhyme rule generates

Pick the first verb of a couplet and you have picked its class, because
a verb belongs to exactly one. A class is a finite, published, **ordered**
list. So the candidates for the answering verb are not a space to sample
— they are four items in a known order, and Rime's rule is *the next
one*.

`successor` is total over the vocabulary and is a function. **The second
line of every couplet is therefore determined by the first.** Half of
every program writes itself, with no choice involved.

The remaining choices — which class, which opening verb, which numbers —
come from a phrase, through FNV-1a, addressed by position:

```python
Realm("quantum realm").poem(4)
```

There is no random source anywhere in the implementation. Two properties
follow, and they are why this is not just a seeded PRNG:

- **Portable.** FNV-1a is written out, not imported, and `hash()` is
  never touched — so `PYTHONHASHSEED` cannot change a poem. The same
  phrase gives the same text on any machine, any Python, any year.
- **Addressed, not sequential.** Every choice is keyed by a path
  (`"3/b/op1"`). Couplet 9 can be written without writing couplets 0–8
  first, and comes out identical either way. A seeded PRNG cannot say
  that: reaching its hundredth draw means replaying the ninety-nine
  before it.

Generated poems also **cannot starve** — every verb's arity is published,
so the generator tracks the stack as it writes and pushes exactly what
each verb needs.

## Grammar

```ebnf
poem     = couplet* ;
couplet  = line line ;          (* and the two verbs must rhyme *)
line     = NUM* VERB NEWLINE ;
NUM      = "-"? digit+ ;
VERB     = lower+ ;             (* and must be in the vocabulary *)
```

Line structure is significant. A maximal run of line feeds is one
NEWLINE, so the blank line between couplets is cosmetic; a run at the
very start or end of the text yields nothing, because a poem does not
begin or end with silence.

## Refusals

Rime never raises. Every stage returns either a value or a refusal
carrying a defect and a place.

| Defect | Stage | Meaning |
|---|---|---|
| `unknown` | lex | a character Rime has no reading for |
| `unknown` | parse | a legally spelled word that is not a verb |
| `voiceless` | parse | a line that does not end in a verb (`1 2`, `3 grow 4`) |
| `orphaned` | parse | a last line with nobody to answer it |
| `unrhymed` | parse | a couplet whose verbs are in different classes |
| `starved` | run | a verb run with less beneath it than it takes |

**The order of complaint is published**, because a program can be wrong
in several ways at once and three parsers left to themselves would each
report a different favourite — which reads as disagreement about Rime
when it is really disagreement about reading order. Phases run in
sequence: *shape*, then *vocabulary*, then *pairing*, then *rhyme*. A
shape fault anywhere beats a rhyme fault everywhere.

Evaluation is total. Division and modulo by zero give zero; reading an
unwritten cell gives zero. Both are definitions, not accidents — the
alternative is a defect class that exists to describe one arithmetic
edge.

## How the language is established

Three scanners (master regex · hand-rolled walk · transition table) and
three parsers (recursive descent · shift/reduce · segment-first) make
**nine front ends**, each derived from a different mechanism. Where all
nine agree, the answer belongs to Rime. Where they split, Rime never
said, and the split is the finding.

Seven laws hold over every input, not just the ones somebody thought to
write down: `total`, `agreement`, `roundtrip`, `determinism`, `rhyme`,
`family`, `machine`. The test suite injects a deliberately faulty front
end at each law, because a law nobody can fail is decoration.

## Running it

```bash
python3 realm.py                      # write a poem, run it, converge
python3 realm.py --phrase "..." --couplets 6 --poems 40 --verbose
python3 realm_test.py                 # the gate: 74 assertions
```

`realm.py` exits non-zero if any law breaks.

## Files

| File | What it is |
|---|---|
| `contract.py` | tokens, the vocabulary, trees, printing |
| `lexers.py` | L1 regex · L2 hand-rolled · L3 table |
| `parsers.py` | P1 descent · P2 shift/reduce · P3 segment-first |
| `machine.py` | the stack, the store, the voice; static depth |
| `rhyme.py` | the rhyme rule as a generator |
| `realm.py` | the matrix, the laws, the corpus, the CLI |
| `realm_test.py` | the gate |

Rime shares no code with `ezr/` or `src/revision/`. It borrows one
conviction from the EZR forge: a single implementation cannot be
evidence about itself.
