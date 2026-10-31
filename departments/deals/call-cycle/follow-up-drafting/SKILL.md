---
name: follow-up-drafting
title: Follow-Up Drafting
department: deals
function: call-cycle
autonomy: assisted
stage: sell
builds_on: [post-call-debrief]
breaks_into: [load-debrief, draft-recap, create-gmail-draft, track-sent]
replaces: "an account executive writing a recap email after every call"
runs_on: github
status: ready
---

# Follow-Up Drafting

Draft the recap email with next steps before the prospect forgets the call.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof
- `ventures/<slug>/sell/recaps/`: earlier recaps, so the tone and structure stay consistent

## Inputs
- `ventures/<slug>/sell/debriefs/<deal_id>-<yyyymmdd>.json` with no matching recap.
- The Gmail thread for the deal (scope `gmail.compose` for drafts, `gmail.readonly` to see sends).
- Repository variable `CALCOM_BOOKING_URL`; approved price file `sell/pricing/<deal_id>.md` if one exists.

## Steps
1. Find debriefs with no file in `sell/recaps/`.
2. Draft with Gemini 2.5 Flash (Groq as fallback), 180 words or fewer: a one-line thank you, "What we heard" as three bullets in the prospect's own words (verified quotes only), "What we agreed" as actions with owner and date, and the next step with the booking link if a second call is needed.
3. Do not mention a price unless the debrief records an agreed figure and `sell/pricing/<deal_id>.md` has `approved: true`. Do not promise a date that is not in the debrief. Do not name a file as attached unless it exists.
4. Subject: `Notes from today and next steps`. Voice from `brain/company.md`: plain, no hype, UK English.
5. Save to `sell/recaps/<deal_id>-<yyyymmdd>.md` with a header block (`to`, `subject`, `thread_id`, `status`) and the body.
6. Create a Gmail draft in the same thread. Never send.
7. On later runs, if the thread shows a message from us after the draft, set `status` `sent` and `last_touch` in `pipeline.csv`.
8. If a draft is still unsent 24 hours after the call, add a comment on the deal issue as a reminder, once.

## Output
- `ventures/<slug>/sell/recaps/<deal_id>-<yyyymmdd>.md`: header block plus the email body.
- A Gmail draft in the thread, ready to send.

## The ladder
- Human-led: Charlie writes the recap from memory the next day.
- Human-assisted: the job drafts within two hours of the call and Charlie edits and sends.
- Fully autonomous: not used; a recap commits us to dates and scope, so a human sends it.

## The human
What stays with Charlie: reading, editing and sending every recap, and any commitment in it.

## Tools
Gmail API drafts (as of Oct 2026, check the limit), Gemini 2.5 Flash then Groq (as of Oct 2026, check the limit), GitHub Actions hourly.

## Build notes
- Speed matters more than polish: aim for a draft ready within two hours of the call ending.
- Quotes in the draft must come from the debrief's verified list, not the model's memory.
- On failure add one line under `skipped` in `ventures/<slug>/board.json` with the reason.
