---
name: renewals-and-expansion
title: Renewals and Expansion
department: customer
function: success
autonomy: human
stage: support
builds_on: [health-scoring]
breaks_into: [find-renewal-window, spot-expansion-signal, write-brief]
replaces: "an account manager timing renewals and upsells"
runs_on: github
status: ready
---

# Renewals and Expansion

Time renewal conversations and spot upsell openings; the ask is yours.

## Reads from the brain
- `brain/company.md`: voice, constraints (free tools only; Charlie approves every price and discount)
- `ventures/<slug>/brain.md`: the venture's money line (plans, prices, billing interval, trial length) and proof. Expansion is only possible if the money line lists a higher plan or add-on.

## Inputs
- `ventures/<slug>/support/health.json`: band, score and trend per `user_id`.
- `support/churn.json` if it exists: risk and reasons.
- Payment events (`PAYMENTS_READ_KEY` or `support/data/payments.csv`): plan, price, billing interval, next renewal date, trial end date.
- PostHog usage against plan limits (secrets `POSTHOG_API_KEY`, `POSTHOG_PROJECT_ID`) and `support/events.json` for event names.
- `support/tickets.json`: open tickets per `user_id`.

## Steps
1. List the window: annual plans renewing in the next 30 days, monthly plans in the red or amber band, and trials ending in the next 7 days.
2. Classify each account. `safe`: green band and no open ticket. `at-risk`: amber or red, or churn risk of 50 or more, or an open P1 or P2 ticket. `upgrade-candidate`: green band, tenure of 30 days or more, and either hitting a plan limit or using a paid-only feature 3 or more times in 14 days.
3. Work out revenue at stake: the sum of plan prices renewing in the window, and the gross value of `at-risk` accounts. Use the prices in the money line; if a price is unknown, leave it blank.
4. Recommend one move per listed account: leave alone, helpful nudge, personal note from Charlie, or upgrade mention. Never recommend a discount; if a discount looks needed, say so as a question for Charlie.
5. Draft short notes for the top 3 accounts as text in the house voice. Mark each `draft, not sent`.
6. Write the one-page brief and stop. The job does not send renewal reminders, notices or offers.

## Output
- `ventures/<slug>/support/renewals.md`: one page. Counts by class, revenue at stake, up to 10 accounts each with a reason and a recommended move, three drafted notes. Charlie reads it.
- `support/renewals.json`: `{"updated": "...", "window_days": 30, "accounts": [{"user_id", "class", "plan", "renewal_date", "value", "reasons": [], "move"}]}`

## The ladder
- Human-led: Charlie decides who to contact and what to offer; the job supplies the list and reasons.
- Human-assisted: the job also drafts the notes and the move; Charlie edits and sends.
- Fully autonomous: not allowed. The ask is Charlie's. The job only produces the brief.

## The human
What stays with Charlie: every renewal conversation, every upgrade ask, every price, discount or refund, and whether an auto-renewal reminder is needed. Ask Legal `consumer-law-check` what notice duties apply to auto-renewing plans before the first annual plan renews. This is not legal advice.

## Tools
Python stdlib plus `requests`; Gemini 2.5 Flash and Groq free tiers for the notes. PostHog free tier and the payment provider's read access (as of Oct 2026, check the limit). GitHub Actions weekly cron.

## Build notes
- A consumer app with monthly plans has few renewals; the brief will often be short. That is correct. Do not pad it.
- No expansion section when the money line has a single plan. Say "single plan, no expansion route" once.
- If payments cannot be read, write a brief from health alone and log the gap under `skipped` in `ventures/<slug>/board.json`.
- Keep user ids only; no names or emails in the brief.
- Tests: fixture with one annual renewal at 20 days, one amber monthly account, one green account at a plan limit; each must land in its class.
