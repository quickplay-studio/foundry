---
name: brain-interview
title: Second brain interview
department: brain
autonomy: assisted
runs_on: claude-code
status: ready
---

# Second brain interview

How the company brain gets built and kept current. Run it in Claude Code (Sonnet) when a section of `brain/company.md` is empty or stale, or when a venture needs its `brain.md` filled beyond what Lodestone sent. One sitting, typed or dictated, as long as Charlie wants.

## Steps
1. Read `brain/company.md` and list the sections that are empty, say "(filled by...)" or are older than ninety days.
2. Ask one question per section, in this order: who we are, what we make, who we sell to, voice, constraints, offers and proof, what we will not do. Follow up only when an answer is vague enough that an agent would have to guess.
3. For a venture: read `ventures/<slug>/brain.md`, then ask what Lodestone could not know: the exact first user, the one feature the MVP must have, the price Charlie would be happy to charge, the ad budget, the deadline, anything off limits.
4. Write the answers back in Charlie's words, trimmed, under the right heading. Dates on anything that will go stale.
5. Append a one-line entry under "Decisions" in the venture brain for every choice made.

## Output
- Updated `brain/company.md` or `ventures/<slug>/brain.md`, committed with the message `brain: <section or slug>`.

## The human
Every answer is Charlie's. The agent never fills a section from its own assumptions; an empty section is better than an invented one.
