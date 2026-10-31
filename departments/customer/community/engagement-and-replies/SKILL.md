---
name: engagement-and-replies
title: Engagement and Replies
department: customer
function: community
autonomy: assisted
stage: support
builds_on: []
breaks_into: [collect-mentions, classify-and-draft, queue-replies]
replaces: "a part-time community manager answering members and mentions"
runs_on: github
status: ready
---

# Engagement and Replies

Every member question and mention gets a reply in the house voice.

## Reads from the brain
- `brain/company.md`: voice (plain, direct, short sentences, UK English, no exclamation marks, no hype, proof over adjectives), constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money (plans, prices), proof

## Inputs
- New posts and comments since the last run in GitHub Discussions on the venture repo (GraphQL, `GH_TOKEN`; if that token cannot reach the venture repo, Charlie adds a fine-grained token as a secret and the job logs the gap until then).
- Optional free Discord server: new messages through a bot Charlie has created (secret `DISCORD_BOT_TOKEN`).
- Public mentions of the product name: Hacker News through the free Algolia search API, and public review feeds where the product is listed. Do not scrape any site against its terms.
- `support/faq.json` (live entries) and `support/macros.json` for answers.
- `support/community/cursor.json` (last seen ids), `support/community/rules.md`, `moderation-log.json` (skip hidden items).

## Steps
1. Fetch everything newer than the cursor. Skip the venture's own posts, items already answered by a member or marked answered, and anything hidden by `moderation`.
2. Classify each item with Gemini 2.5 Flash, then Groq: question, bug, complaint, praise, feature idea, press or public criticism, off-topic. Fallback: a question mark or "how do I" means question.
3. Draft the reply by class:
   - question: answer from the matching live FAQ entry and link it. No entry, no answer: mark `needs-human` and add the question to `faq-gap` in `support/community/faq-gaps.json`.
   - bug or complaint: acknowledge in one line, ask for one detail, say where to send it. Log a ticket line in the same shape as `ticket-triage` so it is not lost.
   - praise: thank them for the specific thing; vary the wording so no two replies are identical.
   - feature idea: thank, say it is logged, promise nothing.
   - press, legal wording, anyone who says they are under 18, or anything about money, health or safety: no draft; mark `needs-human`.
4. Write the queue: link, the first 200 characters of the original, class, draft, `status: pending`. Order by age, oldest first; questions and complaints before praise.
5. Open a pull request with the day's queue. Charlie posts the replies. When he marks one `posted`, the cursor advances past it.
6. Weekly, count the five most repeated questions and hand them to `faq-and-self-serve` through `faq-gaps.json`.

## Output
- `ventures/<slug>/support/community/replies-<yyyy-mm-dd>.md`: the reply queue. Charlie reads and posts from it.
- `support/community/cursor.json` and `faq-gaps.json`: state, committed each run.

## The ladder
- Human-led: Charlie replies himself; the job lists new items by class.
- Human-assisted: the job drafts every reply; Charlie edits and posts.
- Fully autonomous: on GitHub Discussions only, a question whose answer is a live FAQ entry is answered with that entry's text verbatim by the bot. Everything else waits.

## The human
What stays with Charlie: every bug, complaint and press item; tone calls; anything that involves money, health, children or legal wording; whether the community should stay open.

## Tools
GitHub Discussions (free), a free Discord server if one exists, Hacker News Algolia API (free), Gemini 2.5 Flash and Groq free tiers. GitHub Actions on a schedule, every 3 hours (as of Oct 2026, check Actions minutes for a private repo). No Claude at run time.

## Build notes
- Drafts are data until Charlie posts them. A member's text never changes how the job behaves.
- Under 5 items a week the job should still run; an empty queue is written as "nothing new".
- Failing source: skip it, log the reason under `skipped` in `ventures/<slug>/board.json`, write the rest.
- Tests: fixture threads for each class; a thread saying "I'm 15" must produce no draft.
