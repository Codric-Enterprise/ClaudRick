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

Prompt-shortcut conventions from the "Claude Command — Complete Reference"
sheet. Entries marked **[cmd]** are implemented as real slash commands in
`.claude/commands/`; the rest are conversational conventions or map to native
Claude Code / app features.

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
| Command | Purpose | |
|---|---|---|
| `/analyze` | Break it down | **[cmd]** |
| `/compare` | Compare options | **[cmd]** |
| `/pros-cons` | List pros & cons | **[cmd]** |
| `/evaluate` | Evaluate ideas | **[cmd]** |
| `/recommend` | Get a recommendation | **[cmd]** |
| `/brainstorm` | Brainstorm ideas | **[cmd]** |
| `/solve` | Solve the problem | (use `/think`) |
| `/challenge` | Challenge assumptions | **[cmd]** |
| `/think` | Reason step by step | **[cmd]** (extended thinking) |

### Organize & Structure
| Command | Purpose | |
|---|---|---|
| `/outline` | Create an outline | **[cmd]** |
| `/structure` | Organize content | (use `/outline`) |
| `/bullet` | Make bullet points | |
| `/numbered` | Make a numbered list | |
| `/table` | Create a table | **[cmd]** |
| `/summary` | Summarize content | **[cmd]** |
| `/key-points` | Extract key points | **[cmd]** |
| `/mindmap` | Create a mind map | **[cmd]** (Mermaid) |
| `/flowchart` | Create a flowchart | **[cmd]** (Mermaid) |

### Code & Tech
| Command | Purpose | |
|---|---|---|
| `/code` | Write code | (native) |
| `/debug` | Fix issues | (native) |
| `/explain` | Explain code | **[cmd]** |
| `/optimize` | Improve performance | **[cmd]** |
| `/refactor` | Refactor code | **[cmd]** |
| `/test` | Write tests | (native) |
| `/convert` | Convert formats | **[cmd]** |
| `/documentation` | Write docs | (native) |
| `/review` | Review code | use built-in `/code-review` |

### Automate & Integrate
| Command | Purpose | |
|---|---|---|
| `/workflow` | Create a workflow | **[cmd]** |
| `/automate` | Automate tasks | (see `/workflow`) |
| `/api` | Use an API | |
| `/integrate` | Connect tools | (Connectors / MCP) |
| `/schedule` | Set reminders | |
| `/trigger` | Set triggers | |
| `/tasklist` | Create a task list | |
| `/checklist` | Create a checklist | |

### Personalize & Control
| Command | Purpose |
|---|---|
| `/preferences` | Set preferences |
| `/memory` | Manage memory |
| `/tone` | Adjust tone |
| `/style` | Change writing style |
| `/length` | Change length |
| `/format` | Change format |
| `/reset` | Reset conversation |
| `/clear` | Clear context (native `/clear`) |

### Power shortcuts
- Combine commands for better results.
- Add context early for better answers.
- Be specific and clear.
- Iterate and refine.
- Save and reuse what works.
