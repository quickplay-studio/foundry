---
name: carousel-production
title: Carousel Production
department: marketing
function: creation
autonomy: solo
stage: launch
builds_on: [hook-writing]
breaks_into: [outline-slides, render-slides, check-contrast, export-pack]
replaces: "a freelance designer or a paid design subscription, per carousel"
runs_on: github
status: ready
---

# Carousel Production

Designs and exports branded carousels (Instagram, LinkedIn, Facebook) from the best hooks. Free: HTML templates rendered to images on GitHub Actions.

## Reads from the brain
- `brain/company.md`: voice and constraints.
- `ventures/<slug>/brain.md`: problem, MVP, price, proof. Slides claim only what is here.

## Inputs
- `ventures/<slug>/launch/hooks.json`: `cover` hooks with scores.
- `launch/insights/audience.json` for the points each carousel teaches.
- `launch/brand.json`: `{colours:{bg, text, accent}, font, logo}`. If absent, create it with dark text on white, one accent colour and a system font, and tell Charlie in the pull request.
- Optional: product screenshots in `launch/references/`.

## Steps
1. Pick up to three `cover` hooks that are not `rejected`, one per theme.
2. Outline 6 to 8 slides: cover (the hook), the problem, three points, proof, call to action. Each slide has a headline of 8 words or fewer and body of 25 words or fewer.
3. Ask `foundry.util.ask_json` for `{slides:[{headline, body, alt}]}` per carousel. Every number or claim must match `brain.md`.
4. Fill an HTML template (one file, CSS variables from `brand.json`, 1080 by 1350 pixels). Keep a 80 pixel margin so nothing is cropped in feeds.
5. Render each slide to PNG with headless Chrome on the runner (installed on GitHub's Ubuntu image; if not, install Chromium with `apt-get`). Merge the PNGs into one PDF for LinkedIn.
6. Check in code: text to background contrast at least 4.5 to 1, font size of at least 40 pixels for headlines, no dashes, no exclamation marks, each PNG under 400 KB.
7. Write the pack and set this job to `done` in `ventures/<slug>/board.json`. Binary files too big for git go to a workflow artifact; `index.json` records where they are.

## Output
- `ventures/<slug>/launch/carousels/<carousel-id>/slide-01.png` and onward, plus `carousel.pdf`.
- `ventures/<slug>/launch/carousels/<carousel-id>/copy.md`: headline, body and alt text per slide.
- `ventures/<slug>/launch/carousels/index.json`: `[{carousel_id, hook_id, slides, pdf, theme}]`. Read by `cross-platform-adaptation` and `publishing`.

## The ladder
- Human-led: Charlie designs each carousel in Canva.
- Human-assisted: the job renders; Charlie opens the Canva free tier only to polish.
- Fully autonomous: slides render and go to `publishing` for approval. This is the default.

## The human
What stays with Charlie: approving the brand look once, and approving each carousel in `publishing`.

## Tools
Free first. Headless Chrome and ImageMagick on GitHub Actions, Pexels and Unsplash free stock for backgrounds (as of Oct 2026, check the limit), Canva free tier by hand, Gemini 2.5 Flash and Groq through `foundry.util.ask_json`.

## Build notes
- Not built yet. One template, one render function; no new Python packages (shell out to Chrome).
- Fallback with no model: slides from the hook, the `brain.md` problem line, MVP bullets and proof line.
- Test the contrast and size checks with fixture PNGs.
- GitHub implementation: `run.py` beside this file (jobkit).
