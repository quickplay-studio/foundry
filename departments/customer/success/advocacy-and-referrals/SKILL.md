---
name: advocacy-and-referrals
title: Advocacy and Referrals
department: customer
function: success
autonomy: assisted
stage: support
builds_on: [health-scoring]
breaks_into: [find-happy-users, draft-the-ask, record-permission, track-referrals]
replaces: "a referral-programme tool or a paid review-collection service"
runs_on: github
status: ready
---

# Advocacy and Referrals

Turn the happiest users into referrals, reviews and case studies.

## Reads from the brain
- `brain/company.md`: voice (plain, direct, UK English, no exclamation marks, proof over adjectives), constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, money (plans, prices), proof, and where reviews live (store listing, Trustpilot or similar), if stated

## Inputs
- `ventures/<slug>/support/health.json`: `user_id`, band, score, tenure.
- `support/tickets.json`: praise tickets and any negative or open ticket per user.
- `support/advocacy.json`: asks already made, permissions, referral counts. Create it if missing.
- Community praise from `support/community/replies-*.md` and GitHub Discussions, if a community exists.
- Referral sign-ups from PostHog events carrying a `ref` property (secrets `POSTHOG_API_KEY`, `POSTHOG_PROJECT_ID`).

## Steps
1. Select up to 10 candidates per run: green band for 30 days or more, activated, tenure of 30 days or more, no negative ticket and no open ticket in 60 days, not asked in the last 90 days. Paying users first. Praise tickets jump the queue.
2. Choose one ask per person: a review, a referral, or a short testimonial. Never stack asks. Match the ask to the person: a praise ticket gets a testimonial request, a long-tenure user gets a review request, a heavy sharer gets a referral request.
3. Draft the ask: 60 words or fewer, thanks for something specific they did, one ask, one link. Ask for an honest review, never a positive one. Do not offer a reward in return for a review. Check platform rules and Legal `consumer-law-check` before any incentive; this is not legal advice.
4. Referral mechanics: a link with `?ref=<code>` and a PostHog event on sign-up. Any reward must cost nothing the venture cannot cover, and Charlie approves it per venture.
5. Case studies: draft 150 words or fewer from the person's own words, quotes verbatim, no claim they did not make, no money, health or children detail. Save with `permission: pending`. Nothing is used publicly until the status is `granted`.
6. Open a pull request with the drafts in `support/advocacy.md` and the updated `advocacy.json`. Charlie sends the asks.
7. On later runs, update replies and referral counts (sign-ups and paid conversions by `ref`) and move granted quotes into the `proof` list.

## Output
- `ventures/<slug>/support/advocacy.json`: `{"updated": "...", "asks": [{"user_id", "type", "sent", "outcome"}], "proof": [{"user_id", "quote", "source", "permission", "approved_on"}], "referrals": {"clicks": 0, "signups": 0, "paid": 0}}`
- `support/advocacy.md`: the drafts and the proof bank in plain markdown. Marketing reads `proof` entries with `permission: granted` for the landing page.

## The ladder
- Human-led: Charlie picks who to ask and writes the messages; the job lists eligible users.
- Human-assisted: the job drafts every ask and case study; Charlie sends and approves.
- Fully autonomous: only the tracking. Asks are never sent by the job.

## The human
What stays with Charlie: sending each ask, approving any reward, confirming permission for every named quote, and refusing a case study when the story involves money, health or children.

## Tools
Python stdlib plus `requests`; Gemini 2.5 Flash and Groq free tiers for drafts. PostHog free tier for referral events (as of Oct 2026, check the limit). Tally free form to collect a testimonial and a tick-box permission (as of Oct 2026, check the limit). GitHub Actions weekly cron.

## Build notes
- Fake or paid-for reviews are off limits. The check in step 3 is a hard rule in code: reject any draft that mentions a reward next to the word review.
- Under 20 users there may be no eligible candidates. Write "none eligible" and stop.
- Store only `user_id`; the real contact stays in the inbox tool.
- Tests: a user with an open ticket must never be selected; a draft offering a free month for a review must be rejected.
- GitHub implementation: `run.py` beside this file (jobkit).
