# Fine Print Analyzer — Test Corpus Evaluation

Generated 2026-07-18T20:29:05.966Z. All documents are fictional; no real people, brands, or offers.

## 1. Corpus summary

- **Documents:** 10 (8 predatory, 2 benign controls)
- **Planted dark patterns (ground truth):** 34
- **Categories exercised:** 5/5
- **In the new `hidden_terms_and_costs` category:** 12 (35% of all patterns)

## 2. Pattern distribution by category

| Category | Planted | Subtypes exercised |
|---|---|---|
| `deceptive_language` | 3 | 3 (freeform) |
| `tone_manipulation` | 8 | 5/5 |
| `scare_tactics` | 4 | 4/4 |
| `artificial_urgency` | 7 | 4/4 |
| `hidden_terms_and_costs` | 12 | 5/5 |

Severity mix: 5 critical · 14 high · 13 medium · 2 low.

## 3. Coverage check

**Complete** — every subtype in all five categories appears at least once, so the corpus exercises the full analyzer schema.

## 4. Impact of the new category (why it matters)

12 of 34 planted patterns (35%) live in `hidden_terms_and_costs` — the category added this session. Before it existed, the four-category schema had no dedicated home for buried fees, auto-renewal, forced continuity, or hard-to-cancel terms, so these would have been dropped or weakly filed under `deceptive_language`.

**6 of 8 predatory documents** carry a critical/high hidden-terms pattern as a top harm and would have been under-scored pre-change:

- **D01** FitLife Health Club — Membership Agreement — `auto_renewal`, `cancellation_obstruction`
- **D02** CloudNote Pro — Free Trial Terms — `forced_continuity`
- **D03** QuickCash Advance — Loan Offer — `buried_limitation`
- **D05** GlowBox Beauty — Subscription Offer — `hidden_fee`, `forced_continuity`
- **D06** The Wealth Accelerator Program — `forced_continuity`
- **D07** Maple Court Apartments — Lease Addendum — `hidden_fee`, `cancellation_obstruction`

## 5. Per-document ground truth

| ID | Kind | Patterns | Expected risk band | Top harms |
|---|---|---|---|---|
| D01 | predatory | 5 | 70–90 | auto_renewal, cancellation_obstruction, now_or_never |
| D02 | predatory | 3 | 65–85 | forced_continuity, contradiction |
| D03 | predatory | 4 | 75–95 | framing, buried_limitation, negative_consequence |
| D04 | predatory | 4 | 65–85 | now_or_never |
| D05 | predatory | 4 | 60–85 | hidden_fee, forced_continuity |
| D06 | predatory | 5 | 80–98 | false_guarantee, time_pressure, forced_continuity |
| D07 | predatory | 4 | 65–88 | hidden_fee, cancellation_obstruction, threat |
| D08 | predatory | 5 | 80–98 | false_authority, now_or_never |
| C01 | control | 0 | 0–12 | — |
| C02 | control | 0 | 0–15 | — |

## 6. Live grading (when an API key is present)

`grade.js` POSTs each document to a running ReVision server (`/api/messages`), parses the analyzer JSON, and scores it against this ground truth:
- **Recall per category** — did the analyzer flag each planted pattern (phrase substring match)?
- **False-positive rate** — do the two controls stay under their expected bands?
- **Score-band accuracy** — does `overall_risk_score` land in each document’s expected band?

```bash
ANTHROPIC_API_KEY=sk-ant-... revision &   # start the server
node grade.js http://localhost:8000        # run the batch + print metrics
```

Until then, sections 1–5 are the static evaluation: the corpus is complete, balanced, and controls-included.
