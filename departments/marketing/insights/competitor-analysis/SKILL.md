---
name: competitor-analysis
title: Competitor Analysis
department: marketing
function: insights
autonomy: solo
stage: validate
builds_on: []
breaks_into: [find-competitors, collect-content, extract-hooks, find-gaps]
replaces: "a competitor research freelancer or a paid social intelligence tool"
runs_on: github
status: ready
---

# Competitor Analysis

Collects competitor pages and public content, reads transcripts where they exist, and extracts the hook patterns that work in this niche. Free; runs once at validation and again before launch.

## Reads from the brain
- `brain/company.md`: voice, and the rule never to scrape against a site's terms.
- `ventures/<slug>/brain.md`: problem, who and gap. The gap is what competitors do not say.

## Inputs
- Optional: `ventures/<slug>/launch/inputs/competitors.json`, `[{name, url, youtube, instagram, tiktok}]`. If absent, step 1 builds it.
- Firecrawl free tier (`FIRECRAWL_API_KEY`) for public pages. As of Oct 2026, check the limit.
- YouTube Data API (`YOUTUBE_API_KEY`) for titles, dates, views, durations.
- Optional: `launch/inputs/transcripts/<video-id>.txt`, transcripts pulled through Charlie's vidIQ account.

## Steps
1. Build the list. With no input file, run three Firecrawl searches on the problem and gap phrases, keep up to five distinct products or creators, and write them to `competitors.json` for Charlie to correct.
2. Read each competitor's home and pricing page with Firecrawl. Skip any site whose robots.txt or terms forbid it, and record the reason. Extract headline, price and promise.
3. For each YouTube channel, list the latest 30 videos: title, date, views, duration, first 200 characters of the description. Other platforms: public pages only, else skip.
4. Transcripts: use files in `inputs/transcripts/` only. Never download video or audio from any platform.
5. Label hooks with `foundry.util.ask_json`: for each title and each transcript's first 15 seconds, return `{pattern, template}` where pattern is one of curiosity gap, number list, contradiction, pain call-out, how-to promise, before and after, authority, direct offer, and template replaces specifics with slots such as `<number>` or `<pain>`.
6. Aggregate by pattern: count, median views, one example (a quote of 15 words or fewer, with its URL).
7. Find gaps: ask the model what the brain's `gap` says that no competitor page or hook says. Pass both texts; accept only gaps backed by a quoted line.
8. Write the outputs. Set this job to `done` in `ventures/<slug>/board.json`; a failed source goes under `skipped`.

## Output
- `ventures/<slug>/launch/insights/competitors.md`: Table of competitors (name, promise, price, channels), Hook patterns (pattern, count, median views, example), Gaps (up to five, each with the quote).
- `ventures/<slug>/launch/insights/hook-patterns.json`: `[{pattern, template, platform, count, median_views, examples:[{url, text}]}]`. Read by `hook-writing`; Intelligence's `competitor-teardown` may link the markdown.

## The ladder
- Human-led: Charlie watches competitors by hand and keeps notes.
- Human-assisted: the job collects and labels; Charlie corrects the competitor list.
- Fully autonomous: monthly refresh of patterns, no review. This is the default.

## The human
What stays with Charlie: confirming who the real competitors are, and anything that needs a login or breaks a site's terms.

## Tools
Free first. Firecrawl free tier for pages, YouTube Data API free quota, vidIQ (competitor and outlier tools, Charlie's account) for transcripts and outliers, Gemini 2.5 Flash and Groq through `foundry.util.ask_json` (as of Oct 2026, check the limit). Apify actors only where a site's terms allow automated reading.

## Build notes
- Not built yet. `workflow_dispatch` job; stdlib plus `requests`.
- Pattern labels need a model. With none available, write the collected table and leave `hook-patterns.json` empty with a note.
- Quote only short extracts. The output records patterns, not copied wording.
