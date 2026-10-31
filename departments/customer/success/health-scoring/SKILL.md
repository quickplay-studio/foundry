---
name: health-scoring
title: Health Scoring
department: customer
function: success
autonomy: solo
stage: support
builds_on: []
breaks_into: [pull-events, compute-signals, score-and-band, write-and-snapshot]
replaces: "the health module of a customer-success platform"
runs_on: github
status: ready
---

# Health Scoring

Score every account on usage, sentiment and engagement.

## Reads from the brain
- `brain/company.md`: constraints (free tools only, nothing regulated without a human)
- `ventures/<slug>/brain.md`: the venture's problem, who, mvp, money (plans, prices, billing interval). For a consumer or prosumer app an account is one user.

## Inputs
- `ventures/<slug>/support/events.json`: `{"activation", "core", "paid", "cancel", "expected_active_days_per_14", "weights": {"usage": 50, "engagement": 30, "sentiment": 20}, "payments", "proposed"}`. If missing, create it from the mvp line with `proposed: true` and default weights, and note it for Charlie.
- PostHog events per user, last 28 days (secrets `POSTHOG_API_KEY`, `POSTHOG_PROJECT_ID`, read only, HogQL query endpoint). Use only the distinct id; no emails.
- Payment events from the venture's provider: plan, status, start date, failed payments, cancel-at-period-end. Source: read-only key `PAYMENTS_READ_KEY`, or an export in `support/data/payments.csv` with name, email and card details removed.
- `support/tickets.json`: sentiment and count per `user_id`, last 60 days.

## Steps
1. Pull events and payments. Join on `user_id`. Drop accounts with no events and no payment in 90 days (record as `dormant`, count only).
2. Usage score (0 to 100): active days in the last 14 divided by `expected_active_days_per_14`, capped at 100, then adjusted by the trend of `core` events against the previous 14 days (plus or minus 10).
3. Engagement score (0 to 100): 40 if `activation` has fired, plus 30 if the user was active in each of the last two weeks, plus 30 for using two or more distinct features in 14 days.
4. Sentiment score (0 to 100): 70 with no tickets; minus 15 for each ticket with sentiment of -1 or lower, minus 25 for each escalated ticket, plus 10 for each praise ticket, within 60 days.
5. Combine with the weights. Caps: a failed payment in the last 30 days caps the score at 60; cancel-at-period-end caps it at 40.
6. Band: green 70 or more, amber 40 to 69, red under 40. Accounts under 14 days old are `new` and unbanded unless activated. Record `trend` as the change since the last snapshot.
7. Write `health.json` and `health.md`, and copy `health.json` to `support/health-history/<date>.json` for `churn-prediction` and `qbr-prep`.

## Output
- `ventures/<slug>/support/health.json`: `{"updated": "...", "weights": {}, "summary": {"green": 0, "amber": 0, "red": 0, "new": 0, "dormant": 0}, "accounts": [{"user_id", "plan", "tenure_days", "score", "band", "trend", "usage", "engagement", "sentiment", "flags": []}]}`
- `support/health.md`: counts, the 20 lowest scores with their flags, and a "low data" note if there are under 30 accounts.
- `ventures/<slug>/support/health-history/<date>.json`: weekly snapshot, read by `churn-prediction` and `qbr-prep`.

## The ladder
- Human-led: Charlie looks at PostHog himself; the job only writes the scoring definition into `events.json`.
- Human-assisted: the job scores and proposes weight changes in a pull request; Charlie merges.
- Fully autonomous: the job recomputes weekly with the weights in `events.json`. It never changes weights by itself.

## The human
What stays with Charlie: naming the activation and core events, approving any change to weights, and deciding what to do about red accounts.

## Tools
PostHog free tier and the payment provider's read access (as of Oct 2026, check the limit and the API rate on each). Python stdlib plus `requests`. No model is needed to score; Gemini 2.5 Flash or Groq may summarise flags in `health.md`. GitHub Actions weekly cron (as of Oct 2026, check Actions minutes for a private repo).

## Build notes
- Scores are arithmetic, in code, so they are reproducible. A model never sets a number.
- Under 30 accounts the bands are rough; say so in `health.md` rather than hiding it.
- If PostHog or the payment source fails, score what is available, mark `partial: true`, and log the reason under `skipped` in `ventures/<slug>/board.json`.
- Do not commit emails or names. `user_id` only.
- Tests: fixture events and payments with one account per band, one failed payment cap, one cancel cap.
