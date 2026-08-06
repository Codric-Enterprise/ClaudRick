---
description: Plan a safe migration between systems, frameworks, or versions
argument-hint: [from X to Y — describe the migration]
---
Plan a complete migration for the following. Produce:

1. **Scope assessment** — what's affected, what's unchanged, blast radius
2. **Compatibility matrix** — breaking changes, deprecated APIs, behavioral differences
3. **Migration sequence** — ordered steps with dependencies between them
4. **Rollback plan** — for each step, how to undo it if something goes wrong
5. **Data migration** — schema changes, data transformations, validation queries
6. **Dual-run strategy** — how to run old and new in parallel during transition
7. **Verification checklist** — specific tests to confirm each step succeeded
8. **Timeline estimate** — realistic duration for each phase

Flag anything that requires downtime. Prefer zero-downtime approaches.

Migration: $ARGUMENTS
