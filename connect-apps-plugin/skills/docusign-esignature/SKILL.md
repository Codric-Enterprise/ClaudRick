---
name: docusign-esignature
description: >-
  Deep guide to running e-signature workflows through a connected Docusign
  MCP server — creating envelopes from templates, managing recipients and
  routing, tracking status, and triggering Docusign Workflows (formerly
  CLM/Maestro-style multi-step agreement flows). Use when the user wants to
  send something for signature, check on a pending envelope, remind a
  signer, or automate a multi-step agreement process. Triggers on "send for
  signature", "docusign", "envelope", "get this signed", "e-signature",
  "signing workflow".
---

# Docusign e-signature

Docusign's object model has three layers that matter for almost every task:
**account** (the tenant), **envelope** (one signing transaction — the
document(s) plus its recipients and fields), and **template** (a reusable
envelope skeleton). Workflows are a separate, higher-level layer that
sequences multiple envelopes/steps together (approvals, conditional routing,
multi-party agreements).

## Before you start

1. Confirm the Docusign MCP server is actually connected and authorized in
   this session. If its tools aren't available, or a call fails with an auth
   error, tell the user to authorize it (via `claude mcp` / `/mcp` in an
   interactive session, or their connector settings) rather than guessing at
   credentials or retrying blindly.
2. Call `getAccount` / `getUserInfo` first if you're unsure which account or
   user context you're operating in — Docusign is multi-account, and sending
   from the wrong account is a real, hard-to-undo mistake (the recipient gets
   an email).
3. Sending an envelope emails a real person. Treat `createEnvelope` and
   `createEnvelopeFromTemplate` as **user-confirm-first** actions unless the
   user has clearly already approved the exact recipients and document, the
   same way you'd treat any other action that's visible to a third party.

## Core workflow: send something for signature

**Prefer templates over ad-hoc envelopes** whenever one exists — templates
pre-define the document, signing fields (tabs), and often the recipient
roles, which eliminates most of the ways an ad-hoc envelope goes wrong
(missing signature field, wrong recipient order).

1. `getTemplates` to find the right template (or confirm one doesn't exist
   and an ad-hoc `createEnvelope` is genuinely needed).
2. `createEnvelopeFromTemplate`, supplying the recipient(s) mapped to the
   template's roles. Get name + email exactly right — Docusign does not
   validate that the email belongs to the intended person, so a typo silently
   sends a legal document to a stranger.
3. If recipients or field placement need to differ from the template
   defaults, use `updateEnvelopeRecipients` / `updateEnvelopeTabs` **before**
   the envelope leaves draft status — once it's sent, recipient/tab changes
   are much more constrained.
4. Confirm send status back to the user with the envelope ID, not just "sent"
   — it's the handle for every follow-up action.

## Tracking and follow-up

- `getEnvelope` / `getEnvelopes` for status (`sent`, `delivered`, `completed`,
  `declined`, `voided`). Poll on request, not on a tight loop — Docusign
  status changes on human timescales (someone has to open an email and sign).
- `listRecipients` to see per-recipient status when an envelope has multiple
  signers and only one action is described as blocking ("waiting on legal to
  sign").
- `sendReminder` rather than re-sending the whole envelope when a signer is
  slow — re-sending creates a duplicate signing experience and confuses
  recipients.
- `listEnvelopeDocuments` to retrieve the documents themselves, e.g. once
  `completed`, for archival or to hand back to the user.

## Workflows (multi-step agreement automation)

Docusign Workflows sit above individual envelopes — use them when the ask is
"whenever X happens, kick off this multi-step signing/approval process," not
"send this one document."

- `getWorkflowsList` / `getWorkflowTriggerRequirements` to find the right
  workflow and learn what input it needs before triggering it — workflows
  often require specific field values (a contract amount, a counterparty
  name) that aren't optional.
- `triggerWorkflow` to start an instance; `getWorkflowInstance` /
  `getWorkflowInstancesList` to check on running instances.
- `pauseNewWorkflowInstances` / `resumeWorkflow` for operational control
  (e.g. a legal freeze) — these affect **future** instances or a paused
  instance, not in-flight envelopes already sent; be explicit with the user
  about that distinction so they don't assume a pause recalls a live
  signature request.
- `cancelWorkflowInstance` only when the user genuinely wants to abort a
  running multi-step process — this is the workflow-level equivalent of
  voiding, and like voiding, it's user-visible and not silently reversible.

## Common pitfalls

- **Wrong account context.** Multi-account Docusign setups are common in
  orgs; always sanity-check `getAccount` before a send if there's any
  ambiguity.
- **Assuming instant completion.** `createEnvelope*` returns once the
  envelope is *sent*, not once it's *signed*. Don't report a task as "done"
  until you've confirmed the actual status the user cares about.
- **Skipping `getUsers`/`getUser` for role resolution.** Templates often
  reference roles by name ("Signer 1"), not a real person — resolve the
  actual recipient before creating the envelope, don't let a placeholder
  reach send.
- **Treating recipient tabs as decorative.** Tabs (signature, date, initial,
  text fields) are positioned on the document; get `updateEnvelopeTabs`
  wrong and a signature lands on the wrong page or the wrong clause.

## Pre-send checklist

- [ ] Correct Docusign account/context confirmed
- [ ] Template used where one exists; ad-hoc envelope only when it doesn't
- [ ] Every recipient's name + email verified against what the user provided
      (no placeholder roles left unresolved)
- [ ] Recipient order / routing matches the intended signing sequence
- [ ] User has explicitly confirmed sending (this emails a real person)
- [ ] Envelope ID captured and given back to the user for follow-up
