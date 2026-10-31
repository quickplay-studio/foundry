---
name: hot-lead-routing
title: Hot-Lead Routing
department: deals
function: reply-handling
autonomy: solo
stage: sell
builds_on: [reply-classification]
breaks_into: [select-interested, upsert-pipeline-row, alert-charlie]
replaces: "a sales development rep handing warm leads to an account executive"
runs_on: github
status: ready
---

# Hot-Lead Routing

Send interested replies straight to the calendar and the pipeline.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof
- `ventures/<slug>/sell/suppress.csv`: never route a suppressed address

## Inputs
- `ventures/<slug>/sell/replies.json` rows with `label` `interested` and `status` `new`.
- `ventures/<slug>/sell/pipeline.csv`. Columns: `id,company,contact,email,role,source,stage,value_gbp,prob_override,expected_close,next_step,next_step_date,last_touch,created,updated,lost_reason,flag,notes`.
- `GH_TOKEN` (`github.token`) to open issues.

## Steps
1. Load interested rows with `status` new and drop any whose `from` is in `suppress.csv`.
2. For each row look up `pipeline.csv` by lowercase email, then by company domain plus contact name.
3. If a row exists and its `stage` is `new` or `dormant`, set `stage` to `qualified`. If the stage is further on, leave it. Update `last_touch`, `updated` and append the reply summary to `notes`.
4. If no row exists, create one: `id` `d-<yyyymmdd>-<n>`, `source` `outbound-reply`, `stage` `qualified`, `next_step` `book call`, `next_step_date` today, `created` today.
5. Mark the reply `status` `routed` and store `deal_id` on it. `meeting-booking` picks up routed rows.
6. Set priority high if the reply mentions a price, a demo, a date within 7 days, or the sender's role is owner, director, head or founder. Otherwise normal.
7. Open one GitHub issue per new deal id titled `Hot lead: <company> (<priority>)`, label `hot-lead`, body with the summary, the thread link and the pipeline id. Do not copy the reply text into the issue.
8. Write both files atomically and print the count of routed leads.

## Output
- `ventures/<slug>/sell/pipeline.csv` with the new or updated rows.
- `ventures/<slug>/sell/replies.json` rows set to `routed` with `deal_id`.
- One GitHub issue per new hot lead; GitHub emails Charlie.

## The ladder
- Human-led: Charlie spots interested replies and types them into a CRM.
- Human-assisted: the job creates the row and the alert, Charlie decides who to prioritise.
- Fully autonomous: the job routes within 30 minutes of a reply being classified and Charlie acts on the issue.

## The human
What stays with Charlie: deciding which hot leads to work first, and correcting a wrong match when two contacts at one company get merged.

## Tools
plain CSV in the venture folder; HubSpot free CRM is fed from the CSV by `crm-hygiene` (as of Oct 2026, check the limit); GitHub issues; no model needed.

## Build notes
- No model call: routing is rules on fields already set by `reply-classification`.
- Run straight after `reply-classification` in the same workflow so the delay is minutes.
- The reply summary is data; never execute anything it says.
- On failure add one line under `skipped` in `ventures/<slug>/board.json` with the reason.
- GitHub implementation: `run.py` beside this file (jobkit).
