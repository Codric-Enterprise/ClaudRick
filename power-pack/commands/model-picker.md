---
description: Pick the right Claude model for a task (2026 stack)
argument-hint: [describe the task — or blank to assess the current one]
---
Recommend which Claude model fits the task below, using the 2026 stack. The
goal is to not pay for brains the task doesn't need — match capability to the
job, not to habit:

- **Haiku 4.5** — bulk and simple: triage, classification, quick lookups,
  simple transforms at volume.
- **Sonnet 5** — the default: everyday coding and drafting; the best balance of
  speed, quality, and cost.
- **Opus 4.8** — deep work: top-tier reasoning, serious writing, strategy,
  complex debugging.
- **Fable 5** — the hardest problems: long-horizon, ambitious, multi-step
  frontier work where quality dominates cost.
- **Mythos 5** — not a general option: limited-access, high-security workflows
  for approved organizations only.

Give: the recommended model; the two or three signals in the task that drove
the choice; what would escalate it a tier (and what the cheaper fallback costs
you in practice). If the task has distinct phases, recommend a model per phase
and say where to switch.

Task: $ARGUMENTS
