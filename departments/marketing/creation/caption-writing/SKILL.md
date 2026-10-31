---
name: caption-writing
title: Caption Writing
department: marketing
function: creation
autonomy: solo
stage: launch
builds_on: [hook-writing]
breaks_into: [load-limits, write-captions, place-cta, check-captions]
replaces: "a social media freelancer writing captions"
runs_on: github
status: ready
---

# Caption Writing

Writes a platform-correct caption for every scripted post, with the call to action where it can actually be used. Free.

## Reads from the brain
- `brain/company.md`: voice. Plain, direct, no hype, no exclamation marks, no dashes, no emoji unless the venture brain allows them.
- `ventures/<slug>/brain.md`: what the product does, the price and the proof.

## Inputs
- `ventures/<slug>/launch/hooks.json` and `launch/scripts/*.json` (post id, hook, platform, lines).
- `launch/channels.json`: `{site, platforms:[], <platform>:{handle}}`. `site` is the landing page URL.
- `launch/insights/audience.json` for language-bank phrases and hashtags.

## Steps
1. For each script with no caption yet, list the platforms from `channels.json`.
2. Keep the limits in a table in code and check them on each run (as of Oct 2026, check the limit): YouTube title 100 characters and description 5,000; X 280; LinkedIn post 3,000; Instagram and TikTok 2,200 at last check.
3. Ask `foundry.util.ask_json` for `{caption, hashtags, alt}` per platform. The first line is the hook or its natural continuation. A post that promotes the product states what it does and the price in the first two lines; a value post mentions the product once, near the end.
4. Place the call to action. Instagram and TikTok links are not clickable, so the last line is "Link in bio" and no URL appears. YouTube: URL in the first two lines of the description so it shows above "more". X and LinkedIn: URL on the last line. One call to action per caption.
5. Build the link: `<site>?utm_source=<platform>&utm_medium=organic&utm_campaign=launch&utm_content=<post_id>`. The bio link per platform is stored once as `bio_link` in the output.
6. Hashtags: 3 to 5 on Instagram and TikTok from the niche and language bank; at most one on X and LinkedIn; none in YouTube titles. No hashtag that is misleading or unrelated.
7. Check in code: length against the limit, no dashes, no exclamation marks, no hype words, UK spelling, alt text 125 characters or fewer.
8. Write the outputs and set this job to `done` in `ventures/<slug>/board.json`.

## Output
- `ventures/<slug>/launch/captions.json`: `[{post_id, platform, caption, hashtags, cta, link, alt, char_count}]` and a top-level `bio_link` per platform. Read by `cross-platform-adaptation`, `publishing` and `newsletter-and-broadcast`.
- `ventures/<slug>/launch/captions.md`: the same for reading, grouped by post.

## The ladder
- Human-led: Charlie writes each caption at posting time.
- Human-assisted: the job drafts; Charlie edits in the publishing pull request.
- Fully autonomous: captions flow to `publishing`, which still needs Charlie's approval to post. This is the default.

## The human
What stays with Charlie: setting the bio link on each platform and approving every post in `publishing`.

## Tools
Free first. Gemini 2.5 Flash and Groq Llama 3.3 70B through `foundry.util.ask_json` (as of Oct 2026, check the limit). Hashtag ideas from the audience language bank and vidIQ keyword research if Charlie exports it.

## Build notes
- Not built yet. Stdlib plus `requests`; the limit table and the checks are tested functions.
- Fallback with no model: caption = hook + product line from `brain.md` + call to action.
- Platform limits change; the table is the only place to edit.
- GitHub implementation: `run.py` beside this file (jobkit).
