# Claude in 2026 — The Working Cheat Sheet

A refined distillation of four 2026 community cheat sheets, integrated into this
repo alongside the older [50-tips playbook](claude-playbook.md):

- **"How To Actually Use Claude"** — the 5 surfaces, the 2026 model stack, core
  files, and the first 30 minutes.
- **"Claude Code App Development Workflow"** — 10 steps to ship apps.
- **"25 Ways To Use Claude"** — a verb → capability map.
- **"Claude AI Prompt Master"** — prompt patterns by role.

> Scope note (same as the older playbook): several entries are **product
> features** of the Claude apps (Cowork, Connectors, Chrome, Excel) or workflow
> habits, not things this repository's code implements. They're recorded here as
> reference; the parts that translate to reusable prompts are wired up as slash
> commands (see the last section).

---

## 1 — It's not 1 tool. It's 5.

Most people only ever use Chat. The leverage is in matching the surface to the
job:

| Surface | What it's for |
|---|---|
| **Chat** | Quick questions and drafts |
| **Projects** | Persistent workspaces with memory over a doc set |
| **Cowork** | File-first execution and deliverables |
| **Skills** | Reusable, packaged workflows and playbooks |
| **Connectors** | Live context from Gmail, Drive, Slack, Notion, and more |

> Claude performs better when your work has **structure** — the point of the
> core files (§3) and the prompt template (§4).

---

## 2 — The 2026 model stack (pick the right model)

Don't pay for brains you don't need. Match the model to the task.

| Model | Best for |
|---|---|
| **Fable 5** | Hardest coding, long-horizon tasks, ambitious projects |
| **Opus 4.8** | Top-tier reasoning, writing, strategy, deep analysis |
| **Sonnet 5** | Best default — balance of speed, quality, and cost |
| **Haiku 4.5** | Bulk tasks, triage, classification, simple transforms |
| **Mythos 5** | Limited-access, high-security / specialized frontier workflows |

**Pro tip:** start with **Sonnet**; upgrade to **Fable** or **Opus** when
quality matters. Switch models mid-task to hit the right cost/quality point.
Operationalized as the [`/model-picker`](../.claude/commands/model-picker.md)
command.

> This is the same stack shown in the [Mastery Protocol](../mastery-system/index.html)
> model tree — keep the two in sync when the lineup changes.

---

## 3 — Write your core files

A few strong `.md` files beat dozens of random prompts. Write them once, point
Claude at them everywhere (global instructions, Projects, or a working folder):

| File | Holds |
|---|---|
| **about-me.md** | Role, goals, voice, priorities |
| **anti-style.md** | Phrases, tones, and patterns to avoid |
| **project-brief.md** | Objective, audience, inputs, constraints |
| **output-rules.md** | Format, length, quality bar, done criteria |

**Global instructions** then tie them together: read `about-me.md` first, check
the active project folder, read uploaded files before acting, ask clarifying
questions when needed, and stay concise, accurate, and source-aware.

> Operationalized here as the [`/about-me`](../.claude/commands/about-me.md)
> command, which drafts and maintains the profile file, and as the "Write Your
> Core Files" section of the [Mastery Protocol](../mastery-system/index.html).

---

## 4 — The prompt template

Good prompts define the finish line. Structure every non-trivial request with
these elements:

1. **Task** — what you want done.
2. **Context** — the background that matters.
3. **Inputs / files** — the material to work from.
4. **Constraints** — limits to respect.
5. **Success criteria** — how "done" is judged.
6. **Output format** — the shape of the deliverable.
7. **Ask if needed** — invite clarifying questions before starting.
8. **Start only when aligned** — don't begin until the above is settled.

> Operationalized here as the [`/brief`](../.claude/commands/brief.md) command.
> This is a superset of the older CSI + FBI framework and the mastery system's
> 5-part formula — use whichever framing fits, but always name the finish line.

---

## 5 — Best uses (and what to avoid)

**Lean in:** writing in your voice, long-context analysis, project planning,
research synthesis, file-based work, and workflows with connected apps.

**Be careful with:** photo/image editing, live web search without checking
sources, vague one-line briefs, and sensitive work shipped without review.

---

## 6 — Your first 30 minutes

| Time | Do |
|---|---|
| 0–5 min | Install and sign in |
| 5–10 min | Connect Drive / Slack / Gmail / Notion |
| 10–15 min | Create workspace folders |
| 15–20 min | Write the 4 core files (§3) |
| 20–25 min | Run one real Cowork task |
| 25–30 min | Turn the winning process into a Skill |

---

## 7 — Claude Code app development workflow (10 steps)

Most people use Claude Code as a code generator. The leverage is building a
**repeatable development system** around it:

1. **Set up the environment** — install the essentials (Node.js, Claude, Git,
   editor, Docker); remove setup friction before building.
2. **Write the PRD** — define target users, business goals, success metrics, and
   constraints before touching code.
3. **Create `CLAUDE.md`** — document the tech stack, coding standards, folder
   structure, safety rules, and CI/CD workflow. *(This repo has one.)*
4. **Scaffold the project** — routes, folders, a Dockerfile, and the core app
   skeleton, early.
5. **Test the pipeline first** — a basic test suite and deploy pipeline; ship to
   staging before building real features.
6. **Build one feature at a time** — small iterations; don't prompt for the
   whole app at once.
7. **Start with edge cases** — list failure modes, invalid input, and weird
   inputs first so the design is more robust.
8. **Use test-driven thinking** — write failing tests, implement, review every
   diff, commit in small chunks.
9. **Connect Claude with MCP** — link external tools (GitHub, Slack, databases,
   Playwright) for deeper workflows.
10. **Use agents + automation** — a lead/planner agent delegates to specialists;
    automate PR reviews, CI-failure triage, dependency updates, and security
    scans.

> Core lesson: Claude Code isn't just a code generator — build a **repeatable
> development system** around it. Steps 3, 5, 8, and 10 already describe how this
> repo operates (`CLAUDE.md`, CI gate, TDD, and the `.claude/` tooling).

---

## 8 — 25 ways to use Claude (verb → capability)

A fast index from what you want to do to the surface that does it:

| Verb | Use |
|---|---|
| Ask | Chat |
| Think | Opus 4.8 |
| Speed | Sonnet 5 |
| Reason | Extended Thinking |
| Build | Cowork |
| Ship | Claude Code |
| Model | Claude in Excel |
| Slides | Gamma connector |
| Mockup | Claude Design |
| Browse | Claude in Chrome |
| Click | Computer Use |
| Remote | Dispatch |
| Search | Web Search |
| Investigate | Research |
| Trigger | Skills |
| Stack | Plugins |
| Persist | Projects |
| Automate | Scheduled Tasks |
| Connect | Connectors |
| Render | Artifacts |
| Voice | Custom Styles |
| Share | Team Projects |
| Guard | Global Instructions |
| Organize | Obsidian Vault |
| Brief | About-Me file |

> Source note: the original sheet paired "Speed" with *Sonnet 4.6*; it's
> normalized here to **Sonnet 5** to match the 2026 model stack in §2. The verb
> map is about the surface, not the exact version.

---

## 9 — Prompt patterns by role (Prompt Master)

Paste-ready starting points, grouped by who you are. Fill the `[brackets]`.

**Writers** — write a high-converting article on `[topic]` with a strong hook;
rewrite in a more engaging, human tone; add emotional depth; turn an idea into a
viral post.

**Business** — generate a business plan for `[idea]` with a monetization
strategy; identify 5 scalable income streams for `[niche]`; analyze this model
and suggest improvements.

**Marketing** — write a persuasive sales page for `[product]`; generate 10 viral
hooks for `[topic]`; build a full funnel strategy; write ad copy optimized for
CTR.

**Developers** — generate clean, optimized code for `[idea]`; debug and improve
`[code]`; explain this code step by step; suggest architecture for a scalable
system; convert this logic into production-ready code.

**Learning** — teach me `[topic]` from beginner to advanced; create a structured
learning roadmap for `[skill]`; explain using analogies; test my understanding
with questions.

**Content creators** — generate 30-day content ideas for `[niche]`; write a
viral reel script with hook + retention; optimize captions for engagement; turn
this topic into a carousel.

**Chain framework** (any topic): summarize → expand into detail → simplify for
beginners → convert into social content → turn into a monetizable idea.

**Output formats:** blog post · social post · email · report · script ·
presentation · bullet list.
**Tones:** professional · confident · persuasive · conversational · minimal ·
storytelling · analytical · high-authority.

> Most of these map to existing slash commands — see `/write`, `/rewrite`,
> `/code`, `/debug`, `/learn`, `/table`, `/summary`, `/expand`, `/eli5`,
> `/convert`, and the tone/format controls in
> [`commands-pack.md`](commands-pack.md).

---

## What this repo added from these sheets

- **`Mythos 5`** added to the Mastery Protocol model tree (§2).
- **[`/brief`](../.claude/commands/brief.md)** — the §4 prompt template as a
  reusable command.
- **[`/about-me`](../.claude/commands/about-me.md)** — drafts the §3 core profile
  file.
- **[`/model-picker`](../.claude/commands/model-picker.md)** — the §2 model
  choice as a reusable command.
- **"Write Your Core Files"** section (§3) on the Mastery Protocol page.
- A **"Try an Example"** button in the Fine Print Analyzer preloading fictional
  scammy ad copy (§5's "be careful with" tactics, made demonstrable).
- This reference doc, linked from `CLAUDE.md`.
