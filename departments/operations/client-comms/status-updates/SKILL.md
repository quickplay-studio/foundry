---
name: status-updates
title: Status Updates
department: operations
function: client-comms
autonomy: solo
stage: run
builds_on: []
breaks_into: [read-board, draft-update, check-numbers, publish-update]
replaces: "a project manager's weekly update email"
runs_on: github
status: ready
---

# Status Updates

Progress goes out before anyone has to ask for it.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof

## Inputs
- `ventures/<slug>/board.json`: stage, gates, jobs and their statuses, `incidents`, `skipped`.
- `ventures/<slug>/budget.json`: `ad_budget`, `spent`, `revenue`.
- `ventures/<slug>/qa/result.json` if present.
- `ventures/<slug>/status/latest.md`, the previous update, for the date and for what to leave out.

## Steps
1. Read the board and list what changed since the date in `latest.md`: jobs moved to `done`, gates changed, incidents opened or resolved, `skipped` lines added.
2. If nothing changed and the last update is under 7 days old, write nothing. No empty updates.
3. If nothing changed for 7 days, write a one-line "no change" update that names the blocker (the next gate and what it waits for).
4. Build a facts object from the JSON: stage, done list, next gate, blockers, open incidents (count), spend and revenue in pounds. All numbers come from the files, never from the model.
5. Draft the update through the model chain in `foundry/util.py` (`ask_json`: Gemini, then Groq, then a template). Fixed shape, 5 lines at most: where we are; done since the last update; next and what it waits for; what is needed from Charlie; spend against budget in one line. Voice from `brain/company.md`: plain, short, UK English, no dashes, no exclamation marks.
6. Check the numbers: every figure in the draft must appear in the facts object. If one does not, discard the draft and render the template without a model.
7. Publish: write `status/<YYYY-MM-DD>.md`, copy it to `status/latest.md`, and comment on one pinned issue `status: <slug>` in Foundry so GitHub notifies Charlie. If the venture has a portal, add `latest_update` to the facts for `portal-sync`.
8. Set this job in `board.json` to `done` with the file path in `output`.

## Output
- `ventures/<slug>/status/<YYYY-MM-DD>.md` and `status/latest.md`: the update, 5 lines or fewer.
- A comment on the issue `status: <slug>`. No email is sent from here.

## The ladder
- Human-led: Charlie writes each update.
- Human-assisted: the job drafts into a pull request, Charlie edits.
- Fully autonomous: the job writes and posts. This is the default; anything that goes to a customer is sent by Charlie himself.

## The human
What stays with Charlie: sending anything to a customer, and deciding what a customer may know about a delay.

## Tools
Free first. GitHub Actions on a Monday 07:00 UK cron and on a push that changes `board.json`; GitHub issues for notification. Gemini 2.5 Flash then Groq for wording only. No Claude.

## Build notes
- The model is a copy editor. It never decides what happened.
- The fifth line starts with `Spend:` and is for Charlie only. `portal-sync` removes it before anything is shared.
- Keep each update under 600 characters.
- Cron runs in UTC. Set it for 06:00 and 07:00 UTC to cover British Summer Time, and skip the second run if an update for today exists.
- GitHub implementation: `run.py` beside this file (jobkit).
