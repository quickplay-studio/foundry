---
name: budget-tracking
title: Budget Tracking
department: back-office
function: finance-ops
autonomy: solo
stage: run
builds_on: []
breaks_into: [collect-spend, compare-to-budget, apply-kill-rule, write-weekly-line]
replaces: "a paid budgeting app or a bookkeeper's monthly spend review, roughly 10 to 50 pounds a month"
runs_on: github
status: ready
---

# Budget Tracking

Spend versus budget by category, ad spend first, overruns flagged early. This is the weekly heartbeat of every venture and the one place the kill rule is applied.

## Reads from the brain
- `brain/company.md`: voice and constraints (free tools only; ad spend is the one exception and Charlie approves every budget line)
- `ventures/<slug>/brain.md`: money and proof, for what the venture charges and what counts as a sign-up
- `ventures/<slug>/board.json`: `gates`, earlier `weekly` lines, top-level `verdict`

## Inputs
- `ventures/<slug>/budget.json`: `currency`, `ad_budget` (what Charlie approved), `spent`, `revenue`, `lines[]` each `{date, kind, amount, note}`. Lines are spend only; `kind` is `ad`, `tool`, `domain`, `fee` or `other`.
- `ventures/<slug>/finance/ads-*.csv`: ad platform spend exports Charlie downloads. Columns are mapped by header name (date, spend). A missing header means skip the file and say why.
- `ventures/<slug>/finance/expenses.json`: categorised non-ad spend from `expense-categorisation`, if present.
- `ventures/<slug>/finance/payments.json`: paid and refunded rows from `payment-tracking`; the only revenue source.
- `ventures/<slug>/finance/signups.csv`: `date,count`, from the product's own sign-up count. Absent means sign-ups are unknown.
- The ad brief Marketing wrote under `ventures/<slug>/launch/`: the cost per sign-up ceiling.

## Steps
1. Visit every `ventures/*/board.json`. Skip a venture whose top-level `verdict` is `park` (the agents have stopped) or whose `gates.launch` is still `open` (nothing has launched).
2. Build spend lines. Ad lines are one per platform per day with note `ads:<platform>:<date>`; a re-export replaces that line, never doubles it. Other lines are added only if the key `date|kind|amount|note` is new.
3. Recompute `spent` as the sum of all lines. Set `revenue` to paid minus refunded in `payments.json`, in the budget currency. A different currency with no rate in `office/finance/rates.json` is left out and noted.
4. Compare ad spend with `ad_budget`. Flag `amber` at 80 percent used or when the last two weeks' average would exhaust it within two weeks; flag `red` at 100 percent (Charlie pauses ads himself and decides on more). If `ad_budget` is 0 say `no approved budget` and never park.
5. Work out this week's numbers (ISO week, Monday to Sunday): `spent` all kinds, `revenue` net paid dated in the week, `sign_ups` summed from `signups.csv`. `cost_per_sign_up` is cumulative ad spend divided by cumulative sign-ups, null while sign-ups are zero.
6. Ad rule: once ad spend passes £50 and `cost_per_sign_up` is above the ceiling in the ad brief, set `ads_stop` in the note. If the ceiling cannot be found, say so and skip this check.
7. Verdict, in this order:
   - `park` when all hold: `ad_budget` > 0 and ad spend has reached it; total revenue is 0; there is no sign-up trend (the last four weeks total zero, or the last two weeks do not beat the two before); at least four weekly lines exist including this one.
   - `scale` when revenue to date covers total spend, spend is above 0 and sign-ups are rising.
   - `continue` otherwise.
8. Never park on stale or missing data. The park test needs `payments.json` updated this week, or no `stripe-*.csv` ever dropped (which means no revenue). If sign-up data is missing the verdict stays `continue` with the note `sign-up data missing`.
9. Write `budget.json`, then replace or append the `weekly` line in `board.json` and set top-level `verdict` (the daily Lodestone sync reads it). On `park` also set `gates.run` to `parked`; the idea returns to Lodestone as `watching`.

## Output
- `ventures/<slug>/budget.json`, updated in place with refreshed `updated`.
- `ventures/<slug>/board.json`: `weekly` gains one line, keyed by `week` so a re-run replaces it.
  `{"week": "2026-W44", "spent": 42.5, "revenue": 0, "sign_ups": 31, "cost_per_sign_up": 1.37, "verdict": "continue", "note": "amber: 80% of ad budget used"}`
- Money is pounds to two decimals, rounded half up. Dashboards and Charlie read these files; no email is sent.

## The ladder
- Human-led: Charlie reads each ad dashboard and a spreadsheet weekly and decides alone.
- Human-assisted: the job totals and flags, Charlie sets the verdict.
- Fully autonomous (the setting here): the job writes numbers and verdict every week; Charlie acts only on amber, red, `scale` and `park`. It never moves money or touches an ad account.

## The human
What stays with Charlie: approving and raising `ad_budget`, paying the platforms, dropping the CSV exports, pausing campaigns, and overriding a `park` by setting `verdict` back to `continue` with a reason in the venture brain.

## Tools
No model needed. Python stdlib in a GitHub Actions weekly schedule (Mondays, early UTC). Nothing paid; ad platforms' own CSV exports are the data source.

## Build notes
- One short module, `foundry/budget.py`; tests offline with fixture CSVs: park, not-park (revenue present, trend present, budget unused, data stale), and a double run that changes nothing.
- Weekly run order: `expense-categorisation`, `payment-tracking`, `budget-tracking`, `revenue-reporting`, `goal-pacing`, `cash-flow-forecasting`. Commit as `Foundry Bot`, message `run: <date>`.
- A job that cannot run writes a line under `skipped` in `board.json` and does not block the others.
- Open point: the exact path of the ad brief is Marketing's choice; check it when `ad-creative` is filled.
- GitHub implementation: `run.py` beside this file (jobkit).
