---
name: performance-mining
title: Performance Mining
department: marketing
function: insights
autonomy: solo
stage: launch
builds_on: []
breaks_into: [pull-metrics, rank-posts, find-patterns, pick-redos]
replaces: "a paid social analytics tool or a part-time analyst"
runs_on: github
status: ready
---

# Performance Mining

Ranks our own posts by what worked and lists what to redo. Costs nothing; runs weekly once posts are live.

## Reads from the brain
- `brain/company.md`: voice and the free-tools rule.
- `ventures/<slug>/brain.md`: who the venture is for and what the MVP does, so "worked" means sign-ups first and views second.

## Inputs
- `ventures/<slug>/launch/publish-log.json`: one row per post, `{post_id, platform, url, published, hook_id, format}`, written by `publishing`.
- Public stats from the YouTube Data API (`videos.list`, statistics part) and the Meta Graph API (insights for Charlie's own Instagram and Facebook accounts). Keys `YOUTUBE_API_KEY` and `META_ACCESS_TOKEN` come from GitHub secrets only. As of Oct 2026, check the limit.
- Optional: `launch/inputs/vidiq.json`, an export from Charlie's vidIQ account (video stats, outlier scores).
- Optional: `launch/inputs/signups.csv`, columns `date,utm_content`, exported from the page's analytics.

## Steps
1. Read `publish-log.json`. Drop posts under 48 hours old. If none remain, add a line under `skipped` in `ventures/<slug>/board.json` ("no posts old enough") and stop.
2. Fetch metrics per post: views, likes, comments, shares, saves, where the API returns them. Save raw responses to `launch/inputs/metrics-<date>.json`. An API that fails is skipped with its reason; the others still run.
3. Compute per post: views divided by the median views for that platform and format; engagement rate = (likes + comments + shares + saves) / views; sign-ups where `utm_content` equals `post_id`.
4. Rank by sign-ups, then views against median, then engagement rate. Under ten posts: rank anyway and say the sample is small.
5. Group by hook pattern (from `hook_id` in `launch/hooks.json`), format, length band and posting hour. One line per group: count, median views, median sign-ups.
6. Call `foundry.util.ask_json` with the table only. Ask for `{"redo": [{"post_id", "change", "why"}], "drop": [{"post_id", "why"}]}`: up to five redo from the top three posts, up to three drop from the bottom three. If every model fails, write the groups without this section.
7. Write the report, then set this job to `done` in `board.json` with `output` and `updated`.

## Output
- `ventures/<slug>/launch/insights/performance.md`: Summary (best post, worst post, one pattern, three lines), Ranked posts (table: rank, platform, url, views, vs median, engagement, sign-ups), Patterns, Redo, Drop.
- `ventures/<slug>/launch/insights/performance.json`: the same data, read by `hook-writing` and `publishing`. Charlie reads the markdown.

## The ladder
- Human-led: Charlie opens each platform's analytics and keeps a spreadsheet.
- Human-assisted: the job ranks and proposes redos; Charlie picks which to make.
- Fully autonomous: weekly run feeds winning patterns to `hook-writing` with no review. This is the default.

## The human
What stays with Charlie: deciding what counts as a win for this venture, adding the API secrets once, and choosing which redo ideas get made.

## Tools
Free first. YouTube Data API and Meta Graph API on free quotas; vidIQ export from Charlie's account; Gemini 2.5 Flash, then Flash-Lite, then Groq Llama 3.3 70B through `foundry.util.ask_json` (as of Oct 2026, check the limit). No Claude.

## Build notes
- Not built yet. One script on a weekly cron plus `workflow_dispatch`; Python 3.12 stdlib plus `requests`.
- Steps 1 to 5 are arithmetic, so the job is useful even when every model is down.
- Test offline with fixture API responses in `tests/`. Never read raw comments here; that is `audience-analysis`.
- GitHub implementation: `run.py` beside this file (jobkit).
