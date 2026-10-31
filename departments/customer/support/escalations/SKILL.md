---
name: escalations
title: Escalations
department: customer
function: support
autonomy: human
stage: support
builds_on: [ticket-triage]
breaks_into: [detect-triggers, build-case, write-brief, track-to-close]
replaces: "a support lead or customer-success manager watching the queue"
runs_on: github
status: ready
---

# Escalations

Spot the angry, the churn risk and the edge case, and get a human there.

## Reads from the brain
- `brain/company.md`: voice, constraints (nothing regulated without a human and a solicitor)
- `ventures/<slug>/brain.md`: the venture's problem, who, money (plans, prices, refund line), proof

## Inputs
- `ventures/<slug>/support/tickets.json`: tickets with route `escalate`, priority P1 or P2, or no reply past target (P1 over 4 hours, others over 72 hours).
- `support/outbox/`: what was already drafted or sent for each ticket.
- Optional: `support/health.json` and `support/churn.json` for account band and risk; payment events (`support/data/payments.csv` or the provider read key `PAYMENTS_READ_KEY`) for plan and spend; community flags from `support/community/moderation-log.json`.

## Steps
1. Detect triggers: P1; sentiment of -2; third contact in 7 days; refund, chargeback, legal or data rights wording; payment taken and no access; the same bug reported by 3 or more users in 7 days (an incident); a public complaint flagged by moderation; an account in the red band or with churn risk of 70 or more writing in.
2. Build the case per trigger: dated message timeline in three lines, plan and spend, last product activity, what was already sent, and the one thing the user wants.
3. Set the deadline. Data rights request: one month from receipt (Legal `data-protection` confirms). Chargeback: the payment provider's dispute date. Incident: same day. Anything else: 24 hours.
4. Offer options for each case: reply only, fix then reply, refund, no action. State the cost and risk of each in one line. Draft the recommended reply as text for Charlie; never send it.
5. Write the one-page brief: top 5 cases ranked by deadline, then severity, each in 6 lines or fewer. Overflow goes to the queue file.
6. Alert: open or update one GitHub issue labelled `support-escalation`, titled with the date, body equal to the brief. GitHub emails Charlie. Then stop.
7. On later runs, move cases to `resolved` when the ticket closes, and log the cause. Repeated causes go to `faq-and-self-serve` and `macro-authoring` as gaps.

## Output
- `ventures/<slug>/support/escalations.md`: the one-page brief, overwritten each run. Charlie reads it.
- `support/escalations-queue.json`: `{"updated": "...", "cases": [{"id", "ticket_ids", "trigger", "deadline", "options", "draft_reply", "status", "cause"}]}`. Status is open, waiting or resolved.

## The ladder
- Human-led: Charlie reads the queue himself; the job only lists the triggers it found.
- Human-assisted: the job writes the case, the options and a draft reply; Charlie decides and sends.
- Fully autonomous: not allowed. The only automatic message is a holding line from a macro Charlie has approved, saying the message was received and when to expect a reply.

## The human
What stays with Charlie: every decision on refunds, goodwill, legal wording, data rights requests, security reports, and any reply to someone angry. The job never promises money, dates or outcomes.

## Tools
Gemini 2.5 Flash and Groq free tiers for case summaries. GitHub Issues as the alert channel (no extra tool). GitHub Actions on a schedule, every hour (as of Oct 2026, check Actions minutes for a private repo). No Claude at run time.

## Build notes
- The trigger list lives in `support/config.json` under `escalation_triggers` so Charlie can tune it without touching the skill.
- A run with no triggers writes "No escalations" and opens no issue.
- Never copy full message text into the issue if the repo is public; use the ticket id and summary only.
- Tests: a fixture with a planted refund threat and a planted incident must both appear, ranked by deadline.
- GitHub implementation: `run.py` beside this file (jobkit).
