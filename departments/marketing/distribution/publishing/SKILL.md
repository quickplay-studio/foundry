---
name: publishing
title: Publishing
department: marketing
function: distribution
autonomy: assisted
stage: launch
builds_on: [cross-platform-adaptation]
breaks_into: [build-queue, get-approval, post-due, log-results]
replaces: "a social media manager or a paid scheduling tool"
runs_on: github
status: ready
---

# Publishing

Builds the posting schedule, waits for Charlie's approval, then posts due items through each platform's API or hands them over for manual posting. Ten organic posts are scheduled for launch. Free.

## Reads from the brain
- `brain/company.md`: voice and constraints; never post unapproved or unsupported claims.
- `ventures/<slug>/brain.md`: the product and the launch date in `plan.md`.

## Inputs
- `ventures/<slug>/launch/adapted/*.json`: variants with text, media and link.
- `launch/thumbnails/index.json` for covers.
- `launch/channels.json`: `{site, platforms:[], <platform>:{handle, method}}` where `method` is `api`, `buffer` or `manual`.
- Secrets in GitHub only, created by Charlie: `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN` (uploads need OAuth, not a key) and `META_ACCESS_TOKEN`. As of Oct 2026, check the limit and each API's review rules.
- `launch/insights/performance.json` for best posting hours, if present.

## Steps
1. Build `launch/queue.json`, `[{post_id, platform, due, approved:false, status:"queued"}]`. Spread posts: at least four hours apart per platform, at most two a day each, default 12:00 and 18:30 UK time, shifted to the best hours in `performance.json` once it exists. Plan ten organic posts across the first two weeks.
2. Open a draft pull request containing `queue.json` and a readable `queue.md`. Set the board status to `review`. Nothing posts until Charlie sets `approved:true` on a row (or merges the pull request with all rows approved).
3. An hourly workflow picks rows that are approved and due. Never post a row with a `[needs proof]` flag upstream, or one that is not approved.
4. Post by `method`. `api`: YouTube Data API `videos.insert` (uploads cost 1,600 quota units of a daily 10,000; uploads from an unaudited API project may be forced private); Meta Graph API container then `media_publish` for Instagram professional accounts and Facebook pages. `buffer`: add to Charlie's Buffer free-tier queue (free plan allows three channels and a small queue; check the limit, and whether API access is open). `manual`: leave a checklist item in the pull request with text, media path and time.
5. TikTok's posting API restricts unaudited apps to private posts, so TikTok is `buffer` or `manual` unless Charlie has been approved.
6. On failure retry twice, ten minutes apart, then mark `failed` with the reason and carry on. A failure never blocks other rows.
7. Append to `launch/publish-log.json`, `{post_id, platform, url, published, hook_id, format, status}`, which `performance-mining` reads. Set this job to `done` in `ventures/<slug>/board.json` when every row is posted, failed or manual.

## Output
- `ventures/<slug>/launch/queue.json` and `queue.md` (the schedule), `ventures/<slug>/launch/publish-log.json` (what went out, read by `performance-mining`). Charlie sees the pull request and the log.

## The ladder
- Human-led: Charlie posts each item by hand from the checklist.
- Human-assisted: the job queues and posts; Charlie approves every row. This is the default.
- Fully autonomous: not enabled. Every post needs Charlie's approval.

## The human
What stays with Charlie: creating each platform account and handle, adding tokens as secrets, approving rows, and any post that needs a login or a platform audit.

## Tools
Free first. YouTube Data API and Meta Graph API on free quotas, Buffer free tier, GitHub Actions cron (as of Oct 2026, check the limit). Gemini 2.5 Flash through `foundry.util.ask_json` only for the readable summary.

## Build notes
- Not built yet. Stdlib plus `requests`; API clients are thin and tested with mocked HTTP.
- The first run is a dry run that writes `queue.md` and posts nothing.
- Secret names beyond Foundry's default set are added by Charlie; none go in files.
