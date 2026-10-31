---
name: referral-capture
title: Referral Capture
department: deals
function: reply-handling
autonomy: solo
stage: sell
builds_on: [reply-classification]
breaks_into: [extract-referral, check-suppression, add-warm-lead, thank-referrer]
replaces: "a sales rep chasing every speak to my colleague reply"
runs_on: github
status: ready
---

# Referral Capture

Spot the 'talk to my colleague' replies and act on the warm intro.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof
- `ventures/<slug>/sell/suppress.csv`: addresses never to contact

## Inputs
- `ventures/<slug>/sell/replies.json` rows with `label` `referral` and `status` `new`.
- The full thread from Gmail (scopes `gmail.readonly`, `gmail.compose`, `gmail.send`).
- `ventures/<slug>/sell/pipeline.csv`. Columns: `id,company,contact,email,role,source,stage,value_gbp,prob_override,expected_close,next_step,next_step_date,last_touch,created,updated,lost_reason,flag,notes`.

## Steps
1. For each referral row, read the thread and extract `name`, `role`, `email` of the person named, and whether the referrer put them in cc or gave permission ("say I sent you"). Use Gemini 2.5 Flash, Groq as fallback.
2. Use an email address only if it appears in the thread (cc, body, signature). Never guess one from a name or a pattern. If there is none, set `status` `needs_contact`, add it to the digest and stop for that row.
3. Check the address and its sender in `suppress.csv`. A match ends the row with `status` `done`.
4. Create a `pipeline.csv` row: `source` `referral`, `stage` `new`, `notes` "referred by <name> on <date>", `next_step` `intro email`, `next_step_date` today.
5. If the referrer cc'd the person or gave permission, send a short intro from the campaign mailbox that names the referrer in the first line, says what the product does in one line, gives the price if the venture brain has one, asks for 15 minutes and ends with a line saying how to stop further mail. Otherwise save the same text as a Gmail draft for Charlie.
6. Send the referrer one line of thanks in the same thread. Mark the original reply `status` `done`.
7. Never message the referred person twice; a second referral to the same address only adds to `notes`.

## Output
- A new `pipeline.csv` row per referral, with the referrer in `notes`.
- Either a sent intro email or a Gmail draft, and a thank-you line to the referrer.
- `ventures/<slug>/sell/replies.json` row set to `done`, `needs_contact` or `drafted`.

## The ladder
- Human-led: Charlie writes the intro and tracks who referred whom.
- Human-assisted: without cc or permission the job drafts and Charlie sends.
- Fully autonomous: with cc or permission the job sends the intro and logs it.

## The human
What stays with Charlie: sending intros where the referrer gave no permission, and thanking referrers properly after a deal closes.

## Tools
Gmail API (as of Oct 2026, check the limit), Gemini 2.5 Flash then Groq (as of Oct 2026, check the limit), plain CSV, GitHub Actions hourly.

## Build notes
- The referrer's goodwill is the asset: one intro, short, honest, never a sequence.
- Without the referrer's cc or permission the intro is only ever a draft. Every sent intro names the sender and says how to stop further mail. This is a safe default, not legal advice; Charlie confirms it with a solicitor once.
- On failure add one line under `skipped` in `ventures/<slug>/board.json` with the reason.
