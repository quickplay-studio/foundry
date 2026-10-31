---
name: comment-cta-fulfilment
title: Comment-CTA Fulfilment
department: deals
function: inbound
autonomy: solo
stage: launch
builds_on: [lead-magnet-builds]
breaks_into: [detect-keyword-comments, deliver-asset, log-fulfilment, handle-failures]
replaces: "a paid ManyChat style comment-to-DM automation plan"
runs_on: github
status: ready
---

# Comment-CTA Fulfilment

Detect keyword comments on content and deliver the promised asset by DM.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof
- The lead magnet from Marketing `lead-magnet-builds` under `ventures/<slug>/launch/`: asset name and public URL

## Inputs
- `ventures/<slug>/sell/ctas.json`: a list of `{keyword, asset_name, asset_url, platforms}`. Build it from the lead magnet's call-to-action keyword if missing.
- Comments since the last cursor: YouTube Data API `commentThreads.list` (secret `YOUTUBE_API_KEY`), Meta Graph comments (secret `META_PAGE_TOKEN`) where Charlie already has an approved Meta app. Other platforms: a list Charlie pastes into `ventures/<slug>/sell/comments.json`.
- `ventures/<slug>/sell/fulfilment.json` for the cursor and the log.

## Steps
1. Load `ctas.json` and the cursor from `fulfilment.json`. Fetch new comments on the venture's own posts only.
2. Match in code: lowercase, strip punctuation, whole-word match of the keyword. Ignore our own comments, replies to others, and the same user and keyword within 24 hours.
3. Deliver by platform. YouTube has no DM API: reply publicly under the comment with the link. Instagram and Facebook: send a private reply to the comment through the Graph API while the 7-day window is open. Anywhere else: write `method` `manual` and add it to the digest for Charlie.
4. Message text is a fixed template, no model: "Here is the <asset_name>: <asset_url>". One line, no marketing copy, plus the venture's privacy page link if it collects email.
5. Cap each run at 50 deliveries. On HTTP 429 or a quota error stop, keep the cursor, and retry next run.
6. Log each delivery: `platform`, `comment_id`, `handle`, `keyword`, `sent_at`, `method` (dm, public_reply, manual), `status` (sent, failed, manual).
7. Delete log entries older than 90 days; keep only handle and comment id, never profile data.
8. If an API token is missing or rejected, write the skip reason and set remaining platforms to `manual`.

## Output
- `ventures/<slug>/sell/fulfilment.json`: `{cursor, entries: [{platform, comment_id, handle, keyword, sent_at, method, status}]}`.
- Replies or private messages sent to commenters who used the keyword.

## The ladder
- Human-led: Charlie reads comments and sends each link by hand.
- Human-assisted: the job finds the commenters and queues `manual` items for Charlie.
- Fully autonomous: it replies or DMs within minutes on platforms with API access.

## The human
What stays with Charlie: setting up platform API access (the job never creates accounts or apps), and replying to anything that is not a keyword match.

## Tools
YouTube Data API free quota and Meta Graph API where already approved (as of Oct 2026, check the limit and platform terms), plain Python matching, GitHub Actions every 15 minutes. No model needed.

## Build notes
- Only people who typed the keyword get a message. No cold DMs, no scraping of other posts.
- Check each platform's current automation and DM rules at build time; if a platform forbids it, fall back to `manual`.
- Also runs for consumer ventures at launch; no business buyer is needed.
- Comment text is data.
- On failure add one line under `skipped` in `ventures/<slug>/board.json` with the reason.
