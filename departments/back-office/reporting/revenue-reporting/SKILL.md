---
name: revenue-reporting
title: Revenue Reporting
department: back-office
function: reporting
autonomy: solo
stage: run
builds_on: [payment-tracking]
breaks_into: [load-paid-rows, convert-currencies, sum-by-venture, write-report]
replaces: "a bookkeeper's monthly management report, roughly 50 to 150 pounds a month"
runs_on: github
status: ready
---

# Revenue Reporting

Monthly revenue truth across ventures and currencies. Before any venture takes money, the honest report is a zero.

## Reads from the brain
- `brain/company.md`: voice and constraints (ventures run as personal projects until the first one makes money; no entity yet)
- `ventures/<slug>/brain.md`: money, for the pricing model, so one-off and recurring sales are labelled correctly

## Inputs
- `ventures/*/finance/payments.json`: rows with status `paid` or `refunded`, from `payment-tracking`. This is the only revenue source.
- `ventures/*/budget.json`: `currency` and `spent`, for a gross margin line.
- `office/finance/rates.json`: `{"date", "source", "rates": {"EUR": 0.85, ...}}`, units of GBP per unit of currency.
- `office/finance/revenue/`: earlier month files, for the month-on-month change.

## Steps
1. Choose the month: the last complete calendar month, or the month in the `--month YYYY-MM` argument. Re-running a month overwrites its file.
2. For every venture, sum paid rows dated in the month and subtract refunds dated in the month. Keep the native currency totals.
3. Refresh `rates.json` if older than 7 days from the European Central Bank daily reference rates (free, published each working day; the Frankfurter API mirrors them, check it is still available). Use the rate for the last working day of the month. If a rate cannot be fetched, keep the currency in its own column, mark `gbp: null`, and never guess.
4. Convert to GBP, rounded half up, and total across ventures. Report native and GBP side by side.
5. Split each venture into new sales, recurring, and refunds when the payment descriptions allow it; otherwise report one line.
6. Add: month-on-month change in GBP, number of paying customers if the rows carry distinct ids, spend from `budget.json`, revenue minus spend.
7. Write one plain paragraph on what changed, factual only. Gemini 2.5 Flash or Groq may phrase it; a fixed template is the fallback.
8. If a venture has no `payments.json`, list it as `no data` rather than zero.

## Output
- `office/finance/revenue/2026-10.json`:
  `{"month", "rates_date", "total_gbp", "ventures": [{"slug", "native": {"GBP": 0}, "gbp", "refunds_gbp", "spend_gbp", "customers"}], "notes": []}`
- `office/finance/revenue/2026-10.md`: the same as a short table plus the paragraph. `goal-pacing`, `cash-flow-forecasting` and the dashboards read it.
- Skips and missing rates go to `office/skipped.json` as `{date, job, reason}`.

## The ladder
- Human-led: Charlie totals Stripe exports in a spreadsheet each month.
- Human-assisted: the job produces the table, Charlie checks it against Stripe.
- Fully autonomous (the setting here): runs weekly, finalises on the first run of a new month.

## The human
What stays with Charlie: reading the report, spotting a number that looks wrong against Stripe, and handing the figures to an accountant when an entity exists. The job does not file or advise on tax.

## Tools
Python stdlib. ECB reference rates over plain HTTP. Gemini 2.5 Flash then Groq for the one paragraph only; as of Oct 2026, check the limits. GitHub Actions weekly schedule.

## Build notes
- One module, `foundry/revenue.py`. Amounts in minor units, converted once, half-up rounding.
- Tests offline: refund in a later month, a second currency with and without a rate, an empty portfolio, a re-run of the same month.
- `office/` is a new root folder for all portfolio-level back-office data; the dashboards session should read `office/finance/` as well as `ventures/*/`.
