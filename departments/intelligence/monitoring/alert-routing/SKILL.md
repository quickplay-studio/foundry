---
name: alert-routing
title: Alert Routing
department: intelligence
function: monitoring
autonomy: assisted
stage: run
builds_on: [news-and-mention-tracking, account-monitoring]
breaks_into: [score-and-dedupe, route-to-channel, learn-from-labels]
replaces: "a person triaging a monitoring inbox"
runs_on: github
status: ready
---

# Alert Routing

Signals that matter reach the right place; noise is filtered.

## Reads from the brain
- `brain/company.md`: working hours (evenings and weekends UK time), voice, constraints
- `ventures/<slug>/brain.md`: problem and who, so relevance matches the venture

## Inputs
- `ventures/<slug>/run/mentions/mentions.jsonl` from `news-and-mention-tracking` and, for B2B ventures, `ventures/<slug>/sell/signals/signals.jsonl` from `account-monitoring`.
- Rules in `ventures/<slug>/run/alerts/rules.json`: `min_score` (start at 2), `max_alerts_per_day` (start at 3), `routes` by type, `dedupe_hours` (start at 48), `quiet_hours` (start at 22:00 to 07:00 UK, except legal or regulatory items).
- Env: `GH_TOKEN` (`github.token` with `issues: write`), `GEMINI_API_KEY`, `GROQ_API_KEY`.

## Steps
1. Trigger: after each collection run, through a workflow chained to the monitoring jobs, or hourly by cron. Read only items newer than the last run (`ventures/<slug>/run/alerts/cursor.json`).
2. Score in code: `relevance` (already 0 to 3) plus urgency: +1 for regulatory, a negative review of the brand, a competitor price cut, a funding round or new head of function at a target account; +1 if the item names the brand directly. Drop anything below `min_score`.
3. Dedupe: group by fingerprint and by near-identical titles within `dedupe_hours`; keep one item and note the count. Gemini 2.5 Flash (free tier, about 10 requests a minute and 250 a day as of Oct 2026, check; Groq as fallback) is used only to merge near-duplicates and write a one-line "why this matters", 20 items per call.
4. Route in code from `routes`. Alert: open a GitHub issue labelled `alert` and the type (the GitHub app and email notifications are the free channel), at most `max_alerts_per_day`. Digest: everything else goes to the weekly digest and the single weekly line in `board.json`. Items in quiet hours wait until morning.
5. Issue body: the why-line, the item link, the score breakdown, and the line "Label `useful` or `noise`". Add the label `review` to every alert for the first 14 days.
6. Learn weekly, assisted. Read issues closed with `useful` or `noise`. If more than 60 percent of one type were `noise`, propose raising `min_score` for it; if a type was `useful` but was filtered out in the digest, propose lowering it. Open a pull request editing `rules.json`; never merge it.
7. A failed model call does not stop routing: send the item with its stored summary.

## Output
- GitHub issues labelled `alert`, one per routed item.
- `ventures/<slug>/run/alerts/log.jsonl`: every decision (`fingerprint`, `score`, `route`, `reason`), append only.
- `ventures/<slug>/run/alerts/cursor.json` and, weekly, a pull request that proposes rule changes.
- One weekly line in `ventures/<slug>/board.json`: alerts sent, filtered, share marked `useful`.

## The ladder
- Human-led: Charlie scans the digests and decides what matters.
- Human-assisted: the job scores, filters and routes; Charlie labels and approves rule changes. This is the default.
- Fully autonomous: rules update themselves from labels; only after 8 weeks of at least 80 percent `useful` labels.

## The human
What stays with Charlie: labelling alerts, merging rule changes, and acting on an alert.

## Tools
GitHub Issues and pull requests through `GH_TOKEN`, Gemini 2.5 Flash, Groq, GitHub Actions. No paid pager, chat or SMS service, no accounts to create, no Claude.

## Build notes
- Routing and scoring are plain Python, so tests are cheap: a noisy fixture of 100 items must yield at most `max_alerts_per_day` issues.
- Never route personal data from `person-research` sheets into an issue.
- Tests offline with a stubbed GitHub client.
- GitHub implementation: `run.py` beside this file (jobkit).
