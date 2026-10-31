---
name: thumbnail-and-cover-design
title: Thumbnail and Cover Design
department: marketing
function: creation
autonomy: solo
stage: launch
builds_on: [image-generation]
breaks_into: [draft-concepts, render-variants, check-legibility, pick-winner]
replaces: "a freelance thumbnail designer, usually paid per thumbnail"
runs_on: github
status: ready
---

# Thumbnail and Cover Design

Makes three thumbnail or cover variants per post, checks they are legible at small size, and picks the one most likely to earn the click. Free.

## Reads from the brain
- `brain/company.md`: voice and constraints.
- `ventures/<slug>/brain.md`: the product and its proof. Covers never promise what the product does not do.

## Inputs
- `ventures/<slug>/launch/video/index.json` or `launch/scripts/index.json`: the posts needing covers.
- `launch/hooks.json`: `cover` and `title` hooks for each post.
- `launch/images/` and `credits.json` from `image-generation`; `launch/brand.json`.
- Optional: `launch/inputs/vidiq-thumbnails.json`, thumbnail scores and similar-thumbnail outliers exported from Charlie's vidIQ account.

## Steps
1. For each post, take its best `cover` hook. Cover text is 4 words or fewer.
2. Request one background per post through `launch/image-requests.json` (`image-generation`), plus use the product screenshot where the post shows the product.
3. Set the sizes: YouTube 1280 by 720 and under 2 MB; Shorts, Reels and TikTok covers 1080 by 1920. Keep all text inside the central 1080 by 1080 area, because profile grids crop covers.
4. Render three variants per post with ImageMagick: text position (top, centre, bottom), accent colour on the key word, one object or face only. Use `brand.json` fonts and colours.
5. Check in code, then again after shrinking the image to 160 by 90: text height at least 8 per cent of image height, text to background contrast at least 4.5 to 1, text readable (re-run the contrast on the small version), file size within the platform limit.
6. Pick: the vidIQ score if the export has one; otherwise the variant that passes every check with the highest contrast. The other two stay as `b.png` and `c.png` for a test.
7. Write the files and set this job to `done` in `ventures/<slug>/board.json`.

## Output
- `ventures/<slug>/launch/thumbnails/<post-id>/a.png`, `b.png`, `c.png`, and `chosen.png`.
- `ventures/<slug>/launch/thumbnails/index.json`: `[{post_id, platform, chosen, checks:{contrast, size, small_legible}, vidiq_score}]`. Read by `publishing`.

## The ladder
- Human-led: Charlie designs each cover in Canva's free tier.
- Human-assisted: the job renders three; Charlie picks.
- Fully autonomous: the checked winner goes to `publishing`. This is the default.

## The human
What stays with Charlie: choosing for taste, and running YouTube Studio's Test and compare on a channel that has it, using `a`, `b` and `c`.

## Tools
Free first. ImageMagick on GitHub Actions, Pexels and Unsplash free stock, Canva free tier, vidIQ thumbnail scoring through Charlie's account (as of Oct 2026, check the limit), Gemini 2.5 Flash for cover text through `foundry.util.ask_json`.

## Build notes
- Not built yet. Stdlib plus `requests`; ImageMagick installed in the workflow.
- A cover that looks clickable but misleads breaks platform rules and trust; the check list has no "shock" setting.
- Fallback with no model: the hook text shortened to four words at the head of the sentence.
- GitHub implementation: `run.py` beside this file (jobkit).
