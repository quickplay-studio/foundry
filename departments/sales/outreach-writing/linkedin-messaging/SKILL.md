---
name: linkedin-messaging
title: LinkedIn Messaging
department: sales
function: outreach-writing
autonomy: solo
stage: sell
builds_on: [personalisation-research]
breaks_into: [write-connection-note, write-follow-up-dms, check-length-and-tone, build-daily-queue]
replaces: "a LinkedIn Sales Navigator seat and DM automation tools"
runs_on: github
status: ready
---

# LinkedIn Messaging

Draft connection notes and DM sequences that read like a person wrote them.

## Reads from the brain
- `brain/company.md`: voice, constraints
- `ventures/<slug>/brain.md`: problem, mvp, money

## Inputs
- `sell/dossiers/<id>.md` for tier A leads, `sell/icp.md`, `sell/proof.json`.
- `sell/leads.csv` rows with a `linkedin_url` pasted by Charlie.

## Steps
1. Gate: `audit.json` must say `model: b2b`, else write a `skipped` line in `board.json` and stop.
2. Per segment write the connection note: 200 characters or fewer (check LinkedIn's current limit; free accounts are tighter), no pitch, no link, one specific reason taken from the dossier opener.
3. DM 1 after acceptance: thanks, one sentence on what the product does with the price, one question. 60 words or fewer.
4. DM 2 five days later: one useful point or the proof line. DM 3 ten days later: a polite close. Nothing after that.
5. Style: no "I hope this finds you well", no emoji, no stacked adjectives, no obvious template. Each message cites one real fact from the dossier.
6. Rules: the job writes, Charlie sends by hand from his own account. No browser extension, no automation, no scraping. At most 15 invites a day, well under LinkedIn's weekly limit (as of Oct 2026, check it).
7. PECR: treat direct messages like email. Write only to people in business roles at companies, say who Charlie is, and stop at the first "no" or "stop": add the person to `suppression.csv` with reason `linkedin-no`. Legal `data-protection` has the final wording.
8. Each day build `linkedin-queue.md`: lead id, name, profile URL, the exact text to send, and a tick box. Charlie ticks what he sent, and the next run logs it to `sent.csv` with channel `linkedin`.

## Output
- `ventures/<slug>/sell/sequences/linkedin-<segment>.md`: the note and three DMs, with merge fields.
- `ventures/<slug>/sell/linkedin-queue.md`: today's batch.

## The ladder
- Human-led: Charlie writes and sends his own notes.
- Human-assisted: the job drafts and queues, Charlie sends. This is the working mode.
- Fully autonomous: not available. LinkedIn is by hand, always.

## The human
What stays with Charlie: sending every note and message, and answering replies.

## Tools
Gemini 2.5 Flash then Groq for drafting (as of Oct 2026, check the limit). No LinkedIn tool of any kind.

## Build notes
- Length check is code. Tests: a 201-character note fails; a message with no dossier fact fails.
- Keep the queue to tier A and 15 rows at most.
