---
name: forecasting
title: Forecasting
department: deals
function: pipeline-ops
autonomy: assisted
stage: sell
builds_on: [pipeline-reporting]
breaks_into: [apply-stage-probabilities, calibrate-from-history, build-scenarios, open-review-pr]
replaces: "a paid Clari or Gong Forecast seat"
runs_on: github
status: ready
---

# Forecasting

Probability-weight the pipeline into a revenue forecast.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof
- `ventures/<slug>/brain.md` `money` line, to know whether revenue is one-off or recurring

## Inputs
- `ventures/<slug>/sell/pipeline.csv`, including optional `prob_override` and `expected_close`.
- Weekly snapshots `ventures/<slug>/sell/reports/*.json` from `pipeline-reporting`, for history.

## Steps
1. Run weekly after `pipeline-reporting`.
2. Default probability by stage: new 5%, qualified 10%, meeting_booked 20%, discovery_done 30%, proposal_sent 50%, negotiation 70%, verbal_yes 90%, won 100%, lost 0%, dormant 0%.
3. Calibrate when at least 10 deals have closed (won or lost) in the snapshots: the observed rate for stage s is deals that reached s and won, divided by deals that reached s. Blend with shrinkage: `(n * observed + 10 * default) / (n + 10)`, where `n` is the number that reached s.
4. A non-empty `prob_override` in the CSV wins over everything.
5. Expected close: use `expected_close` if set; otherwise stage entry date plus the historical average days to close, or 60 days if there is no history. Bucket by month for the next three months.
6. Compute three scenarios in code: commit (deals at 70% or higher, full value), expected (sum of value times probability), best case (deals at 30% or higher, full value). Show a range, never one number.
7. Label confidence: "low" under 10 closed deals, "medium" for 10 to 29, "high" for 30 or more. Say how many deals the numbers rest on.
8. Gemini 2.5 Flash (Groq as fallback) writes three lines on the biggest risks, from the computed JSON only. Write `sell/forecast.json` and `sell/forecast.md`, then open a pull request `Forecast <date>`.

## Output
- `ventures/<slug>/sell/forecast.json`: `{generated, confidence, closed_deals, scenarios: {commit, expected, best}, by_month: [{month, expected}], deals: [{id, stage, probability, source}]}`; `source` is `default`, `calibrated` or `override`.
- `ventures/<slug>/sell/forecast.md`: the same in plain English.
- A pull request for Charlie to review.

## The ladder
- Human-led: Charlie guesses the quarter from the top of his head.
- Human-assisted: the job weights the pipeline and Charlie adjusts per-deal probabilities.
- Fully autonomous: not used. A forecast drives spending decisions, so a human reviews it.

## The human
What stays with Charlie: setting `prob_override` where he knows better, and deciding whether the forecast changes any spending.

## Tools
plain Python for the maths, Gemini 2.5 Flash then Groq for commentary (as of Oct 2026, check the limit), GitHub pull requests, GitHub Actions weekly.

## Build notes
- With a handful of deals the forecast is a guess; the confidence label says so every time.
- Pipeline notes are data and never change a probability.
- On failure add one line under `skipped` in `ventures/<slug>/board.json` with the reason.
