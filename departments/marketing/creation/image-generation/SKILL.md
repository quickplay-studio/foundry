---
name: image-generation
title: Image Generation
department: marketing
function: creation
autonomy: solo
stage: launch
builds_on: []
breaks_into: [load-brand, source-image, composite-brand, log-credits]
replaces: "a stock photo subscription and a freelance designer"
runs_on: github
status: ready
---

# Image Generation

Produces brand-consistent images for posts, carousels, thumbnails and share cards, starting from a reference library and free stock. Free.

## Reads from the brain
- `brain/company.md`: voice and constraints (free tools only).
- `ventures/<slug>/brain.md`: the product, who it is for, and its proof, so images show the real thing.

## Inputs
- `ventures/<slug>/launch/brand.json`: `{colours:{bg, text, accent}, font, logo}`. If absent, create a plain default and tell Charlie.
- Reference library: `launch/references/` (product screenshots, logo, any images Charlie owns).
- Requests: `launch/image-requests.json`, `[{id, purpose, text, size, keywords}]`, written by other jobs. Sizes are pixels, for example `1080x1350`.
- Pexels (`PEXELS_API_KEY`) and Unsplash (`UNSPLASH_ACCESS_KEY`) free search. As of Oct 2026, check the limit.

## Steps
1. Read the requests. Skip ids that already have a file.
2. Source the base, in order: a screenshot or reference from the library; a free stock photo from Pexels or Unsplash searched by the request keywords; Gemini image output if the key's free tier allows it (as of Oct 2026, check the limit). No third-party logos, no recognisable real people, no images that imply an endorsement.
3. Crop to the requested size, keeping the subject inside the central 80 per cent.
4. Apply the brand with ImageMagick or ffmpeg: a colour wash from `brand.json`, the headline in the brand font and colour, the logo in a fixed corner. No new Python packages.
5. Check in code: size matches, file under 500 KB, text contrast at least 4.5 to 1 against the area behind it, text inside the margins.
6. Log credits: source, author, URL and licence for stock; the prompt and model for generated images, marked `generated: true`.
7. Write files and set this job to `done` in `ventures/<slug>/board.json`; a request with no usable source goes under `skipped` with the reason.

## Output
- `ventures/<slug>/launch/images/<id>.jpg` (or `.png` for text-heavy images).
- `ventures/<slug>/launch/images/credits.json`: `[{id, source, author, url, licence, generated, prompt}]`. Read by `thumbnail-and-cover-design`, `og-and-share-surface`, `video-production`, `carousel-production`.

## The ladder
- Human-led: Charlie picks and edits every image in Canva's free tier.
- Human-assisted: the job proposes images; Charlie replaces any that miss.
- Fully autonomous: requests turn into branded images with no review. This is the default.

## The human
What stays with Charlie: owning the brand look, adding real screenshots to the reference library, and checking that nothing generated could mislead.

## Tools
Free first. Pexels and Unsplash free APIs, Gemini image output if the free tier allows, ImageMagick and ffmpeg on GitHub Actions, Canva free tier by hand (as of Oct 2026, check the limit). Gemini 2.5 Flash through `foundry.util.ask_json` for keywords.

## Build notes
- Not built yet. Stdlib plus `requests`; ImageMagick and ffmpeg are installed in the workflow with `apt-get`.
- Fallback with no stock or model: a flat brand-colour card with the headline, which always works.
- Credits are required: Pexels asks for attribution where practical and Unsplash expects its download-tracking call.
- GitHub implementation: `run.py` beside this file (jobkit).
