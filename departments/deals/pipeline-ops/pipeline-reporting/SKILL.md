---
name: pipeline-reporting
title: Pipeline Reporting
department: deals
function: pipeline-ops
autonomy: solo
stage: sell
builds_on: [crm-hygiene]
breaks_into: [snapshot-pipeline, diff-against-last-week, flag-stalls, write-report]
replaces: "a weekly pipeline review prepared by sales ops or a paid Clari seat"
runs_on: github
status: ready
---

# Pipeline Reporting

Weekly pipeline state: what moved, what stalled, what closes next.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof
- `ventures/<slug>/sell/hygiene-log.md`: the latest block, so the report can say how clean the data is

## Inputs
- `ventures/<slug>/sell/pipeline.csv` (after `crm-hygiene`).
- The previous snapshot `ventures/<slug>/sell/reports/<yyyy-Www>.json`, if any.
- `GH_TOKEN` (`github.token`) to open the report issue.

## Steps
1. Run Mondays at 07:00 UK. GitHub cron is UTC: schedule at 06:00 and 07:00 UTC and let the script exit unless the UK hour is 7.
2. Compute in code, and write to this week's JSON: count and `value_gbp` by stage; new deals this week; deals that moved forward, moved back, were won, were lost (with `lost_reason`); stalled deals (`last_touch` older than 14 days in an active stage); deals with `next_step_date` in the next 14 days; stage-to-stage conversion over the last 90 days; average days in stage.
3. Compare with last week's snapshot by deal id to find what moved. With no snapshot, say "first report".
4. Ask Gemini 2.5 Flash (Groq as fallback) for a six-line summary: what moved, what stalled, what closes next, one risk. Give it only the computed JSON.
5. Check the summary: every number in it must appear in the JSON. Any other figure fails the check and the summary is replaced by a plain bulleted list from the JSON.
6. Add a data quality line from the hygiene log: rows flagged and the top flag.
7. Write `sell/reports/<yyyy-Www>.md` and `.json`.
8. Open a GitHub issue `Pipeline <yyyy-Www>` with the summary and a link to the file.

## Output
- `ventures/<slug>/sell/reports/<yyyy-Www>.md`: summary, stage table, moved, stalled, closing next, data quality.
- `ventures/<slug>/sell/reports/<yyyy-Www>.json`: the computed numbers, used next week and by `forecasting`.
- A GitHub issue so the report reaches Charlie.

## The ladder
- Human-led: Charlie counts deals on a Sunday evening.
- Human-assisted: the job reports, Charlie annotates the stalled deals.
- Fully autonomous: a report lands every Monday morning with no input.

## The human
What stays with Charlie: deciding what to do about stalled deals, and correcting data that the report shows is wrong.

## Tools
plain Python for numbers, Gemini 2.5 Flash then Groq for the summary (as of Oct 2026, check the limit), GitHub Actions weekly, GitHub issues.

## Build notes
- The model never computes; it only phrases numbers the script already produced.
- Fewer than 10 deals: report counts and drop the conversion and average rows rather than show noise.
- On failure add one line under `skipped` in `ventures/<slug>/board.json` with the reason.
