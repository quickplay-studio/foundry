---
name: reactivation
title: Reactivation
department: deals
function: pipeline-ops
autonomy: solo
stage: sell
builds_on: [crm-hygiene]
breaks_into: [find-dormant, pick-angle, draft-and-send, enforce-stop-rules]
replaces: "a sales rep running a dormant-deal revival sequence"
runs_on: github
status: ready
---

# Reactivation

Revive dormant deals and win back lost ones on a schedule.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof
- `ventures/<slug>/sell/suppress.csv`: skip these addresses, always
- `ventures/<slug>/brain.md` `proof` line: new evidence is the only honest reason to write again

## Inputs
- `ventures/<slug>/sell/pipeline.csv` rows at `stage` `dormant` or `lost`.
- `ventures/<slug>/sell/replies.json` rows with `label` `not_now` and `snooze_until` in the past.
- `ventures/<slug>/sell/reactivation.json`, the log of earlier attempts (empty if missing).
- Gmail scopes `gmail.send`, `gmail.readonly`.

## Steps
1. Run Tuesday to Thursday between 09:00 and 16:00 UK, at most 10 sends per run.
2. Eligible: dormant 30 days or more since `last_touch`; lost with `lost_reason` price, timing or competitor for 90 days or more; `not_now` replies past `snooze_until`. Not eligible: reason `never`, `no_need` or `fit`, anything in `suppress.csv`.
3. Only people we have already had a two-way conversation with (they replied or took a call). Never cold contacts.
4. At most 2 attempts per person, at least 45 days apart. After the second, set `flag` `cold` and stop for good.
5. Pick an angle from the record: what changed on our side (a real feature or result in the venture brain), what they said was blocking them, or a simple check-in if nothing changed. Never invent news.
6. Draft with Gemini 2.5 Flash (Groq as fallback): 80 words or fewer, one question, sender named, and a closing line "Say stop and I will not write again." Voice from `brain/company.md`.
7. Send in the original thread. Log `{deal_id, sent_at, angle, attempt}` to `reactivation.json`. Set `last_touch` today.
8. Replies come back through `reply-classification`. Any `never` goes to `suppress.csv`; an `interested` reply moves the deal to `qualified` through `hot-lead-routing`.

## Output
- `ventures/<slug>/sell/reactivation.json`: a list of `{deal_id, email, sent_at, angle, attempt, outcome}`. `outcome` is blank, `replied` or `stopped`.
- Sent messages in the original threads; `last_touch` updated in `pipeline.csv`.

## The ladder
- Human-led: Charlie remembers to chase old leads now and then.
- Human-assisted: the job lists who is due and drafts, Charlie sends.
- Fully autonomous: it sends within the limits above; a stop request ends contact at once.

## The human
What stays with Charlie: the first send of the first campaign (review three drafts), any person who replies angrily, and the rule itself. The two-attempt limit and the opt-out line are a safe default, not legal advice; Charlie confirms them with a solicitor once.

## Tools
Gmail API (as of Oct 2026, check the limit), Gemini 2.5 Flash then Groq (as of Oct 2026, check the limit), GitHub Actions weekdays.

## Build notes
- GitHub cron is UTC; the script checks UK local time before sending.
- Honour a stop request immediately by adding the address to `suppress.csv` in the same run.
- On failure add one line under `skipped` in `ventures/<slug>/board.json` with the reason.
- GitHub implementation: `run.py` beside this file (jobkit).
