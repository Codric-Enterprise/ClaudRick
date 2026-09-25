# ruff: noqa: E501  (each mutant is an exact source string; wrapping would change what it matches)
"""Mutants: each is a deliberate bug the gate must catch. Run by finish.py.

A mutant is (file, text, replacement, what it breaks). The gate runs against a copy of this
directory with the one edit applied, and must fail. A mutant whose text is no longer in its
file is stale: the code moved, so the mutant must be moved with it. Stale mutants are failures,
not skips. A mutant that survives is either a gap in the gate or an equivalent change (the
program means the same thing); decide which, and never leave an equivalent one in this list.
"""

MUTANTS = (
    ('core.py', 'return a if a.value == (op == "or") else None', 'return a if a.value == (op == "and") else None', 'short stops on wrong value'),
    ('core.py', 'return a if a.value == (op == "or") else None', 'return None', 'no short circuit'),
    ('core.py', 'Thread(b.value, min(a.trust, b.trust))', 'Thread(b.value, b.trust)', "join drops a's trust"),
    ('core.py', 'Thread(b.value, min(a.trust, b.trust))', 'Thread(b.value, max(a.trust, b.trust))', 'join max'),
    ('core.py', 'Thread(not a.value, a.trust)', 'Thread(a.value, a.trust)', 'not is identity'),
    ('core.py', 'Thread(not a.value, a.trust)', 'Thread(not a.value, LITERAL)', 'not resets trust'),
    ('core.py', '        return Z(f"misbound: {word} needs a Bool, got {a.value!r}")\n', '        return None\n', 'truth accepts non-bool'),
    ('core.py', 'elif ins[0] in ("br", "short", "join")', 'elif ins[0] in ("br",)', 'coverage ignores and/or'),
    ('core.py', 'elif ins[0] in ("br", "short", "join")', 'elif ins[0] in ("br", "short")', 'coverage ignores join'),
    ('core.py', '        return Thread(x % y, trust)', '        return Thread(abs(x) % abs(y) * (1 if x >= 0 else -1), trust)', 'truncated modulo'),
    ('core.py', '        if y == 0:\n            return Z("misbound: modulo by zero")\n', '', 'modulo by zero unguarded'),
    ('core.py', 'if not (_whole(x) and _whole(y)):', 'if not (_num(x) and _num(y)):', 'modulo on floats'),
    ('core.py', 'return got if got.void else Thread(got.value, min(got.trust, cap), got.reason)', 'return got', 'cap disabled'),
    ('parse.py', 'left = Bin("or", left, conjunction(s))', 'left = Bin("and", left, conjunction(s))', 'or read as and'),
    ('parse.py', '        return Not(negation(s))\n    return comparison(s)', '        return Not(comparison(s))\n    return comparison(s)', 'not not'),
    ('parse.py', '    left = conjunction(s)\n    while s.is_word("or")', '    left = negation(s)\n    while s.is_word("or")', 'no and level'),
    ('parse.py', 'op = "*" if s.is_word("times") else "%"', 'op = "*"', 'modulo read as times'),
    ('parse.py', 'return f"{_operand(e.left, in_call=True)} {e.op} {_operand(e.right, in_call=True)}"', 'return f"{_operand(e.left)} {e.op} {_operand(e.right)}"', 'render unwrapped'),
    ('parse.py', 'items = [_operand(i, in_call=True) for i in e.items]', 'items = [_operand(i) for i in e.items]', 'list render unwrapped'),
    ('parse.py', '"trusted", "or", "modulo",', '"trusted",', 'or/modulo not reserved'),
    ('build.py', '            for trust in (LITERAL, CERTAIN):', '            for trust in (LITERAL,):', 'build checks literal trust only'),
    ('build.py', '        if module.FUNCTIONS[n][1:] != (len(r.fn.params), r.trust):', '        if False:', 'build skips interface check'),
    ('build.py', '    found = differences(report, source)', '    found = []', 'build never verifies'),
    ('build.py', '        while keyword.iskeyword(name) or name in taken:', '        while name in taken:', 'keywords not escaped'),
    ('build.py', '                out.append(f"{pad}{ins[1]} = _join({ins[2]!r}, {ins[3]}, {ins[4]})")', '                out.append(f"{pad}{ins[1]} = {ins[4]}")', 'build join drops trust'),
    ('build.py', '                out.append(f"{pad}{ins[1]} = _not({ins[2]})")', '                out.append(f"{pad}{ins[1]} = {ins[2]}")', 'build not codegen drops the negation'),
    ('build.py', '    del sys.modules[module.__name__]', '    pass', 'load leaves module'),
    ('GRAMMAR.ebnf', '| "modulo" ) , unary', ') , unary', 'grammar loses modulo'),
    ('GRAMMAR.ebnf', 'builtin        = "length" | "first" | "rest" ;', 'builtin        = "length" | "first" | "rest" | "last" ;', 'grammar invents a builtin'),
    ('GRAMMAR.ebnf', 'at least most equal to true false', 'at least most equal to true', 'grammar list drifts'),
    ('SEMANTICS.md', '`_cap`', '`_capped`', 'semantics cites a missing function'),
    ('SEMANTICS.md', '`_short`, `_join`, `_not`, ', '', 'semantics omits a copied function'),
)  # fmt: skip
