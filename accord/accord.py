"""accord — the gate: two surfaces, one tree, one TAC, examples that actually run.

python3 accord.py agree examples/classify.emit examples/classify.prose
python3 accord.py tac examples/fact.prose
"""

from __future__ import annotations

import sys
from pathlib import Path

import emit
import prose
from core import AccordError, check, format_tac, lower, run_examples, tac_hash

SURFACES = {".emit": emit.parse, ".prose": prose.parse}


def load(path: str):
    suffix = Path(path).suffix
    if suffix not in SURFACES:
        raise SystemExit(f"{path}: unknown surface {suffix!r} (want .emit or .prose)")
    return SURFACES[suffix](Path(path).read_text())


def agree(emit_source: str, prose_source: str) -> dict:
    report: dict = {"stage": None, "errors": [], "hash": None, "examples": None}
    trees = {}
    for label, parse, source in (
        ("emit", emit.parse, emit_source),
        ("prose", prose.parse, prose_source),
    ):
        try:
            trees[label] = parse(source)
        except AccordError as err:
            report["stage"] = f"{label}: parse"
            report["errors"] = [str(err)]
            return report
        errors = check(trees[label])
        if errors:
            report["stage"] = f"{label}: check"
            report["errors"] = errors
            return report
    if trees["emit"] != trees["prose"]:
        report["stage"] = "agree: tree"
        report["errors"] = [_first_difference(trees["emit"], trees["prose"])]
        return report
    tacs = {k: lower(v) for k, v in trees.items()}
    hashes = {k: tac_hash(v) for k, v in tacs.items()}
    if hashes["emit"] != hashes["prose"]:
        report["stage"] = "agree: tac"
        report["errors"] = ["trees agree but TAC differs: the lowering is not deterministic"]
        return report
    report["hash"] = hashes["emit"]
    verdicts = {k: run_examples(trees[k], tacs[k]) for k in trees}
    report["examples"] = (len(verdicts["emit"].passed), len(trees["emit"].examples))
    for label, verdict in verdicts.items():
        for ex, got in verdict.failed:
            shown = got.reason if got.void else f"{got.value!r} @ {got.trust}"
            report["errors"].append(
                f"{label}: {ex.args} should give {ex.value!r} @ {ex.trust}, gave {shown}"
            )
    report["stage"] = "examples" if report["errors"] else "agreed"
    return report


def _first_difference(a, b) -> str:
    for field in ("name", "params", "returns", "measure", "body", "examples"):
        if getattr(a, field) != getattr(b, field):
            left, right = getattr(a, field), getattr(b, field)
            return f"the surfaces disagree on {field}:\n  emit:  {left}\n  prose: {right}"
    return "the surfaces disagree"


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[0] == "agree":
        report = agree(Path(argv[1]).read_text(), Path(argv[2]).read_text())
        if report["stage"] == "agreed":
            passed, total = report["examples"]
            print(f"agreed  tac {report['hash'][:16]}  examples {passed}/{total}")
            return 0
        print(f"refused at {report['stage']}")
        for err in report["errors"]:
            print(f"  {err}")
        return 1
    if len(argv) == 2 and argv[0] == "tac":
        try:
            fn = load(argv[1])
        except AccordError as err:
            print(f"refused at parse: {err}")
            return 1
        errors = check(fn)
        if errors:
            print("refused at check:\n  " + "\n  ".join(errors))
            return 1
        tac = lower(fn)
        print(format_tac(tac))
        print(f"# sha256 {tac_hash(tac)}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
