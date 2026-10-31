---
name: objection-response
title: Objection Response
department: deals
function: reply-handling
autonomy: assisted
stage: sell
builds_on: [reply-classification, objection-library]
breaks_into: [match-objection, draft-reply, queue-draft-for-approval]
replaces: "a sales rep writing a fresh answer to every objection"
runs_on: github
status: ready
---

# Objection Response

Draft answers to common objections from a tuned library.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof
- `ventures/<slug>/sell/objections.json`: the rebuttal library from `objection-library` (if missing, use the starter set in Build notes)

## Inputs
- `ventures/<slug>/sell/replies.json` rows with `label` `objection` and `status` `new`.
- The full Gmail thread for each row (scope `gmail.compose` to create drafts).
- The venture brain `proof` and `money` lines: the only source for facts and prices in a draft.
- Repository variable `CALCOM_BOOKING_URL`.

## Steps
1. Select rows with `label` objection and `status` new. Skip any row with `needs_review` true and list it for Charlie instead.
2. Match `objection_type` to a library entry. If the type is `other` or empty, ask Gemini 2.5 Flash (Groq as fallback) to pick the nearest entry id from the library or return `none`.
3. If the result is `none`, set `status` to `no_match`, add the row to the digest and stop for that row. Never invent a rebuttal.
4. Draft the reply from the entry: one sentence acknowledging their point in their words, the rebuttal in 60 words or fewer, one fact from the venture `proof` line, one question or one next step. Add `CALCOM_BOOKING_URL` only for timing and need objections. Voice from `brain/company.md`: plain, no hype, no exclamation marks, UK English.
5. Check the draft before saving: any price, discount or date must appear in the venture brain or in an approved `sell/pricing/<deal_id>.md`; any number not found there fails the check and the row goes to the digest. Price objections never get a discount offer.
6. Create the reply as a Gmail draft in the same thread (`drafts.create`). Never send.
7. Update the row: `draft_id`, `library_id`, `status` `drafted`. Write the digest of drafts and no-match rows as one GitHub issue titled `Objection drafts <date>`.
8. On the next run, if the thread now holds a message from the campaign mailbox after the draft, set `status` `sent`. Do not change the draft text.

## Output
- Gmail drafts in the original threads, one per matched objection.
- `ventures/<slug>/sell/replies.json` rows updated with `draft_id`, `library_id`, `status`.
- A GitHub issue digest that lists drafts, no-match rows and failed checks.

## The ladder
- Human-led: Charlie writes every answer himself from memory.
- Human-assisted: the job drafts from the library and Charlie edits and sends each one.
- Fully autonomous: not used. Replies about money, terms or complaints always keep a human.

## The human
What stays with Charlie: reading and sending every draft; any concession on price, scope or terms; any thread that mentions security, contracts or a complaint (no draft is made).

## Tools
Gmail API drafts (free; as of Oct 2026, check the limit), Gemini 2.5 Flash then Groq (as of Oct 2026, check the limit), GitHub Actions hourly, GitHub issues for the digest.

## Build notes
- Starter library when `objections.json` is missing: price, timing, authority, need, competitor, trust. Each gets a two-line holding rebuttal built only from the venture brain.
- The assisted gate is the draft itself: nothing leaves the mailbox until Charlie sends it.
- A thread with an earlier sent draft from this job is not drafted again; one draft per reply.
- On failure add one line under `skipped` in `ventures/<slug>/board.json` with the reason.
