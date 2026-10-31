---
name: event-coordination
title: Event Coordination
department: customer
function: community
autonomy: human
stage: none
builds_on: []
breaks_into: [decide-format, propose-slots, build-run-sheet, draft-comms]
replaces: "a community or events manager"
runs_on: github
status: ready
---

# Event Coordination

AMAs, calls and spotlights on a cadence people can count on.

## Reads from the brain
- `brain/company.md`: voice (plain, direct, UK English, no exclamation marks), working hours (evenings and weekends UK time), constraints (free tools only)
- `ventures/<slug>/brain.md`: the venture's problem, who, mvp, proof, so topics fit the product

## Inputs
- Community size and activity: members and posts in the last 30 days from GitHub Discussions on the venture repo (`GH_TOKEN`, or a fine-grained token as a secret) or a free Discord.
- Topics: top open questions from `ventures/<slug>/support/faq.json` (entries `needs-human-fact` or `stale`), `support/community/faq-gaps.json`, and `support/community/spotlights.json`.
- `support/community/events.json`: past and planned events with attendance and questions.

## Steps
1. Decide whether a live event is worth it. Default rule: under 50 active members in 30 days, run a text AMA in a Discussions thread instead of a call. Charlie can override this threshold in `events.json` under `min_members_for_live`.
2. Pick the format and the cadence: text AMA, spotlight evening, or a short call. One event a month at most; skip months with a gap in `events.json` rather than filling them.
3. Propose two slots in the next 3 weeks, evenings or weekends, in UK time with the time zone named, avoiding UK bank holidays. Charlie picks; the job does not book anything.
4. Build the run sheet: T minus 7 days announce, T minus 1 reminder, start, close, T plus 1 recap. Include a Tally free form link to collect questions in advance, pre-filled with the top five topics from step 1's inputs.
5. Draft the announcement, the reminder and the recap in the house voice. Each states what happens, when, how to join and what is free. No hype and no exclamation marks.
6. Write the one-page brief and stop. After the event, a second run drafts the recap and turns unanswered questions into entries in `faq-gaps.json`.

## Output
- `ventures/<slug>/support/community/event-brief.md`: one page. Why now, format, two slots, run sheet, the three drafts, topics. Charlie reads it.
- `support/community/events.json`: `[{"id", "date", "format", "topic", "attendance", "questions": [], "status"}]`. Status is proposed, scheduled, held or skipped.

## The ladder
- Human-led: Charlie decides, hosts and says everything live; the job gives the brief.
- Human-assisted: the job also drafts the announcement, reminder and recap; Charlie posts them.
- Fully autonomous: not allowed. The job produces the brief and, after an event Charlie marks `held`, the recap draft.

## The human
What stays with Charlie: whether to hold an event, picking the slot, hosting, everything said live, and consent if a call is recorded. Nothing about money, health or children is promised on a call. This is not legal advice.

## Tools
GitHub Discussions (free) for a text AMA or announcements, a free Discord stage or a free video-call plan for live sessions (as of Oct 2026, check the limit), Tally free form for questions (check the limit), Gemini 2.5 Flash and Groq free tiers for drafts. GitHub Actions monthly cron, plus one run after each held event.

## Build notes
- A thin community is the normal case. The brief should say "run a text AMA" without apology.
- Do not invite anyone by direct message or email from this job.
- Calendar entries are Charlie's; the job writes slots as text, never into a calendar.
- Failing source: log it under `skipped` in `ventures/<slug>/board.json` and write the brief from what is available.
- Tests: a fixture with 20 members must recommend a text AMA; slots must fall in evenings or weekends.
- GitHub implementation: `run.py` beside this file (jobkit).
