---
name: trend-monitoring
title: Trend Monitoring
department: marketing
function: insights
autonomy: solo
stage: validate
builds_on: []
breaks_into: [build-queries, collect-signals, score-topics, write-brief]
replaces: "a trend-tracking subscription or a social listening freelancer"
runs_on: github
status: ready
---

# Trend Monitoring

Watches the venture's niche for breaking topics and rising formats, and says what to post this week. Free; runs weekly, and once before launch to inform validation.

## Reads from the brain
- `brain/company.md`: voice and constraints.
- `ventures/<slug>/brain.md`: problem, who and category, from which the search phrases are built.

## Inputs
- Five to eight niche phrases built from the brain (the problem in the reader's words, the category, the who).
- Hacker News Algolia API, `search_by_date`, last seven days. Free, no key.
- YouTube Data API `search.list` with `publishedAfter` seven days back and `order=viewCount`; each call costs 100 quota units, so at most eight phrases a run. `YOUTUBE_API_KEY` from GitHub secrets. As of Oct 2026, check the limit.
- Optional: Firecrawl search (`FIRECRAWL_API_KEY`) for news pages.
- Optional: `launch/inputs/vidiq-outliers.json`, an export of vidIQ outlier and trending results from Charlie's account.
- The previous `launch/insights/trends-<date>.json`, if one exists.

## Steps
1. Build the phrases. Write them to the top of the JSON so a run can be repeated.
2. Collect from each source. A source that fails is skipped with its reason under `skipped` in `ventures/<slug>/board.json`.
3. Deduplicate by URL. Keep title, source, date and one engagement figure (points, views).
4. Score each topic out of 100: 40 for recency (fades linearly over seven days), 40 for engagement (percentile within its own source), 20 for fit. Fit is a yes or no from `foundry.util.ask_json` on whether the topic touches the problem or the reader, with a one-line reason; no reason, no points.
5. Find rising formats. Fetch durations with `videos.list` (1 unit per 50 ids). Bucket the top 25 videos by views into under 60 seconds, 1 to 10 minutes, over 10 minutes, and by title pattern (starts with a number, a question, "how to", "vs"). A bucket is rising if its share is up 10 points or more on the previous run.
6. Write the brief and the JSON. Set this job to `done` in `board.json`.

## Output
- `ventures/<slug>/launch/insights/trends.md`: Top 10 topics (table: score, topic, source, url, why it fits), Rising formats (up to three, with shares), This week (three post angles, each topic plus hook angle plus format).
- `ventures/<slug>/launch/insights/trends-<date>.json`: phrases, raw items, scores. Read by `hook-writing`, `script-writing` and Intelligence's validate report.

## The ladder
- Human-led: Charlie scrolls the niche daily and notes what is moving.
- Human-assisted: the job posts the weekly brief; Charlie picks the angles.
- Fully autonomous: the top angle goes straight to `hook-writing`. This is the default.

## The human
What stays with Charlie: deciding which trends fit the brand and are safe to comment on. Anything political, tragic or regulated is skipped by default.

## Tools
Free first. Hacker News Algolia API, YouTube Data API free quota, Firecrawl free tier, vidIQ export from Charlie's account, Gemini 2.5 Flash and Groq via `foundry.util.ask_json` (as of Oct 2026, check the limit). Google Trends has no official API, so it is not used.

## Build notes
- Not built yet. Weekly cron plus `workflow_dispatch`; stdlib plus `requests`.
- Without a model, scores use steps 3 to 5 with fit set to 0 and the brief says so.
- Test offline with a saved Algolia response and a saved YouTube response.
- GitHub implementation: `run.py` beside this file (jobkit).
