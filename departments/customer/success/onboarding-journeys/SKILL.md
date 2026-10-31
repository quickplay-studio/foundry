---
name: onboarding-journeys
title: Onboarding Journeys
department: customer
function: success
autonomy: assisted
stage: support
builds_on: []
breaks_into: [define-activation, map-the-path, draft-sequence, measure-drop-off]
replaces: "a paid lifecycle-email tool plan or an onboarding consultant"
runs_on: claude-code
status: ready
---

# Onboarding Journeys

Guide every new user through activation step by step.

## Reads from the brain
- `brain/company.md`: voice (plain, direct, UK English, no exclamation marks, say what it does first), constraints (free tools only)
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof. The mvp line decides the activation event.

## Inputs
- `ventures/<slug>/support/events.json`. If missing, create it with keys `activation`, `core`, `paid`, `cancel`, `expected_active_days_per_14`, `weights`, `payments`, `proposed: true`, proposing event names from the mvp line.
- PostHog funnel from sign-up to the activation event, last 30 days (secrets `POSTHOG_API_KEY`, `POSTHOG_PROJECT_ID`, read only).
- `support/tickets.json`: how-to tickets from users in their first 14 days, to find where they get stuck.
- `support/faq.json`: live entries to link from each step.

## Steps
1. Define activation: the one event that shows the user got what the mvp line promises (not sign-up, not a page view). Write it to `events.json` as `activation`.
2. Map the path in 3 to 5 steps from sign-up to activation. For each step record the PostHog event that proves it and the point after which a user is probably stuck (`stuck_after_hours`).
3. Read the funnel. Report sign-ups, activated, share per step and median hours to activate. Under 20 sign-ups, write "too few to read" and skip the numbers.
4. Draft the sequence. For each step: an in-app line of 20 words or fewer, and one email (subject of 6 words or fewer, body of 70 words or fewer, one link, one action). Rules: send only if the step event has not fired after `stuck_after_hours`; stop on the activation event; at most one email a day and five in total; every email is about using the product, no promotion and no upsell.
5. Open a pull request with `support/onboarding.json` and `support/onboarding.md` (all copy in reading order). Note the consent and sender wording for Legal `data-protection` to check before the first send.
6. After launch, a weekly run refreshes the funnel table, names the step with the worst drop-off, and proposes one copy change for it as a pull request.

## Output
- `ventures/<slug>/support/onboarding.json`: `{"activation_event", "stop_event", "max_emails": 5, "steps": [{"id", "goal", "event", "stuck_after_hours", "in_app", "email": {"subject", "body", "send_after_hours"}}], "funnel": {"as_of", "signups", "activated", "by_step": []}}`
- `support/onboarding.md`: the copy and the funnel table, for Charlie to approve.

## The ladder
- Human-led: Charlie designs the path and writes the copy; the job supplies the funnel and the stuck points.
- Human-assisted: the job drafts everything and opens a pull request; Charlie edits and merges.
- Fully autonomous: weekly funnel refresh and in-app copy tweaks merge on their own; emails always wait for Charlie until the venture has earned money.

## The human
What stays with Charlie: confirming the activation event, approving every email before the first send, the consent wording, choosing the sender, and any change that adds a message.

## Tools
PostHog free tier for events and funnels (as of Oct 2026, check the limit). The free tier of an email sender the venture already uses; the job never creates an account. Gemini 2.5 Flash and Groq for the weekly refresh. The first design run is a Claude Code session with Sonnet, because choosing the activation event takes judgment about the product.

## Build notes
- One design run per venture in Claude Code; the weekly refresh runs on GitHub Actions with free models.
- If the product has no PostHog events yet, write the event names the build must emit into `onboarding.md` and log it under `skipped` in `ventures/<slug>/board.json`.
- Sending is a separate step owned by the venture's email setup; this skill writes the copy and the rules, not a mail server.
- Tests: `onboarding.json` must have 3 to 5 steps, no email over 70 words, and a `stop_event`.
