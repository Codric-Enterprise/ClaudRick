# contract_traps — Sprint 2 tracking note

`ground-truth.json`'s `schema` block now declares the `contract_traps`
category and its 7 subtypes (arbitration_clause, indemnification,
liability_waiver, jurisdiction_shopping, class_action_waiver,
unilateral_modification, confession_of_judgment), matching the prompt
change in the Android app's `AnalyzerPrompts.kt` and (still to do) the
web app's `static/index.html` analyzer prompt.

**Not done yet, and flagged honestly rather than faked:** none of the 10
existing corpus documents (D01–D08, C01–C02) have a contract_traps
pattern *planted* in them, so `documents[].planted[]` has no
contract_traps entries. The schema declaration alone doesn't prove the
analyzer actually detects this category — that requires real planted
examples (e.g., a binding-arbitration clause buried in D01's gym
membership fine print, an indemnification clause in D07's lease
addendum) and a re-run of `grade.js` against them.

**Before Sprint 4 QA hardening claims contract_traps "works":**
1. Add at least 1-2 planted contract_traps patterns per predatory
   document (or a new D09/D10 pair dedicated to it).
2. Re-run `grade.js` to confirm recall on the new category.
3. Confirm the 2 control documents (C01, C02) still score nothing here
   — false positives on this category are especially costly, since
   "you waived your right to sue" is a serious claim to get wrong.
