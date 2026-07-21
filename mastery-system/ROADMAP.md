# mastery-system (Mastery Protocol) — Roadmap

Roadmap for the standalone `mastery-system/index.html` tool (the "6 Levels to
Claude Power User" model tree + prompt formula). This file only tracks
direction — the tool itself is self-contained, no build step.

## Done

- ✅ Single-file, dependency-free tool covering the 6-level model, deployed as
  static HTML.
- ✅ `.github/workflows/deploy-pages.yml` publishes `mastery-system/` to GitHub
  Pages automatically on push to `main` (and currently also the in-flight
  branch `claude/skills-integration-screenshots-ol4ody`).

## Likely next steps

- Confirm GitHub Pages is actually turned on for this repo under
  **Settings → Pages** — the workflow being present doesn't guarantee Pages is
  enabled; if it isn't, the deploy step will fail or no-op.
- Prune the extra branch (`claude/skills-integration-screenshots-ol4ody`) from
  the deploy trigger once that branch merges — feature-branch entries in a
  Pages trigger tend to accumulate if not cleaned up after merge.
- No changelog/versioning for content edits to the 6-level model itself; worth
  adding if the model starts changing meaningfully between updates.
- Currently no progress-tracking or account system (appropriate for a static
  single-page tool) — only worth revisiting if the tool grows beyond a
  read-only reference.
