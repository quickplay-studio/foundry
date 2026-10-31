---
name: cross-platform-adaptation
title: Cross-Platform Adaptation
department: marketing
function: repurposing
autonomy: solo
stage: launch
builds_on: [caption-writing]
breaks_into: [read-master, map-formats, rewrite-natively, check-limits]
replaces: "a social media manager reformatting each post by hand"
runs_on: github
status: ready
---

# Cross-Platform Adaptation

Takes one finished idea (a script with its media and caption) and produces a native version for every platform in use, so nothing is a crude repost. Free.

## Reads from the brain
- `brain/company.md`: voice and constraints.
- `ventures/<slug>/brain.md`: the product and proof. Adapted versions never add claims.

## Inputs
- A master: `ventures/<slug>/launch/scripts/<post-id>.json` with its `captions.json` rows. Media from `launch/video/index.json`, `launch/carousels/index.json`, `launch/thumbnails/index.json`.
- `launch/channels.json`: `platforms` and per-platform `handle`.
- Platform limits kept in `caption-writing`'s table; as of Oct 2026, check the limit.

## Steps
1. List masters that have no adapted file yet.
2. Map each master to formats. Vertical video (9:16) goes to TikTok, Instagram Reels, YouTube Shorts and Facebook Reels. A carousel goes to an Instagram carousel and a LinkedIn PDF document. A script's key point also becomes a text post for X (a thread of up to six posts, 280 characters each) and LinkedIn.
3. For each variant, change what the platform needs, not just the size: the first line (YouTube title up to 60 characters; Reels and TikTok spoken hook), the call to action ("Link in bio" where links are not clickable), tone (LinkedIn slightly more explanatory; the voice rules still hold), tags and mentions.
4. Ask `foundry.util.ask_json` for `{variants:[{platform, format, text}]}` for the text posts and thread. Video and image variants reuse the master's media; never re-upload a file that carries another app's watermark, always use the original render.
5. Reuse the UTM link from `captions.json` with `utm_source` set to the target platform.
6. Check in code: length against each limit, a link present only where clickable, no dashes, no exclamation marks, no claim missing from the master.
7. Skip platforms where Charlie has no `handle`. Write the file and set this job to `done` in `ventures/<slug>/board.json`.

## Output
- `ventures/<slug>/launch/adapted/<post-id>.json`: `{post_id, variants:[{platform, format, text, media, link, char_count, limit}]}`. `media` is a path into `launch/video`, `launch/carousels` or `launch/thumbnails`. Read by `publishing`.
- `ventures/<slug>/launch/adapted/index.md`: one table of every variant for Charlie to scan.

## The ladder
- Human-led: Charlie rewrites each post for each app.
- Human-assisted: the job produces variants; Charlie edits the ones that matter in the publishing pull request.
- Fully autonomous: variants flow to `publishing`, which still needs approval. This is the default.

## The human
What stays with Charlie: which platforms are worth the effort for this venture, and the handles he has set up.

## Tools
Free first. Gemini 2.5 Flash and Groq Llama 3.3 70B through `foundry.util.ask_json` (as of Oct 2026, check the limit). ffmpeg only if a crop is missing, on GitHub Actions.

## Build notes
- Not built yet. Stdlib plus `requests`. Format mapping is a table in code; the limit check is a tested function.
- Fallback with no model: take the master caption, trim at a sentence end to fit, add the right call to action.
- Add a platform by adding one row to the table.
