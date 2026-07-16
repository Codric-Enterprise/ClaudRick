---
description: Structure an incident response from symptoms
argument-hint: [describe the incident — errors, symptoms, timeline]
---
You are the incident commander. Given the symptoms below, produce:

1. **Severity classification** — SEV1-4 with justification
2. **Impact assessment** — users affected, revenue impact, data risk
3. **Hypothesis tree** — ranked list of probable root causes with evidence for/against each
4. **Triage steps** — specific commands, queries, or checks to run right now (in priority order)
5. **Mitigation options** — immediate actions to reduce impact (rollback, feature flag, redirect, scale)
6. **Communication template** — status page update and internal Slack message, both ready to send
7. **Escalation criteria** — when to page who

Be specific. Reference actual services, logs, and metrics — not generic advice.

Incident: $ARGUMENTS
