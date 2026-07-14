# Claude Playbook

A reference distilled from two community cheat-sheets, integrated into this repo
as working tooling:

- The **50 Tips** below are operationalized as the
  [`claude-power-practices`](../.claude/skills/claude-power-practices/SKILL.md)
  skill (auto-applied guardrails).
- The **Command Reference** is operationalized as real slash commands in
  [`.claude/commands/`](../.claude/commands/) (the high-value subset).

> Note on scope: some sheet entries are product features of the Claude apps
> (Chrome extension, Excel add-in, keyboard shortcuts, Memory, Connectors) or
> conversational conventions rather than things this repository can implement.
> They're recorded here for reference; the repo tooling implements the parts
> that translate to reusable prompts and guardrails.

---

## Part 1 — Top 50 Game-Changing Claude Tips

**Getting set up**
1. **Upgrade to a paid plan** — higher usage limits; advanced features; admin/security controls on Team/Enterprise.
2. **Pick the right model** — Opus for reasoning, Sonnet for a speed/intelligence balance, Haiku for fastest iteration.
3. **Set up profile preferences** — so Claude defaults to your preferred structure, tone, and units.
4. **CSI + FBI prompting framework** — Context, Specific, Instruction + Format, Blueprint, Identity.
5. **Chat search** — ask Claude to search your past chats to reuse earlier narrative/definitions.

**Memory & context**
6. **Memory** — turn on/off whether Claude remembers preferences/context across conversations.
7. **Voice input** — dictate complex prompts, brainstorm, or draft long narratives.
8. **Incognito chats** — won't use existing memory; new chats only (top-right corner).
9. **Knowledge-cutoff awareness** — know each model's training cutoff; verify post-cutoff facts with web search.
10. **Project sharing** — add a chat to a Project, then Share → invite by email / toggle general access.

**Power features**
11. **Claude in Chrome** — browser extension (beta) to navigate, click, and fill forms.
12. **Finance prompt pattern** — structured workflow: data → analysis → deliverable; specify materiality & time window.
13. **XML tags for precision** — wrap instructions/context/format in tags so requirements don't mix.
14. **Web search + web fetch** — search for benchmarks/news; provide URLs for deeper fetch analysis.
15. **Research mode** — search across connected internal sources + the web.
16. **Extended thinking** — enable for complex scenario planning, tradeoffs, multi-step reasoning.
17. **Hallucination guardrails** — use verification patterns; force "don't guess" behavior.
18. **Anti-fake-links check** — if Claude gives a link or claims it sent something, force verification.
19. **Create real deliverables** — have Claude create/edit files (XLSX/PPT/DOCX/PDF) directly.
20. **Image understanding** — Claude can analyze uploaded images (e.g. chart screenshots).

**Scaling up**
21. **Connectors** — live context from your tools during a conversation, no manual uploads.
22. **Project knowledge scale** — Projects use RAG to expand capacity (~10×) for large doc sets.
23. **Agent Skills for SOPs** — enable Skills (code execution), create custom Skills to standardize SOPs.
24. **Artifacts for prototyping** — prototype shareable dashboards/tools; publish/share when ready.
25. **Claude Code for automation** — terminal/agentic tool for repeatable reporting automation.
26. **Install Claude in Excel** — add-in from the Microsoft Marketplace (admin deploy via M365 if needed).
27. **Ctrl+Option+C (Mac)** — shortcut to open the Claude sidebar.
28. **Ctrl+Alt+C (Windows)** — shortcut to open the Claude sidebar.
29. **Model switch** — switch models mid-task for the right cost/quality point.
30. **Get citations** — ask "what does this call/range do?" for cell-level citations you can click.

**Spreadsheet & finance workflows**
31. **Workbook summary** — "Give me a 10-bullet overview of what this workbook is for."
32. **Formula explanation** — "Explain this formula like I'm briefing the board."
33. **Formula creation** — "Build a formula that flags overdue invoices" → review → apply.
34. **Formula troubleshooting** — "Find all #REF errors" or why a cell errors → trace it.
35. **Multi-tab reading** — "What assumptions drive the revenue forecast?" across tabs.
36. **Scenario analysis** — "Build a sensitivity table showing IRR across exit multiples and hold periods."
37. **Extract insights & trends** — "Identify my top 10 customers by revenue and their growth rates."
38. **Variance analysis** — "Compare actuals to budget and explain the largest variances."
39. **Highlight discrepancies** — "Reconcile these two sheets and highlight discrepancies."
40. **Standardized formats** — "Clean up company names and convert all dates to YYYY-MM-DD."
41. **Fix data-quality issues** — "Find and remove duplicate rows, keep the latest"; fix encoding errors.
42. **Build a model template** — "Build a three-statement model for a SaaS company" from scratch.
43. **Extract financial table** — upload PDF/CSV → extract into editable data (best with native/digital PDFs).
44. **Audit & validate model** — "Check that all formulas are linked correctly across sheets."
45. **Improve model** — "What's missing from this valuation model?" / "How can I simplify it?"
46. **Add data from files** — "Fill this DCF template from the uploaded financials."
47. **Extract financial table** — from uploaded PDF/CSV into structured data.
48. **Convert digital PDFs to Excel** — "Extract the financial table into editable Excel data."
49. **Mini audit trail** — enable a Claude Log tab; request a "work log" appendix in chat.
50. **Debug & fix errors** — identify #REF!/#VALUE! → get actionable fixes → track/undo changes.

---

## Part 2 — Claude Command Reference

Every command from the "Claude Command — Complete Reference" sheet is
implemented as a real slash command in `.claude/commands/` — invoke as
`/name [args]`.

Three names — `/clear`, `/memory`, `/review` — collide with Claude Code's own
built-ins. Inside Claude Code the **built-in wins** and the custom file defers
to it (each such file documents this and points to the native behavior); the
custom versions still serve as prompt directives in other contexts.

### Focus & Context
| Command | Purpose |
|---|---|
| `/focus` | Set the main objective |
| `/context` | Add background |
| `/details` | Provide more detail |
| `/examples` | Give examples |
| `/clarify` | Ask follow-up questions |
| `/define` | Define terms |
| `/assumptions` | List assumptions |
| `/priorities` | Set priorities |
| `/constraints` | Set constraints |

### Think & Solve
| Command | Purpose |
|---|---|
| `/analyze` | Break it down |
| `/compare` | Compare options |
| `/pros-cons` | List pros & cons |
| `/evaluate` | Evaluate ideas |
| `/recommend` | Get a recommendation |
| `/brainstorm` | Brainstorm ideas |
| `/solve` | Solve the problem end to end |
| `/challenge` | Challenge assumptions (red-team) |
| `/think` | Reason step by step (extended thinking) |

### Organize & Structure
| Command | Purpose |
|---|---|
| `/outline` | Create an outline |
| `/structure` | Organize loose content |
| `/bullet` | Make bullet points |
| `/numbered` | Make a numbered list |
| `/table` | Create a table |
| `/summary` | Summarize content |
| `/key-points` | Extract key points |
| `/mindmap` | Create a mind map (Mermaid) |
| `/flowchart` | Create a flowchart (Mermaid) |

### Code & Tech
| Command | Purpose |
|---|---|
| `/code` | Write code |
| `/debug` | Diagnose and fix a bug |
| `/explain` | Explain code or a concept |
| `/optimize` | Improve performance |
| `/refactor` | Refactor code |
| `/test` | Write tests |
| `/convert` | Convert formats |
| `/documentation` | Write docs |
| `/review` | Review content/code — see note above; prefer built-in `/code-review` for diffs |

### Automate & Integrate
| Command | Purpose |
|---|---|
| `/workflow` | Create a repeatable workflow |
| `/automate` | Automate a repetitive task |
| `/api` | Work with an API |
| `/integrate` | Connect / integrate tools |
| `/schedule` | Schedule a reminder or recurring run |
| `/trigger` | Define an event trigger |
| `/tasklist` | Break work into an ordered task list |
| `/checklist` | Produce a verification checklist |

### Personalize & Control
| Command | Purpose |
|---|---|
| `/preferences` | Record working preferences |
| `/memory` | Remember a project fact — see note above (native `/memory` wins) |
| `/tone` | Adjust tone |
| `/style` | Change writing style |
| `/length` | Change length |
| `/format` | Change output format |
| `/reset` | Reset the approach and restart |
| `/clear` | Start a fresh topic — see note above (native `/clear` wins) |

### Power shortcuts
- Combine commands for better results.
- Add context early for better answers.
- Be specific and clear.
- Iterate and refine.
- Save and reuse what works.
