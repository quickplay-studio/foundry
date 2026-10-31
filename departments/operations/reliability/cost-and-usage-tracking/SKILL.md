---
name: cost-and-usage-tracking
title: Cost and Usage Tracking
department: operations
function: reliability
autonomy: solo
stage: run
builds_on: []
breaks_into: [refresh-limits, collect-usage, compare-to-budget, flag-overruns]
replaces: "a finance person reconciling API bills, or a paid cost dashboard"
runs_on: github
status: ready
---

# Cost and Usage Tracking

Token and API spend tracked against budget; no surprise bills.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof

## Inputs
- `ventures/<slug>/budget.json`: `ad_budget`, `spent`, `revenue`, `lines`.
- `ventures/<slug>/usage.jsonl`: one line per model or API call batch: `{"date", "job", "service", "calls", "tokens_in", "tokens_out"}`, appended by each job that calls a service.
- `ventures/<slug>/limits.json`: `[{"service", "unit", "limit", "period", "checked"}]`. Venture repo `docs/integrations/limits.md` is the starting point.
- GitHub Actions run times from the API (`run_started_at` to `updated_at`).

## Steps
1. Refresh `limits.json`: any entry older than 30 days is re-read from the service's own pricing or docs page (Firecrawl scrape, then extract the number). If the number cannot be read, keep the old entry and add a `skipped` line. Never guess a limit. Each value is "as of Oct 2026, check the limit".
2. Seed these services if missing: GitHub Actions (2,000 minutes a month on private repos, free on public), Gemini 2.5 Flash, Groq, Firecrawl, Apify, Supabase, PostHog, Cloudflare Pages or Netlify.
3. Collect usage for the month so far: sum `usage.jsonl` by service; sum Actions minutes across the venture repo and Foundry, rounding each run up to a whole minute. If a job writes no `usage.jsonl` line, record `{"job": "cost-and-usage-tracking", "reason": "no usage log from <job>"}` under `skipped`.
4. For each service compute `used`, percent of limit, and projected month-end (`used` divided by days elapsed, times days in month).
5. Raise entries under `incidents` in `ventures/<slug>/board.json` (shape: `{"id", "date", "severity", "what", "source": "cost", "status": "open"}`):
   - `warn`: used is 80 percent or more of a limit, or the projection passes 100 percent.
   - `high`: a limit is reached; any service shows a non-zero bill or a card on file (free tools only until revenue); `budget.json` `spent` is 80 percent or more of `ad_budget`; or `spent` is over 50 pounds and cost per sign-up is above the figure in the ad brief, which triggers the kill rule.
6. Agents never pause ads or pay anything. The incident text tells Charlie the exact action: "stop the campaign" or "move this job to Groq".
7. Dedupe by `source` and service: update an open incident rather than adding one. Resolve it when used falls under 70 percent.
8. Run weekly on Mondays, and daily in the last 5 days of the month.

## Output
- `ventures/<slug>/usage-summary.json`: `[{"service", "used", "limit", "pct", "projected"}]` with a `generated` date.
- `incidents` and `skipped` lists in `ventures/<slug>/board.json`.
- Updated `limits.json`.

## The ladder
- Human-led: Charlie opens each dashboard and compares.
- Human-assisted: the job reports, Charlie acts.
- Fully autonomous: the job tracks and flags; it still cannot spend or stop spending. This is the default.

## The human
What stays with Charlie: approving every ad budget line, paying platforms himself, stopping a campaign, and deciding whether to leave a free tier.

## Tools
Free first. GitHub REST API, Firecrawl free tier for the limits pages (as of Oct 2026, check the limit), Python stdlib plus `requests`. No model needed; the arithmetic is in code. No Claude.

## Build notes
- Claude usage is budgeted by Charlie and cannot be read here. Record it as `claude_sessions` by hand in `usage.jsonl` if he wants it counted.
- Use pence for money in code, pounds in text.
- Percentages are rounded half up to one decimal place.
- A `high` cost incident is read by `incident-response` and by the weekly Back Office budget line.
