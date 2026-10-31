---
name: monitoring-and-alerting
title: Monitoring and Alerting
department: operations
function: reliability
autonomy: solo
stage: run
builds_on: [project-scaffolding]
breaks_into: [list-monitors, check-workflow-runs, check-endpoints, write-incident-or-skip]
replaces: "a paid uptime and cron monitoring service"
runs_on: github
status: ready
---

# Monitoring and Alerting

Watch every automation for failures and silent stalls.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof

## Inputs
- `ventures/<slug>/monitors.json`: `[{"id", "type": "workflow|url|file", "repo", "workflow", "url", "expect_text", "path", "max_age_hours"}]`. If absent, build it (step 1).
- `GH_TOKEN` (`github.token`) to read workflow runs. Nothing else is needed.
- `ventures/<slug>/monitor-state.json`: consecutive failure counts per monitor, written by this job.

## Steps
1. If `monitors.json` is missing, create it: every workflow with a `schedule` in `.github/workflows/` of Foundry and of `quickplay-studio/<slug>`, plus the live URL once `board.json` records one. Default `max_age_hours` is 26 for a daily schedule and twice the interval for anything more frequent.
2. Workflows: `GET /repos/{repo}/actions/workflows/{file}/runs?per_page=5`. A failure is a last conclusion of `failure`. A silent stall is no successful run inside `max_age_hours`, which GitHub does not report as an error.
3. Files: a job can succeed and write nothing. For each `file` monitor, check the last commit time of the path against `max_age_hours`.
4. URLs: GET with a 15 second timeout. Fail on a non-200 status, a missing `expect_text`, or a timeout. Raise only after 2 consecutive fails, to avoid flapping.
5. For each failure write an entry under `incidents` in `ventures/<slug>/board.json`: `{"id": "inc-YYYYMMDD-n", "date", "severity": "warn|high", "what", "source": "<monitor id>", "status": "open", "last_seen"}`. One open incident per source: update `last_seen` instead of adding another. High means users, money or data are affected; everything else is warn.
6. A monitor that passes twice in a row closes its incident: `status: resolved`.
7. If a check cannot run (no token, API error, rate limit), add `{"job": "monitoring-and-alerting", "reason": "<short>", "date": "<ISO>"}` under `skipped`. A check that could not run is never reported as passing.
8. Alert: open or update a GitHub issue `incident: <slug> <monitor id>` in Foundry. GitHub emails Charlie through his notification settings. At most one alert per incident per 24 hours.
9. Commit `board.json` and `monitor-state.json` only when an incident changes, plus one heartbeat commit a day.

## Output
- `ventures/<slug>/board.json`: `incidents` and `skipped` lists as above, the only place the dashboards read.
- `ventures/<slug>/monitors.json` and `monitor-state.json`.
- A GitHub issue per open incident.

## The ladder
- Human-led: Charlie checks each automation by hand.
- Human-assisted: the job reports, Charlie triggers a re-run.
- Fully autonomous: the job detects, records and alerts; `incident-response` takes over. This is the default.

## The human
What stays with Charlie: reading high incidents, creating the UptimeRobot monitor for the live URL (an account step), and deciding whether an incident is worth a fix.

## Tools
Free first. GitHub Actions on a 6-hourly schedule (about 4 short runs a day, well inside 2,000 private-repo minutes a month, as of Oct 2026, check the limit), the GitHub REST API. UptimeRobot free tier as an independent check on the live URL (as of Oct 2026, check the limit). Python stdlib plus `requests`. No model, no Claude.

## Build notes
- GitHub disables scheduled workflows in a repo with no activity for 60 days; the daily heartbeat commit prevents that.
- Scheduled runs can start late. Allow for it in `max_age_hours`.
- Never put a webhook URL or token in `monitors.json`.
- This job cannot watch itself. The UptimeRobot check on the live URL and the daily heartbeat commit are the outside checks.
