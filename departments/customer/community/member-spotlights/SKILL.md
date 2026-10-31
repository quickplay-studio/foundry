---
name: member-spotlights
title: Member Spotlights
department: customer
function: community
autonomy: assisted
stage: support
builds_on: []
breaks_into: [find-wins, request-permission, draft-spotlight, schedule-and-log]
replaces: "a community manager writing member stories"
runs_on: github
status: ready
---

# Member Spotlights

Find and celebrate member wins.

## Reads from the brain
- `brain/company.md`: voice (plain, direct, UK English, no exclamation marks, proof over adjectives), constraints (nothing regulated without a human)
- `ventures/<slug>/brain.md`: the venture's problem, who, mvp, proof. A win is a user getting what the mvp line promises.

## Inputs
- Community posts where a member reports a result: GitHub Discussions on the venture repo (`GH_TOKEN`, or a fine-grained token as a secret) and a free Discord if one exists.
- `ventures/<slug>/support/tickets.json`: praise tickets. `support/advocacy.json`: quotes with `permission` status.
- `support/health.json`: green users with long tenure. `support/events.json`: optional `milestones` (for example a 30-day streak or a 100th core event) read from PostHog.
- `support/community/spotlights.json`: who has been featured and when.

## Steps
1. Find up to 5 candidates a week: a member who shows a concrete result, a milestone event, or a praise ticket with a specific story. Skip anyone featured in the last 90 days, anyone with an open complaint, and any win that is about money, health or children.
2. Rank by specificity (a number or a before and after), recency and fit with the mvp line. Keep the top 2.
3. Draft a permission request for each: 50 words or fewer, says exactly what would be shared, where, and that no is fine. A public post is still asked about before it is featured. Save as `permission: pending`. Charlie sends it.
4. When Charlie records `permission: granted` in `spotlights.json`, draft the spotlight: 80 to 120 words, the member's own words in at most two verbatim quotes, what they did, what changed, one link. Use the first name or handle exactly as they agreed. State nothing they did not say.
5. Draft the post for GitHub Discussions (announcements) and a one-line caption for Marketing to reuse. Propose a date; the cadence is one spotlight every two weeks, evenings or weekends UK time.
6. Open a pull request with the drafts. After posting, Charlie sets `posted` and the job logs it.

## Output
- `ventures/<slug>/support/community/spotlights/<yyyy-mm-dd>-<handle>.md`: permission request, spotlight draft, caption, proposed date.
- `support/community/spotlights.json`: `[{"id", "user_id_or_handle", "win", "permission", "requested", "posted", "url"}]`. Permission is none, pending, granted or refused.

## The ladder
- Human-led: Charlie finds and writes spotlights; the job lists candidates.
- Human-assisted: the job finds candidates and drafts the request and the post; Charlie sends and approves.
- Fully autonomous: only the candidate list and the log. Nothing is featured without the member's yes.

## The human
What stays with Charlie: sending each permission request, deciding whether a win is worth sharing, approving each post, and refusing anything involving money, health or children.

## Tools
GitHub Discussions (free), PostHog free tier for milestone events (as of Oct 2026, check the limit), Gemini 2.5 Flash and Groq free tiers. GitHub Actions weekly cron.

## Build notes
- Under 30 members the list will often be empty. Write "no candidates" and stop.
- A refusal is final: `refused` is never asked again.
- Keep a handle hash, not the handle, in the committed JSON if the repo is public.
- Tests: a candidate with an open complaint is skipped; a draft with a quote not in the source text is rejected.
- GitHub implementation: `run.py` beside this file (jobkit).
