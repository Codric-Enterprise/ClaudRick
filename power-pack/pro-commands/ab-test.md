---
description: Design an A/B test with hypothesis, metrics, and sample size
argument-hint: [what you want to test and optimize]
---
Design a rigorous A/B test:

1. **Hypothesis** — "If we [change], then [metric] will [improve] because [reasoning]"
2. **Primary metric** — the one number that decides winner/loser, and why this metric
3. **Guardrail metrics** — what must NOT get worse (engagement, revenue, error rate)
4. **Variants** — control vs. treatment(s) with exact specification of what changes
5. **Sample size** — calculate minimum sample per variant (given baseline rate, MDE, power, significance)
6. **Duration estimate** — how long to run based on your traffic and the required sample
7. **Segmentation** — should you split by user type, geography, device? Why or why not
8. **Randomization** — unit of randomization (user, session, page view) and why
9. **Analysis plan** — statistical test to use, one-tailed vs. two-tailed, how to handle multiple comparisons
10. **Decision framework** — what results lead to ship, iterate, or kill

Flag common pitfalls: peeking, novelty effects, Simpson's paradox, insufficient runtime.

Test: $ARGUMENTS
