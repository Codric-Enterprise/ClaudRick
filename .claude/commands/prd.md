---
description: Write a short Product Requirements Doc for a new feature before building it
argument-hint: [the feature/tool to define]
---
Write a PRD for the feature below — before any code. One job: get the
requirements pinned down so building doesn't drift mid-implementation. Don't
write or edit code as part of this command.

Produce exactly these sections:

- **Problem** — what's broken or missing today, for whom.
- **Goal** — the single outcome that counts as success; not a feature list.
- **Non-goals** — what this explicitly does not attempt, so scope doesn't creep.
- **Users & use case** — who touches this and the concrete scenario that
  exercises it.
- **Requirements** — the must-haves, as testable statements ("the server
  returns 429 with Retry-After when the limit is exceeded"), not vague
  intentions.
- **Constraints** — anything the existing codebase imposes (e.g. ReVision's
  stdlib-only backend, server-side-key rule, `create_server(client=...)`
  seam) that the design must respect.
- **Open questions** — what you can't resolve without the user; ask before
  assuming.

Keep it to what fits on one screen. If the feature is small enough that a PRD
is overkill, say so and suggest going straight to `/brief` or `/code` instead
of padding this out.

Feature: $ARGUMENTS
