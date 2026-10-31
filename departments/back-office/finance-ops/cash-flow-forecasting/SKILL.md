---
name: cash-flow-forecasting
title: Cash-Flow Forecasting
department: back-office
function: finance-ops
autonomy: assisted
stage: run
builds_on: [revenue-reporting, budget-tracking]
breaks_into: [load-baseline, project-13-weeks, run-scenarios, open-pull-request]
replaces: "an accountant's forecasting add-on, roughly 50 to 150 pounds a month"
runs_on: github
status: ready
---

# Cash-Flow Forecasting

Project cash in and out; know the runway before it is an emergency. Thirteen weeks, three scenarios, one pull request for Charlie to read.

## Reads from the brain
- `brain/company.md`: constraints (ventures must pay for themselves; ad spend is the one exception, and Charlie approves each budget line)
- `ventures/<slug>/brain.md`: money, for the expected billing pattern and payment delay

## Inputs
- `office/finance/cash.json`: `{"as_of", "currency", "cash"}`. One balance figure Charlie types in. Never an account number.
- `office/finance/commitments.json`: `[{"name", "amount", "currency", "every": "week|month|year|once", "first", "venture", "kind"}]` for known costs such as domains or tools that have a price.
- `office/finance/assumptions.json`: `{"low_factor": 0.5, "high_factor": 1.25, "buffer": 0, "tax_set_aside_rate": 0}`. The values shown are defaults; Charlie edits them.
- `office/finance/revenue/YYYY-MM.json`: recent monthly revenue.
- `ventures/*/budget.json`: remaining `ad_budget` (approved minus spent) and recent weekly spend.
- `ventures/*/finance/payments.json`: invoices that are due, with days late history.

## Steps
1. If `cash.json` is missing or `as_of` is more than 14 days old, write the forecast as `unanchored`, say so in the first line, and ask Charlie for a new balance in the pull request body. Do not guess a balance.
2. Build 13 weekly buckets from the Monday after `as_of`.
3. Cash out: every commitment on its dates; remaining approved ad budget spread over the weeks at the last four weeks' average spend, ending when it runs out. No unapproved spend is ever forecast.
4. Cash in, base case: per venture, the trailing three-month average of revenue spread evenly across weeks, plus each due invoice on its due date plus that venture's average days late (0 with no history). A venture with `verdict: park` brings in nothing new.
5. Scenarios: `low` multiplies projected revenue by `low_factor`, `high` by `high_factor`, `base` by 1. Costs are identical in all three.
6. If `tax_set_aside_rate` is above 0, hold that share of positive revenue as a separate line. The job never works out a tax liability.
7. Per scenario report: closing cash by week, the first week cash falls below `buffer` (or `none in 13 weeks`), runway in weeks, and the three largest outflows.
8. Write a short commentary of at most five sentences, facts only. Gemini 2.5 Flash or Groq may phrase it; a fixed template is the fallback.
9. Open a pull request with the files and the changed assumptions, if any.

## Output
- `office/finance/forecast.json`: `{"as_of", "anchored", "weeks": [{"start", "in", "out", "close_base", "close_low", "close_high"}], "runway_weeks": {"base", "low", "high"}, "first_below_buffer": {...}}`
- `office/finance/forecast.md`: first line states the base-case runway; then the table and commentary.
- The pull request is the hand-off. Merge means Charlie has read it.

## The ladder
- Human-led: Charlie builds a spreadsheet forecast by hand each month.
- Human-assisted (the setting here): the job builds the forecast from the files, Charlie owns the assumptions and merges.
- Fully autonomous: not offered. A forecast rests on assumptions about customers and money that are Charlie's to hold.

## The human
What stays with Charlie: typing the current balance, listing commitments, setting the factors and buffer, deciding when to spend ahead of revenue, and talking to an accountant when an entity exists.

## Tools
Python stdlib. Gemini 2.5 Flash then Groq free tier for the commentary; as of Oct 2026, check the limits. GitHub Actions weekly schedule, last in the Run order.

## Build notes
- One module, `foundry/cashflow.py`. Integer minor units; currencies other than GBP converted with `office/finance/rates.json` and flagged when no rate exists.
- Tests offline: unanchored forecast, zero revenue, park venture, buffer breach in week 9, ad budget exhausting mid-horizon.
- Do not compute VAT, corporation tax or income tax here; those belong to the accountant and to `entity-compliance`.
