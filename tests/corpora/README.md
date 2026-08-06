# ReVision tool test corpora

Batch test inputs + ground truth + graders for all four ReVision tools. All
inputs are fictional. These are **evaluation harnesses**, not pytest tests
(pytest ignores them — no `test_*.py` here).

## Layout

- `analyzer/` — 10 documents (8 predatory + 2 controls) seeded with 34 known
  dark patterns; `ground-truth.json` labels each. Graded by exact match.
- `tools/` — 6 inputs each for Enhance / Translate / Jargonary
  (`<tool>/inputs.json`) with machine-checkable rubric expectations. Graded by
  rubric, since these tools are generative.

## Running the live evaluation (needs a running server with an API key)

```bash
ANTHROPIC_API_KEY=sk-ant-... revision &          # start the server on :8000

# Fine Print Analyzer — per-category recall, score-band accuracy, control FPs
node tests/corpora/analyzer/grade.js       http://localhost:8000

# Enhance / Translate / Jargonary — rubric pass-rates
node tests/corpora/tools/grade-tools.js    http://localhost:8000
# one tool only:
node tests/corpora/tools/grade-tools.js    http://localhost:8000 jargonary
```

Each grader prints per-input pass/fail, per-check pass rates, and a clean-input
count. See `analyzer/evaluation-report.md` and `tools/evaluation-report.md` for
the static (no-key) evaluation and the rubric definitions.
