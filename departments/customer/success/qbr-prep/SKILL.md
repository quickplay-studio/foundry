---
name: qbr-prep
title: QBR Prep
department: customer
function: success
autonomy: assisted
stage: none
builds_on: [health-scoring]
breaks_into: [pull-quarter-data, compare-with-last-quarter, draft-review, list-actions]
replaces: "a customer-success manager's quarterly review prep, or an analyst's reporting time"
runs_on: github
status: ready
---

# QBR Prep

Build the quarterly review from real account data.

## Reads from the brain
- `brain/company.md`: voice (plain, direct, UK English, no hype), constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof, and any stated goals for the quarter

## Inputs
- `ventures/<slug>/support/health-history/*.json` and `support/health.json`: scores and bands over the quarter.
- `support/churn.json`, `support/tickets.json`, `support/faq.json`, `support/macros.json`, `support/advocacy.json` where they exist.
- PostHog events for the quarter (secrets `POSTHOG_API_KEY`, `POSTHOG_PROJECT_ID`) and payment events (`PAYMENTS_READ_KEY` or `support/data/payments.csv`).
- `ventures/<slug>/board.json`: the weekly lines (spent, revenue, sign-ups, cost per sign-up, verdict).
- The previous review in `support/qbr/`, if any.
- Mode. `venture` is the default: the review of the whole customer base, for Charlie. `account` applies only when the audit says the idea has a business buyer: one page per named account.

## Steps
1. Fix the quarter (calendar quarters, UK dates) and pull the data. Compute every number in code: sign-ups, activation rate, 28-day active users, paying users, revenue, cancellations, refunds, tickets by category, median first response, share of tickets answered by macro, health band movement.
2. Compare with the previous quarter and with any goal in the brain. If there is no goal, leave the column empty; do not invent one.
3. Ask the model (Gemini 2.5 Flash, then Groq) for the narrative from the numbers only: what changed, up to three causes that the data supports, the five most asked-for features with counts, and the main risks. Every sentence must trace to a number in the table.
4. List up to five actions, each with an owner (Charlie or a named job) and a date inside the next quarter.
5. In `account` mode, add one page per account: usage against plan, value delivered, open issues, renewal date, proposed next steps. Use `user_id`, never a name or email.
6. Open a pull request with the review. Charlie edits the narrative and merges.

## Output
- `ventures/<slug>/support/qbr/<yyyy>-q<n>.md`: sections Numbers (table with last quarter and change), What happened, What customers asked for, Risks, Actions. Two pages at most.
- `support/qbr/<yyyy>-q<n>-<user_id>.md`: one per account in `account` mode.
- `support/qbr/<yyyy>-q<n>.json`: the numbers, so the next review can compare without re-reading.

## The ladder
- Human-led: Charlie writes the review; the job supplies the numbers table.
- Human-assisted: the job writes the numbers, the draft narrative and the action list; Charlie edits and merges.
- Fully autonomous: the numbers table and JSON are written and committed on the quarter's first Monday. The narrative still waits for Charlie.

## The human
What stays with Charlie: the story told about the quarter, the choice of actions, any decision to change price, scope or channel, and anything that goes to a customer in `account` mode.

## Tools
Python stdlib plus `requests` for all arithmetic. Gemini 2.5 Flash and Groq free tiers for the narrative. PostHog free tier and the payment provider's read access (as of Oct 2026, check the limit). GitHub Actions cron on the first Monday after each quarter ends.

## Build notes
- Numbers come from code. The model never calculates and never rounds.
- A first quarter has no comparison; say so once and skip the change column.
- Missing source: leave its rows blank, note it at the top, and log it under `skipped` in `ventures/<slug>/board.json`.
- Under 30 paying users, add one line saying the percentages move a lot on small counts.
- Tests: a fixture quarter with known counts must reproduce every number in the table.
- GitHub implementation: `run.py` beside this file (jobkit).
