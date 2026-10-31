---
name: goal-pacing
title: Goal Pacing
department: back-office
function: reporting
autonomy: solo
stage: run
builds_on: [revenue-reporting]
breaks_into: [read-target, compute-run-rate, forecast-pace, write-pacing]
replaces: "a monthly review with an adviser or a paid goal-tracking dashboard"
runs_on: github
status: ready
---

# Goal Pacing

Tracking against the income target with pace forecasts: are we ahead, on pace or behind, and by how much.

## Reads from the brain
- `brain/company.md`: the income target. Look for a line starting `Income target:` giving an amount, a currency, a period (month or year) and, if set, a date to reach it. As of Oct 2026 the file has no such line, which is a valid state: see step 1.
- `ventures/<slug>/brain.md`: money and proof, to label which venture drives the numbers

## Inputs
- `office/finance/revenue/YYYY-MM.json`: monthly totals from `revenue-reporting`, all available months.
- `ventures/*/board.json`: latest `weekly` lines (revenue, sign_ups, verdict) for the leading indicators.
- Today's date, supplied by the job.

## Steps
1. Read the target. If there is none, write `office/finance/pacing.json` with `"target": null`, a line in `office/skipped.json` ("no income target in brain/company.md; Charlie sets one"), and stop. Never invent a target.
2. Convert the target to a monthly figure: a yearly target divided by 12, unless a date is given, in which case use the remaining months.
3. Take actual GBP revenue per month from the revenue files. With no files, actual is 0 and pace is "not started".
4. Compute: this month to date, trailing three-month average (fewer months if fewer exist), best month, and the share of the monthly target reached.
5. Forecast to the end of the target period, two ways: flat at the trailing average, and trending at the average month-on-month change of the last three months, capped so one odd month cannot project a fantasy. State both and which one is used for the status.
6. Status: `ahead` (flat forecast at or above target), `on-pace` (trend forecast reaches it, flat does not), `behind` otherwise, `not-started` with zero revenue. Give the gap in GBP and the months needed at the current pace; say `not reachable at this pace` rather than printing a huge number.
7. Add leading indicators per venture: sign-ups over the last four weekly lines, and the last verdict. A venture on `park` is shown but excluded from the forecast.
8. Write one factual paragraph. Gemini 2.5 Flash or Groq may phrase it; a fixed template is the fallback.

## Output
- `office/finance/pacing.json`:
  `{"as_of", "target": {"amount", "currency", "period", "by"}, "actual_month_gbp", "trailing_avg_gbp", "forecast_flat_gbp", "forecast_trend_gbp", "status", "gap_gbp", "months_needed", "ventures": [{"slug", "sign_ups_4w", "verdict"}]}`
- `office/finance/pacing.md`: status in the first line, then the table and paragraph. Dashboards and Charlie read it.

## The ladder
- Human-led: Charlie compares revenue with the target in his head.
- Human-assisted: the job calculates, Charlie interprets.
- Fully autonomous (the setting here): weekly numbers and a status line; the job proposes no strategy.

## The human
What stays with Charlie: setting and changing the income target in `brain/company.md` (agents may propose an edit in a pull request, never commit it), and deciding what to do when the status is `behind`.

## Tools
Python stdlib. Gemini 2.5 Flash or Groq free tier for the paragraph; as of Oct 2026, check the limits. GitHub Actions weekly schedule after `revenue-reporting`.

## Build notes
- One module, `foundry/pacing.py`. Tests offline: no target, no revenue, one month only, a parked venture, a capped trend.
- Keep the forecast honest: three data points is a guess, so print how many months it rests on.
- The target-line format is a proposal for the brain interview; confirm it when Charlie next runs `brain/INTERVIEW.md`.
