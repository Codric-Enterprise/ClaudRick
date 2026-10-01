# realm/ — Rime

A language whose grammar rhymes, and whose rhyme rule writes its
programs.

```
3 4 grow      ← -ow: the numbers themselves
12 slow       ← must answer in the same family, or it is not a program
```

Rime is a small postfix language with one unusual property: **a couplet
is well formed only if its two verbs rhyme**, and the vocabulary is
built so that a rhyme class *is* an operation family. Rhyme is a typing
discipline, not decoration.

Because a class is a finite ordered list, the answering verb is simply
*the next one* — so half of every program is derived rather than chosen,
and generation is deterministic with no random source at all.

Start with [`LANGUAGE.md`](LANGUAGE.md).

```bash
python3 realm.py         # write a poem, run it, put it to nine front ends
python3 realm_test.py    # the gate: 74 assertions
```

Separate from ReVision (`src/revision/`) and from EZR (`ezr/`) — no
shared code, its own gate.
