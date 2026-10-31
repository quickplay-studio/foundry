---
name: churn-prediction
title: Churn Prediction
department: customer
function: success
autonomy: solo
stage: support
builds_on: [health-scoring]
breaks_into: [build-history, score-risk-rules, back-test, rank-and-draft]
replaces: "a churn analytics add-on or a part-time data analyst"
runs_on: github
status: ready
---

# Churn Prediction

Predict which accounts are about to slip before usage dips.

## Reads from the brain
- `brain/company.md`: voice, constraints (free tools only, no unsolicited email outside the law)
- `ventures/<slug>/brain.md`: the venture's problem, who, money (plans, billing interval, trial length), proof

## Inputs
- `ventures/<slug>/support/health.json` and `support/health-history/*.json`: current and past weekly scores per `user_id`.
- `support/events.json`: names of the `core`, `paid` and `cancel` events and `expected_active_days_per_14`.
- PostHog events (secrets `POSTHOG_API_KEY`, `POSTHOG_PROJECT_ID`) and payment events (`PAYMENTS_READ_KEY` or `support/data/payments.csv`): failed payments, cancel-at-period-end, downgrades, trial end dates.
- `support/tickets.json`: negative tickets and unanswered tickets per `user_id`.

## Steps
1. Build each paying or trialling account's last 8 weeks from the health history. Mark accounts that cancelled in the last 90 days as `churned` with the cancel date.
2. Score risk with rules. Risk points, summed and capped at 100:
   - no `core` event for 7 days after a 14-day run of 3 or more active days: 30
   - health score down 20 or more in two snapshots: 25
   - failed payment not recovered: 30
   - cancel-at-period-end set: 40
   - trial ends within 3 days and not activated: 30
   - two negative tickets in 30 days: 15
   - a ticket unanswered for over 72 hours: 15
3. Back-test: for each churned account, compute the risk it would have had 14 days before cancelling. Report churned, caught (risk 50 or more), and false alarms (risk 50 or more and still active after 30 days). With fewer than 30 churned accounts write "too few to tune" and keep the default points. With 30 or more, propose point changes of one step per week at most, logged in `rules_version`.
4. Rank active accounts by risk. Give each at-risk account (risk 50 or more) its reasons in plain words and one suggested action: `ask-why`, `help-email`, `win-back` or `none`.
5. For the 5 highest, draft a short note in the house voice to `support/outbox/winback-<user_id>.md` with `send: hold`. A note asks one question or offers help. It never offers a discount.
6. Write `churn.json` and `churn.md`. Set `escalate: true` on any at-risk account that also has an open P1 or P2 ticket; `escalations` reads that flag.

## Output
- `ventures/<slug>/support/churn.json`: `{"updated": "...", "horizon_days": 30, "rules_version": 1, "backtest": {"churned": 0, "caught": 0, "false_alarms": 0, "note": ""}, "at_risk": [{"user_id", "risk", "reasons": [], "plan", "next_bill", "suggested_action", "escalate"}]}`
- `support/churn.md`: top 10 at risk with reasons, and the back-test line. Charlie reads it weekly.
- `support/outbox/winback-<user_id>.md`: held drafts.

## The ladder
- Human-led: Charlie reads the at-risk list and writes to people himself.
- Human-assisted: the job also drafts the notes in `outbox/`; Charlie sends them.
- Fully autonomous: the list refreshes weekly with no input. Notes still wait for Charlie, because nothing here sends email on its own.

## The human
What stays with Charlie: sending any note to an at-risk user, any discount or price change, deciding whether to chase a cancelled user at all.

## Tools
Python stdlib plus `requests` for the rules and back-test; no model needed for scoring. Gemini 2.5 Flash and Groq free tiers for drafting notes and plain-word reasons. PostHog free tier and the provider's read access (as of Oct 2026, check the limit). GitHub Actions weekly cron.

## Build notes
- Rules first because a one-person app has tens or hundreds of accounts, not thousands. Add a small logistic model only at 200 or more accounts and 30 or more churn events, written in stdlib.
- Label every prediction with the number of accounts behind it. Under 30 accounts it is a prompt for a look, not a forecast.
- Consumer subscriptions: a user who wants to cancel must be able to; the notes never obstruct cancelling.
- If health history is missing, run on the current snapshot only and log it under `skipped` in `ventures/<slug>/board.json`.
- Tests: fixture history with one planted churner must be caught at 14 days out.
