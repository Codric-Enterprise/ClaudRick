# Claude Commands Pack — 83 commands

For each command: the **slash form** works in Claude Code (type `/name your input`);
the **prompt** below it is what to paste into a normal claude.ai chat (replace
`{your input}`).

Near-duplicates exist because two cheat-sheets were merged: `key-points`/`keypoints`
and `pros-cons`/`proscons` do the same job — keep whichever you prefer.

---

## Focus & Context

### /focus
> Treat the following as the single main objective for this task. Restate it in one sentence, then keep everything that follows aligned to it — flag anything that would drift off-objective. Objective: {your input}

### /context
> Take the following as background context for the current task. Acknowledge the key facts, note anything that changes your approach, and ask about any gap that would materially affect the outcome. Context: {your input}

### /details
> Go deeper on the following: add the specifics, edge cases, and mechanics that a high-level summary leaves out. If details are missing to do this well, list the exact questions you need answered. Topic: {your input}

### /examples
> Give concrete, varied examples of the following — including at least one edge or counter-example. Keep each example short and label what it illustrates. Concept: {your input}

### /clarify
> Before answering, ask the follow-up questions needed to remove ambiguity from the following. List them in priority order, and say why each one matters to the result. Don't proceed until the load-bearing ones are resolved. Request: {your input}

### /define
> Define the following term(s) precisely: a one-line plain-language definition, then the nuance or common misconception, then how the term is used in this context. Distinguish it from any term it's often confused with. Term(s): {your input}

### /assumptions
> Surface the assumptions behind the following — both stated and unstated. Mark each as safe, uncertain, or risky, and note which ones the outcome depends on most. Subject: {your input}

### /priorities
> Rank the following by priority. State the ranking criterion (impact, urgency, effort, dependency), order the items, and explain the top choice. Flag anything that's a prerequisite for the rest. Items: {your input}

### /constraints
> Take the following as hard constraints for the task. Restate them as a checklist, note any that conflict with each other, and keep every proposed solution inside them — call out explicitly if a good option would require breaking one. Constraints: {your input}

---

## Think & Solve

### /think
> Think hard about the following before answering. Work through it step by step: restate the problem, lay out the options and their trade-offs, check your reasoning for errors, then give the conclusion with your confidence and what would change it. Problem: {your input}

### /analyze
> Break the following down into its component parts: sub-problems, dependencies, unknowns, and the key decision points. Surface anything ambiguous before concluding. Target: {your input}

### /compare
> Compare the options below across the dimensions that matter for the decision (cost, effort, risk, maintainability, speed, and any domain-specific ones). Present a compact table, then name the situations where each option wins. Options: {your input}

### /pros-cons  (also /proscons)
> List the pros and cons of the following. Be concrete and weight them — mark which points are decisive versus minor. End with a one-line net assessment. Subject: {your input}

### /evaluate
> Evaluate the following against clear, stated criteria. For each criterion give a short judgment and evidence, then a summary verdict with confidence level. Call out what would change the verdict. Idea: {your input}

### /recommend
> Give a single clear recommendation for the following, not a survey. Lead with the recommendation, then the top 2–3 reasons, then the main trade-off you are accepting. State your confidence. Question: {your input}

### /brainstorm
> Brainstorm ideas for the following. Go wide first (include a few unconventional options), then cluster them into themes, then flag the 3 most promising with a one-line reason each. Goal: {your input}

### /solve
> Solve the following. Restate the problem, choose an approach (and say why), work to a concrete answer, then verify the answer against the original constraints. Show the key steps, not every keystroke. Problem: {your input}

### /challenge
> Red-team the following. List the load-bearing assumptions, then attack each: where could it fail, what evidence is missing, what's the strongest counter-argument? Finish with the single biggest risk. Target: {your input}

---

## Organize & Structure

### /outline
> Create a clear hierarchical outline for the following — main sections with nested sub-points, ordered logically. Keep each line short. Subject: {your input}

### /structure
> Organize the following into a clear structure: group related items, order the groups logically, and add headings. Don't drop or invent content — just impose order. Content: {your input}

### /bullet
> Rewrite the following as clean bullet points — one idea per bullet, parallel phrasing, no filler. Use one level of nesting only where it genuinely helps. Content: {your input}

### /numbered
> Rewrite the following as a numbered list. Use numbering to convey order or sequence (steps, ranked items). Keep each item to one action or idea. Content: {your input}

### /table
> Organize the following into a clean Markdown table. Infer sensible columns if they aren't given, keep cells terse, and don't invent data — leave unknown cells blank. Data: {your input}

### /summary
> Summarize the following. Give a one-sentence TL;DR, then 5–10 bullets covering the substance, then any open questions or caveats. Preserve exact meaning; do not add claims that aren't in the source. Content: {your input}

### /key-points  (also /keypoints)
> Extract only the key points from the following as a tight bullet list — the things someone must know, nothing filler. Bold the single most important point. Content: {your input}

### /mindmap
> Build a mind map of the following as a Mermaid `mindmap` diagram in a fenced ```mermaid``` block: central node, main branches, and sub-branches. Keep labels to a few words. Topic: {your input}

### /flowchart
> Draw the following process as a Mermaid `flowchart TD` in a fenced ```mermaid``` block. Include decision branches and end states. Keep node labels short. Process: {your input}

---

## Code & Tech

### /code
> Write code for the following. Match the surrounding project's language, style, and conventions. Keep it minimal and correct, handle the obvious edge cases, and briefly note anything you assumed or left out. Show how to run or test it. Task: {your input}

### /debug
> Debug the following. Form a hypothesis about the root cause, confirm it against the code/evidence before changing anything, then apply the minimal fix and state how to verify it's resolved. Note any related latent bugs you spot. Problem: {your input}

### /explain
> Explain the following clearly. Start with a one-line "what it is / what it does," then how it works step by step, then any gotchas. For code, reference specific `file:line` locations. Match the depth to the audience if one is stated. Target: {your input}

### /optimize
> Optimize the following code. First measure or reason about where the real cost is, then propose changes ranked by impact-to-effort. Show the diff and state the expected win and any risk. Don't change behavior without saying so. Target: {your input}

### /refactor
> Refactor the following for clarity and maintainability while preserving behavior. Explain the smell you're addressing, make the change match surrounding style, and confirm tests still pass (or note which to run). Target: {your input}

### /test
> Write tests for the following. Cover the happy path, edge cases, and failure modes. Match the project's existing test framework and layout. Make the tests deterministic and independent, then note how to run them. Target: {your input}

### /convert
> Convert the following into the requested target format (e.g. JSON↔CSV↔YAML, Markdown↔HTML, one language→another). Preserve all data and meaning, and flag anything that can't map cleanly. Request: {your input}

### /documentation
> Write documentation for the following. Lead with what it is and when to use it, then usage with a concrete example, then parameters/return/errors and any gotchas. Match the surrounding docs' tone and format. Don't document behavior you haven't verified. Target: {your input}

### /review
> Review the following and report issues most-important first: correctness, clarity, and consistency, with a concrete fix for each. Separate must-fix from nice-to-have, and note what's already good. Target: {your input}

---

## Automate & Integrate

### /workflow
> Turn the following into a repeatable workflow: numbered steps, the input/output of each, decision points, and where a human check is needed. Note which steps could be automated (script, CI, etc.) and how. End with the trigger that should start the workflow. Task: {your input}

### /automate
> Figure out how to automate the following. Identify the manual steps, pick the right mechanism (script, cron, CI job, MCP tool), and produce the concrete automation plus how to trigger and verify it. Note anything that must stay a manual/human check. Task: {your input}

### /api
> Help use the following API. Identify the right endpoint(s), required auth, parameters, and response shape, then give a minimal working request example and handle errors/rate limits. Prefer the official docs; don't invent endpoints or fields. Request: {your input}

### /integrate
> Plan an integration between the following tools/systems. Define what data flows which way, the connection method (API, webhook, connector, file exchange), auth, and failure handling. Give the concrete steps to wire it up and how to test the round trip. Integration: {your input}

### /schedule
> Set up scheduling for the following. Translate the timing into a concrete schedule (e.g. cron expression or one-shot time), state what runs and what it produces, and note timezone and what happens on failure or a missed run. Schedule: {your input}

### /trigger
> Define a trigger for the following: the event that fires it, the condition to match, and the action to take. Specify how the event is detected (webhook, file watch, poll), and add a guard against firing on the wrong thing or firing twice. Trigger: {your input}

### /tasklist
> Break the following into an ordered task list. Each task should be a concrete, single-outcome action, sequenced by dependency, with blockers marked. Keep it actionable — no vague "figure out" items. End with the first task to start. Goal: {your input}

### /checklist
> Produce a checklist for the following as `- [ ]` items — the things to verify or do, in order, each independently checkable. Cover the easy-to-forget steps. Subject: {your input}

---

## Personalize & Control

### /preferences
> Take the following as my working preferences and apply them to your responses from here on: restate them back as a short list so we're aligned, then follow them. Ask before overriding one when a task would benefit from doing so. Preferences: {your input}

### /memory
> Remember the following and apply it going forward. If it's a durable fact or convention, propose where to record it so it persists. To remember: {your input}

### /tone
> Adjust the tone as requested below (e.g. formal, friendly, direct, diplomatic). Change only the tone — keep the facts, meaning, and structure intact. Request: {your input}

### /style
> Rewrite in the requested style below (e.g. plain English, technical, executive summary, marketing). Preserve the underlying meaning and any specifics; change voice, vocabulary, and rhythm to fit. Request: {your input}

### /length
> Adjust length as requested below. To shorten: cut redundancy and keep the substance. To lengthen: add real detail and examples, not padding. Request: {your input}

### /format
> Reformat into the requested shape below (e.g. table, bullets, numbered steps, JSON, headings). Keep all content; change only presentation. Request: {your input}

### /reset
> Set aside the approach taken so far and restart clean. Briefly confirm what we're keeping (goal, constraints) versus discarding (the prior approach), then begin fresh. New direction: {your input}

### /clear
> Drop the prior topic from active focus and start fresh on the new topic below. Don't carry over assumptions from the previous thread. New topic: {your input}

---

## Write & Edit

### /write
> Write the following as requested. Establish the audience, purpose, and format first (ask if unclear), then produce a clean draft. Match the requested tone, keep it tight and free of filler, and don't fabricate facts. Brief: {your input}

### /edit
> Edit the text below for clarity, flow, and correctness while preserving the author's meaning and voice. Return the edited version, then a short list of the substantive changes you made. Text: {your input}

### /rewrite
> Rewrite the following to be clearer and stronger. Keep the meaning; improve structure, word choice, and rhythm. If a goal is given (shorter, friendlier, more formal), optimize for it. Don't add or drop information. Text: {your input}

### /shorten
> Shorten the following without losing substance. Cut redundancy, hedging, and filler; keep every key fact and the original meaning. Aim for the tightest version that still reads well. Text: {your input}

### /expand
> Expand the following with real substance — detail, examples, context, and reasoning — not padding. Keep the original intent and voice. Flag anything you added that should be fact-checked. Text: {your input}

### /improve
> Improve the writing below for clarity, concision, flow, and impact while preserving meaning and voice. Return the improved version, then note the top 3 changes and why. Text: {your input}

### /paraphrase
> Paraphrase the following in fresh wording while keeping the exact meaning. Don't echo the original phrasing, and don't add or drop information. If a register is specified, match it. Text: {your input}

---

## Data & Analysis

### /insights
> Extract the meaningful insights from the data/text below — patterns, outliers, and what they imply — not just a restatement of the numbers. Rank by importance and note your confidence. Don't invent data. Data: {your input}

### /forecast
> Produce a forecast from the following. State your method and assumptions, give the projection as a range (not false-precision single numbers), and list what would change it. Be explicit about uncertainty; don't fabricate data. Basis: {your input}

### /report
> Turn the following into a structured report: a short executive summary, then findings with supporting detail, then recommendations / next steps. Keep every claim traceable to the source and mark anything assumed. Material: {your input}

### /stats
> Summarize the key statistics for the data below: relevant totals, averages, spread/distribution, and notable comparisons. Show the calculation basis, and state any assumption about missing/ambiguous values rather than guessing silently. Data: {your input}

### /clean
> Clean the data below: identify duplicates, inconsistent formats, missing values, and likely errors, then return the cleaned version plus a change log of what you fixed. Ask before dropping anything ambiguous — never silently discard rows. Data: {your input}

---

## Learn & Research

### /research
> Research the following in depth. Lay out what's known, the key perspectives or debates, and the current state of evidence. Distinguish well-established facts from contested or uncertain points, and note where a claim would need checking against a live source. Don't fabricate sources, figures, or quotes. Topic: {your input}

### /learn
> Help me learn the following. Start from what a beginner needs, build up in a logical order, and use concrete examples. Flag the common misconceptions, and end with a couple of quick questions to check understanding. Topic: {your input}

### /sources
> Suggest where to find reliable information on the following: the types of sources worth trusting and specific well-known ones. Do NOT invent URLs, titles, or citations — if unsure a source exists, say what to search for instead. Topic: {your input}

### /explore
> Explore the following broadly: the main sub-areas, adjacent ideas, open questions, and interesting angles worth pursuing. Aim to widen the map, not to conclude. End with a few threads most worth going deeper on. Topic: {your input}

---

## Collaborate

### /email
> Draft an email for the following. If the recipient or goal is unclear, ask first; otherwise produce a subject line and a concise, appropriately-toned message with a clear ask or next step. Offer a shorter or warmer variant if it would help. Details: {your input}

### /feedback
> Give constructive feedback on the following. Lead with what genuinely works, then the most important issues with specific, actionable fixes ranked by impact. Be candid but kind, and separate must-change from optional polish. Subject: {your input}

---

## Content tools (text transforms)

### /eli5
> Explain the following in plain, jargon-free language someone with no background could follow. Use one short everyday analogy, keep it to a few sentences, and don't oversimplify to the point of being wrong. {your input}

### /tldr
> Summarize the text below. Give a one-sentence TL;DR, then 3–5 bullets capturing the essentials. Preserve critical numbers, names, and caveats. Do not add anything that isn't in the source. {your input}

### /factcheck
> Extract the factual, checkable claims from the text below. For each: state the claim, your assessment (supported / unsupported / misleading / uncertain), and a one-line reason. Flag anything you cannot verify rather than guessing. {your input}

### /proofread
> Proofread the text below. Return the corrected version, preserving the author's meaning, tone, and voice — fix only grammar, spelling, punctuation, and obvious slips. Then list the notable changes you made. {your input}

### /glossary
> Scan the text below for jargon, acronyms, and dense domain terms. Return a glossary: each term with a one-line plain-language definition as used in this context. Sort alphabetically. {your input}

---

## Structure & setup (2026 cheat sheet)

See [`claude-2026-cheatsheet.md`](claude-2026-cheatsheet.md) for the sheets these
came from.

### /brief
> Turn the following into a structured brief before doing any work. Fill in: Task (the single outcome), Context (background that changes the approach), Inputs/files (what's provided vs. missing), Constraints (scope/tone/tech/length/deadlines), Success criteria (how "done" is judged), and Output format (exact shape of the deliverable). Then list any clarifying questions and only start once the brief is settled. Request: {your input}

### /about-me
> Help me build an about-me.md core file — the profile Claude reads before acting, covering my role & context, goals, voice (and what to avoid), priorities, and default formats/tone/units. If my details are thin, ask up to 6 high-signal questions first; then output a concise, copy-paste-ready about-me.md with clear headings and a one-line note on where to put it. Details: {your input}

### /model-picker
> Recommend which Claude model fits the task below, matching capability to the job: Haiku 4.5 for bulk/simple triage and transforms; Sonnet 5 as the everyday default; Opus 4.8 for deep reasoning, writing, and strategy; Fable 5 for the hardest long-horizon work; Mythos 5 only for approved organizations' high-security workflows. Give the recommended model, the signals that drove the choice, what would escalate it a tier, and a per-phase split if the task has phases. Task: {your input}

---

## Repo-specific dev commands (ReVision — Claude Code only)

These run shell/CI actions and only make sense inside the repo in Claude Code.

- **/check** — run the CI gate: `ruff check .`, `ruff format --check .`, `pytest`.
- **/run-app** — start the ReVision server (`revision`, serves :8000).
- **/smoke** — curl `/healthz`, `/`, and `/api/messages` to verify the server.
