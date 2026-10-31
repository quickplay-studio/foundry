---
name: audience-analysis
title: Audience Analysis
department: marketing
function: insights
autonomy: solo
stage: validate
builds_on: []
breaks_into: [collect-text, strip-personal-data, cluster-themes, build-language-bank]
replaces: "a customer research freelancer or a social listening tool"
runs_on: github
status: ready
---

# Audience Analysis

Mines public comments, reviews and, after launch, our own comments and DMs for the questions people ask, the objections they raise and the words they use. Free; runs before launch and weekly after.

## Reads from the brain
- `brain/company.md`: voice and constraints.
- `ventures/<slug>/brain.md`: problem and who, which set the search terms and the communities.

## Inputs
- Public text: YouTube comments on the top niche videos (`commentThreads.list`, 1 quota unit a call, up to 100 threads a call, `YOUTUBE_API_KEY`), Hacker News comments (Algolia API), and Reddit threads, Play Store reviews and Trustpilot reviews of competitors through Apify actors (`APIFY_TOKEN`). Use a source only where its terms allow automated reading. As of Oct 2026, check the limit.
- After launch: comments on our own channels (YouTube API, Meta Graph API with `META_ACCESS_TOKEN`).
- DMs: only text Charlie pastes into `ventures/<slug>/launch/inputs/dms.txt`. The job never reads an inbox.

## Steps
1. Build 5 to 10 search terms and communities from the brain. Collect up to 500 items per source.
2. Strip personal data in code before any model sees the text: usernames, handles, emails, phone numbers, names after "my name is". Raw text is held in the workflow run only and never committed.
3. Drop items under five words, spam and duplicates.
4. With `foundry.util.ask_json`, label each batch of 50 as question, objection, desired outcome or other, with a theme of 2 to 4 words. Merge near-identical themes.
5. Count per theme. Keep the top 10 questions and top 8 objections. For each, pick up to two quotes of 20 words or fewer, anonymised.
6. Build the language bank: phrases people use, 8 words or fewer, seen more than once, taken verbatim.
7. For each objection, write a one-line answer using only facts in `brain.md`. No fact, no answer; mark it `no answer yet`.
8. Write 10 content ideas, each tied to the question or objection it answers.
9. Write outputs; set this job to `done` in `ventures/<slug>/board.json`. A failed source goes under `skipped`.

## Output
- `ventures/<slug>/launch/insights/audience.md`: Questions, Objections (with answers), Language bank, Content ideas.
- `ventures/<slug>/launch/insights/audience.json`: `{questions:[{theme, count, quotes}], objections:[{theme, count, answer}], language_bank:[], content_ideas:[{idea, answers}]}`. Read by `hook-writing`, `landing-page-copy`, `lead-magnet-builds` and Intelligence's validate report.

## The ladder
- Human-led: Charlie reads comments and threads and writes notes.
- Human-assisted: the job clusters and ranks; Charlie reads the objections.
- Fully autonomous: weekly refresh after launch, feeding the other creation jobs. This is the default.

## The human
What stays with Charlie: pasting DMs, deciding which objections the product can honestly answer, and removing any theme that touches a regulated area.

## Tools
Free first. YouTube Data API free quota, Hacker News Algolia API, Apify free tier, Gemini 2.5 Flash and Groq through `foundry.util.ask_json` (as of Oct 2026, check the limit). Legal's `data-protection` governs retention; this is not legal advice.

## Build notes
- Not built yet. Stdlib plus `requests`; the personal-data strip is a tested function with fixtures.
- With no model, write counts of raw terms and the language bank only; label the rest `needs model`.
- Delete anything raw from artifacts after 30 days.
