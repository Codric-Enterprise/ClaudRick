# How To Actually Use Claude — 2026 Cheat Sheet

> "The Updated Cheat Sheet You'll Actually Save."

A faithful transcription of the ten-panel *How To Actually Use Claude* cheat
sheet (2026 edition), annotated for this repository. Original framework credited
to **Denis Panjuta** ([@denis-panjuta](https://twitter.com/denis_panjuta));
reshared by Code 231.

The interactive version of this page lives at
[`docs/claude-2026-cheatsheet.html`](./claude-2026-cheatsheet.html) — a
self-contained, shareable artifact in the same house style as the
[command console](./command-console.html).

> Scope note: like the [playbook](./claude-playbook.md), much of this sheet
> describes Claude *product* surfaces (Cowork, Projects, Connectors) and working
> conventions rather than things this repo's runtime code implements. The
> **Mapped to this repo** column below points to the parts ReVision already
> operationalizes as commands, skills, and hooks.

---

## The thesis

> **Claude becomes powerful when your workflow has structure.**
>
> Many people open it, type a random one-liner, and judge the result. The
> people who get professional-grade output do the opposite: they give context,
> attach files, set a clear target, pick the right model, review, and save the
> winning process as a reusable Skill.

The loop the sheet keeps returning to:

`Give context → Attach files → Set the target → Use the right model → Review & refine → Save to Skills`

→ **Better context + better work → better results.**

---

## 01 — Claude in 2026

- **Model stack:** Fable 5, Opus 4.8, Sonnet 5, Haiku 4.5, Mythos 5.
- **Long-context workflows:** up to a 1M-token-class context on supported
  workflows.
- **Works across** chat, files, tools, and connected apps.
- **Best when** you give context, files, and a clear success target.

**2026 at a glance:** 1M token context class · longer context · more capable ·
safer by design · faster & smarter.

## 02 — It's not 1 tool. It's 5.

| Surface | What it's for |
| --- | --- |
| **Chat** | Quick questions and drafts |
| **Projects** | Persistent workspaces with memory |
| **Cowork** | File-first execution and deliverables |
| **Skills** | Reusable workflows and playbooks |
| **Connectors** | Gmail, Drive, Slack, Notion, and more |

## 03 — Pick the right model

| Model | Reach for it when… |
| --- | --- |
| **Fable 5** | Hardest coding, long-horizon tasks, ambitious projects |
| **Opus 4.8** | Top-tier reasoning, writing, strategy, deep analysis |
| **Sonnet 5** | Best default balance of speed, quality, and cost |
| **Haiku 4.5** | Bulk tasks, triage, classification, simple transforms |
| **Mythos 5** | Limited-access high-security / specialized frontier workflows |

**Pro-tip:** Start with Sonnet. Upgrade to Fable or Opus when quality matters.

## 04 — Setup in 5 minutes

1. Install the desktop app or open Claude.
2. Upgrade to Pro / Team if you need more usage and advanced features.
3. Open Projects or Cowork.
4. Connect your apps and choose a working folder.

**Top connectors:** Drive · Gmail · Slack · Notion.

## 05 — The smart workspace (Cowork)

A single flow, left to right:

`About Me → Projects → Templates → Research → Final Outputs`

> Claude performs better when your work has structure.

## 06 — Write your core files

A few strong `.md` files beat dozens of random prompts.

| File | Holds |
| --- | --- |
| `about-me.md` | Role · goals · voice · priorities |
| `anti-ai-style.md` | Phrases · tone · patterns to avoid |
| `project-brief.md` | Objective · audience · inputs · constraints |
| `output-rules.md` | Format · length · quality bar · done criteria |

## 07 — Global instructions

Standing rules that guide *every* response:

- Read `ABOUT-ME` first.
- Check the active project folder.
- Read uploaded files before acting.
- Ask clarifying questions when needed.
- Be concise, accurate, and source-aware.

## 08 — The prompt template

Good prompts define the finish line.

- **Task** — what you want done.
- **Context** — background it needs.
- **Inputs / files** — the material to work from.
- **Constraints** — what to respect.
- **Success criteria** — how "done" is judged.
- **Output format** — the shape of the deliverable.
- **Ask a question if needed** — permission to check before guessing.
- **Start only when aligned** — no output until the brief is clear.

## 09 — Best uses for Claude

**Do this**

- Writing in your voice
- Long-context analysis
- Project planning
- Research synthesis
- File-based work
- Workflows with connected apps

**Avoid this**

- Photo / image editing
- Live web search without checking sources
- Vague one-line briefs
- Sensitive work without review

> Leverage strengths. Avoid pitfalls.

## 10 — Your first 30 minutes

| Time | Do |
| --- | --- |
| 0–5 min | Install and sign in |
| 5–10 min | Connect Drive / Slack / Gmail / Notion |
| 10–15 min | Create workspace folders |
| 15–20 min | Write the 4 core files |
| 20–25 min | Run one real Cowork task |
| 25–30 min | Turn the winning process into a Skill |

---

## Mapped to this repo

Where the sheet's advice already has a concrete home in ReVision's tooling:

| Sheet panel | Already lives here |
| --- | --- |
| 03 · Pick the right model | The [`claude-power-practices`](../.claude/skills/claude-power-practices/SKILL.md) skill leads with model choice; the app's model is server-controlled in [`config.py`](../src/revision/config.py) (`REVISION_MODEL`). |
| 06 · Write your core files | `CLAUDE.md` is this repo's `about-me.md` + `output-rules.md`; the [command reference](./commands-pack.md) gives `/context`, `/constraints`, `/focus`, `/preferences` for the rest. |
| 07 · Global instructions | The `SessionStart` hook ([`.claude/hooks/session-start.sh`](../.claude/hooks/session-start.sh)) + `CLAUDE.md`'s "Notes for AI assistants" are the standing rules. |
| 08 · The prompt template | Operationalized as slash commands: `/focus`, `/context`, `/constraints`, `/checklist`, `/clarify`, `/format` — the template's fields, one command each. |
| 10 · Turn the process into a Skill | This repo's [`.claude/skills/`](../.claude/skills/) (`dev-check`, `run-app`, `add-tool`, `test-and-lint`) are exactly that: winning processes saved as skills. |

## What to treat with care

An evaluation, not just a transcription:

- **Model names are a moving target.** The stack listed (Fable 5, Opus 4.8,
  Sonnet 5, Haiku 4.5, Mythos 5) is the sheet's 2026 snapshot. Verify current
  ids before hard-coding them anywhere; this repo keeps the id in `config.py`,
  not the frontend, for exactly that reason.
- **"1M-token-class" is a ceiling, not a free lunch.** Long context still
  rewards curation — a tight brief and the right files beat a giant dump.
- **"Avoid live web search without checking sources"** is the same guardrail as
  the playbook's anti-fake-links rule and the `claude-power-practices` skill:
  never present unverified links or claims as fact.
- **The sheet is a workflow, not a spec.** It's advice for using the Claude
  apps; none of it changes ReVision's server-side-key rule or endpoints. Treat
  it as a companion to [`claude-playbook.md`](./claude-playbook.md).
