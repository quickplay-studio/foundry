---
name: moderation
title: Moderation
department: customer
function: community
autonomy: assisted
stage: support
builds_on: []
breaks_into: [scan-new-content, apply-rules, hide-and-log, review-queue]
replaces: "a volunteer or paid community moderator"
runs_on: github
status: ready
---

# Moderation

Spam, conduct and noise handled quietly.

## Reads from the brain
- `brain/company.md`: voice (plain, direct, UK English, no exclamation marks), constraints (nothing regulated without a human)
- `ventures/<slug>/brain.md`: the venture's who and problem, so on-topic is defined by the product, not guesswork

## Inputs
- New posts and comments since the last run in GitHub Discussions on the venture repo (GraphQL, `GH_TOKEN`; a fine-grained token as a secret if `GH_TOKEN` cannot reach it) and, if one exists, a free Discord server through a bot (secret `DISCORD_BOT_TOKEN`).
- `ventures/<slug>/support/community/rules.md`: the house rules. If missing, create five short rules: be civil, stay on topic, no spam or promotion, no personal data, no harassment. Charlie edits.
- `support/community/blocklist.json` (repeat offenders, banned domains) and `moderation-log.json` (history).

## Steps
1. Fetch content newer than the cursor. Skip items by Charlie or the venture account.
2. Score each item with simple signals first: link count, a domain on the blocklist, repeated text, an account created today with a link, all capitals. Then classify with Gemini 2.5 Flash, then Groq, into one of: clean, noise, spam, abuse, personal-data, safety, legal.
3. Act by class:
   - clean: nothing.
   - noise (off-topic, low effort): leave it; add a gentle rules-pointer reply to the queue as a draft.
   - spam at confidence 0.95 or more: hide it (GitHub `minimizeComment`, Discord delete) and log it. Reversible.
   - spam below 0.95: queue it.
   - abuse or harassment: hide, log, queue for Charlie.
   - personal-data (emails, phone numbers, addresses, card numbers): hide at once to limit harm, log, queue.
   - safety (self-harm, threats, anything involving a child): do not reply, do not give advice, queue as P1 and open a GitHub issue labelled `support-escalation`.
   - legal (defamation claims, takedown threats): do nothing public, queue as P1.
4. Three hides of the same author in 14 days: add them to the blocklist and block if the platform allows. Log it.
5. Write the queue file (link, class, confidence, what was done, what Charlie must decide) and a weekly count by class.
6. Open a pull request with the queue and log changes. Charlie reviews and reverses any mistake by setting `reversed: true`; the job learns the pattern.

## Output
- `ventures/<slug>/support/community/moderation-log.json`: `[{"id", "time", "platform", "url", "author_hash", "class", "action", "confidence", "reversed"}]`
- `support/community/moderation-queue.md`: items needing a decision, newest first.
- `support/community/blocklist.json`: authors (hashed) and domains.

## The ladder
- Human-led: Charlie moderates; the job only flags with a class and confidence.
- Human-assisted: the job hides high-confidence spam and personal data and queues the rest.
- Fully autonomous: also blocks repeat spammers after three hides. Abuse, safety and legal always go to Charlie.

## The human
What stays with Charlie: banning anyone who is not an obvious spammer, every safety item, appeals, rule changes, and whether the community should exist at all. If members can post to each other, ask Legal `regulatory-screen` whether Online Safety Act duties apply before opening it. This is not legal advice.

## Tools
GitHub Discussions (free) and a free Discord server, both with their own moderation APIs. Gemini 2.5 Flash and Groq free tiers. GitHub Actions on a schedule, every 3 hours (as of Oct 2026, check Actions minutes for a private repo).

## Build notes
- Hide, never delete, on GitHub, so every action can be undone. Discord has no hide, so delete there only spam at confidence 0.95 or more, and log the class and link, never the text.
- Store a hash of the author handle, not the handle, in the log of a public repo.
- A failing platform call is logged under `skipped` in `ventures/<slug>/board.json`; the queue is still written.
- Tests: planted spam, planted email address, planted self-harm line; each must land in its class and action.
- GitHub implementation: `run.py` beside this file (jobkit).
