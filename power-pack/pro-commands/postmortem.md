---
description: Write a blameless postmortem from incident details
argument-hint: [describe what happened, timeline, and resolution]
---
Write a blameless postmortem. Structure:

1. **Summary** — one paragraph: what happened, impact, duration, resolution
2. **Timeline** — minute-by-minute from first signal to full resolution
3. **Root cause** — the actual technical cause (not "human error"), with the causal chain
4. **Contributing factors** — what made detection slow or blast radius large
5. **Impact** — quantified: users affected, errors served, revenue lost, SLA impact
6. **What went well** — things that worked during response
7. **What went poorly** — things that slowed detection or resolution
8. **Action items** — specific, assigned, with priority and due date. Categorize as: prevent recurrence, improve detection, reduce impact
9. **Lessons learned** — systemic insights, not just "be more careful"

Tone: factual, blameless, focused on systems not people.

Incident details: $ARGUMENTS
