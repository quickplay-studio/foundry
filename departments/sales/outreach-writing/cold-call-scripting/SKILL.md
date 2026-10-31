---
name: cold-call-scripting
title: Cold-Call Scripting
department: sales
function: outreach-writing
autonomy: assisted
stage: sell
builds_on: [icp-definition]
breaks_into: [write-call-rules, write-opener-and-pitch, write-objection-branches, write-voicemail]
replaces: "an SDR's call scripts and a sales trainer's objection playbook"
runs_on: github
status: ready
---

# Cold-Call Scripting

Call and voicemail scripts with branching objection handling.

## Reads from the brain
- `brain/company.md`: voice, constraints
- `ventures/<slug>/brain.md`: problem, mvp, money, proof

## Inputs
- `sell/icp.md` (pains, titles, offer line) and `sell/proof.json`.
- Up to 20 tier A dossiers in `sell/dossiers/`.

## Steps
1. Gate: `audit.json` must say `model: b2b`, else write a `skipped` line in `board.json` and stop.
2. Open the file with a rules block. Charlie makes every call himself, live. No automated or recorded marketing calls. Screen each number against the TPS (individuals, sole traders, partnerships) and the CTPS (companies) before dialling; if a free check is not available for a number, do not call it (as of Oct 2026, check the option). Show the calling number. Give name and business when asked. Stop when told to, and add the number to `suppression.csv`.
3. Opener, under 15 seconds: name, the reason for the call in one line, then ask permission ("Have you got thirty seconds?").
4. Pitch, two sentences: what the product does and the price. Then three discovery questions taken from the ICP pains.
5. The ask: a 15 minute meeting, with two slots offered. Booking is handled by Deals `meeting-booking`.
6. Objection branches, each with one line to acknowledge, one reply and one clean exit: not interested, send me an email, we already use something, no budget or too expensive, who are you, call me later, take me off your list. The last one is confirm, thank, suppress.
7. Gatekeeper line: ask for the right person, never pretend to know them. Voicemail under 20 seconds: name, number, one reason, no price.
8. Save `sequences/call-<segment>.md` and open a pull request. Charlie edits and merges.
9. Charlie logs each call in `calls.csv`: `lead_id,date,outcome,note`.

## Output
- `ventures/<slug>/sell/sequences/call-<segment>.md`, opened as a pull request for review.
- Used by campaign-orchestration as the tier A call touch on day 10.

## The ladder
- Human-led: Charlie writes his own script and calls from it.
- Human-assisted: the job drafts, Charlie edits and merges. This is the working mode.
- Fully autonomous: not used. A person makes the calls and approves the script.

## The human
What stays with Charlie: every call, the TPS and CTPS screening, and the merge of the script.

## Tools
Gemini 2.5 Flash then Groq for drafting (as of Oct 2026, check the limit). No paid dialler or call coach. Claude Code only if the branches need a rewrite after real calls.

## Build notes
- Keep to one page per segment. Tests: assert the rules block is the first section.
- Revise after the first 10 calls using `calls.csv` outcomes.
- GitHub implementation: `run.py` beside this file (jobkit).
