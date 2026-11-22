# Graded decisions: a plain-English spec

Audience: people who run payments, trades, claims, or medical coding, and
the people who review their work. No programming is needed to read this.

## The problem with pass or fail

Most automated checks end in one of two answers: go or stop. A system
that is 96% sure and a system that is 51% sure can both show "approved."
A reviewer then has no way to see how close the call was, and the
explanation for a refusal is usually missing.

This spec keeps the whole range. Every result is a **score from 0 to 256**
(0 means no basis at all, 256 means fully verified), and the score is
turned into one of four **bands**. Each band states what the result is
allowed to do.

## The four bands

| Band | What it means | What it may do |
|---|---|---|
| **act** | The evidence is strong enough to act on by itself. | Drive the action (pay, settle, code, send). |
| **review** | Good evidence, but a person has to look first. | Act only after a named person approves. |
| **hold** | Not enough to act. The reason is recorded. | Be shown with its reason. Never acted on. |
| **can't tell** | The needed information is missing or unusable. | Be shown as "can't tell," with the missing piece named. |

Every band can be displayed. Showing a result is never the risk; acting on
an unsure one is.

## Plain words for the score

| Score | Words a reader sees |
|---|---|
| 224 to 256 | very sure |
| 160 to 223 | pretty sure |
| 96 to 159 | not sure |
| 0 to 95 | can't tell |

## The three profiles

Each profile sets where the band lines fall. Pick the profile that matches
the cost of being wrong.

| Profile | Act at | Review at | Hold at | Use when |
|---|---|---|---|---|
| `general` | 224 | 160 | 96 | Reading tone, motive, or risk in a document for a person to read. |
| `clinical_coding` | 224 | 192 | 128 | Suggesting diagnosis or procedure codes. A coder reviews anything short of act. |
| `financial_strict` | 240 | (none) | 128 | Exchanges and financial institutions. Anything short of 240 stops. |

In `financial_strict` there is no review step. A result is either acted on
or stopped, and a stop always comes with its explanation. This is the
profile for trades and settlements.

## Why a result is low: the limiting reason

Every result carries a list of **reasons**. Each reason has:

- a **code** from a fixed list, so causes can be counted across many results:
  `missing_input`, `conflicting_sources`, `below_threshold`, `timeout`,
  `out_of_range`, `unverified_source`, `weak_evidence`, `strong_evidence`;
- a **sentence** a person can read;
- the **evidence**: the exact words or facts from the source that drove
  the score.

The **limiting reason** is the one with the lowest score. It is the first
thing a reviewer is shown, because it is what held the result back.

### Example: a trade under `financial_strict`

A settlement of 2.4 million to a counterparty.

- Amount matches the invoice. Strong evidence, score 256. Evidence: "2,400,000".
- Counterparty account was confirmed by one data feed only. Unverified
  source, score 236. Evidence: "one feed".

Result: score 236, plain words "very sure," band **hold**. The system
shows it and does not settle it. The explanation says the reading is very
sure but the score is below the 240 this profile needs to act, and the
limiting reason is that the account was confirmed by one feed only. The
fix is a second confirmation, not a judgment call by the system.

### Example: a coding suggestion under `clinical_coding`

A suggested diagnosis code drawn from a note.

- The note says "probable pneumonia," which is hedged. Weak evidence,
  score 200. Evidence: "probable pneumonia".
- The chest X-ray report states consolidation. Strong evidence, score 240.
  Evidence: "consolidation".

Result: score 200, plain words "pretty sure," band **review**. A coder
approves or rejects it before it goes onto a claim. The limiting reason is
the hedged wording in the note, so the coder knows what to check.

This example is an illustration of how the bands work. It is not a coding
rule and it does not establish which code is correct.

### Example: missing input

If the discharge summary never arrived, the score is 0, the band is
**can't tell**, and the reason is "discharge summary not received." The
system does not guess a code, and it does not quietly leave the input out.

## What the system never does

- It never averages over missing data. One unknown input makes the result
  unknown, with its reason carried forward.
- It never raises a score. Combining results can only keep it the same or
  lower it. A result is no more certain than its least certain input.
- It never hides a stop. A hold or can't-tell result always comes with its
  explanation.

## Audit trail

Every decision writes one line to an audit log:

- the inputs (each value with its score),
- the score and band,
- the thresholds of the profile used,
- the outcome (for example "settled," "held," "shown," "approved by a reviewer").

The log is append-only. Lines are added to the end and existing lines are
never rewritten by the library. Lines are written with sorted keys and no
timestamp, so the same inputs produce the same bytes.

## Replay

The same inputs under the same profile always produce the same score, band,
and explanation. Anyone with the inputs and the profile name can re-run a
past decision and check it against the audit log. If the thresholds change,
the audit line still records the thresholds that were in force, so an old
decision is judged by the rules it was made under.

## Limits of this spec

- The bands are a policy choice. The numbers are starting points. A
  deployment should set them with the people who carry the risk, and
  record that choice.
- A score is only as good as the evidence behind it. The library does not
  judge whether a source is reliable. It only refuses to hide that a source
  was not checked.
- Nothing here gives medical, legal, or financial advice. It decides when
  a person must look, not what the answer is.
