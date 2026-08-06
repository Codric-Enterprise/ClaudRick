# ReVision — Four-Tool Batch Test & Evaluation

Generated 2026-07-19T04:10:17.694Z. All inputs are fictional. This covers all four tools; the Fine Print Analyzer corpus lives in `../corpus`.

## Corpus at a glance

| Tool | Inputs | Coverage | Output | Gradeable how |
|---|---|---|---|---|
| Fine Print Analyzer | 10 | 5 categories, all subtypes | structured JSON | **exact** — vs 34 ground-truth patterns |
| Enhance | 6 | 6 doc types | plain text | rubric (5 checks) |
| Translate | 6 | 4 target langs, 4 detected sources | JSON | rubric (6 checks) |
| Jargonary | 6 | 6 domains, 2 levels, 24 terms | JSON | rubric (5 checks) |

**Total: 28 test inputs across the four tools.**

## Why the tools grade differently

The Analyzer returns structured JSON, so it grades against exact ground truth (the 34 planted patterns). The other three are **generative** — no single correct output — so they grade against **machine-checkable rubric assertions** that hold regardless of wording:

**Enhance** — non_empty, length_ratio_0.5_to_3x, preserves_must_keep, no_meta_preamble, tone_direction_signal

**Translate** — valid_json, translation_non_empty, detected_language_correct, preserves_must_keep, sentence_count_parity, translation_differs_from_source

**Jargonary** — valid_json, simplified_non_empty, key_takeaway_non_empty, glossary_covers_terms, preserves_must_keep

These avoid the trap of scoring style: they check meaning-preservation (must-keep numbers/terms survive), structural validity (parseable JSON, non-empty fields), directional correctness (detected language, tone signal, glossary recall) — not prose quality.

## What can be evaluated now vs. live

- **Now (no key):** corpus completeness and balance — done. Every tool has ≥6 varied inputs with defined must-keep tokens and expected outcomes. The Analyzer’s static evaluation (coverage + the 35% hidden-terms finding) is in `../corpus/evaluation-report.md`.
- **Live (needs a keyed session):** the rubric pass-rates. Each generative-tool input is scored by running it through the tool and applying the assertions above. Recall/pass-rate is only meaningful against real model output.

## Running the live evaluation

```bash
ANTHROPIC_API_KEY=sk-ant-... revision &        # start server (fresh keyed session)
node ../corpus/grade.js  http://localhost:8000  # Analyzer: recall + score bands
node grade-tools.js      http://localhost:8000  # Enhance/Translate/Jargonary rubric pass-rates
# or one tool: node grade-tools.js http://localhost:8000 jargonary
```

Each grader prints per-input pass/fail, per-check pass rates, and a clean-input count. LLM-as-judge scoring (nuanced quality) can be layered on later; the rubric layer is the objective floor.
