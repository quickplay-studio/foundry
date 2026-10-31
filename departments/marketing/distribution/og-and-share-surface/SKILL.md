---
name: og-and-share-surface
title: OG and Share Surface
department: marketing
function: distribution
autonomy: solo
stage: launch
builds_on: [image-generation]
breaks_into: [list-pages, render-og-images, write-meta-tags, verify-live]
replaces: "a freelance designer making share images or a paid OG image service"
runs_on: github
status: ready
---

# OG and Share Surface

Gives every page a share-ready image and the open-graph and Twitter tags to go with it, so a link looks right when pasted into a chat or a feed. Free.

## Reads from the brain
- `brain/company.md`: voice and constraints.
- `ventures/<slug>/brain.md`: the product name and one-line description.

## Inputs
- Page list: `launch/seo/metadata.json` (`seo-and-geo`) if present, else the home page and each page named in `launch/channels.json` under `pages`.
- Title and description per page from the metadata file or `launch/landing-page.md`.
- `launch/brand.json`: `{colours:{bg, text, accent}, font, logo}`. Product screenshot or backgrounds from `launch/images/`.
- `launch/channels.json` `site` for absolute URLs.

## Steps
1. List the pages. Give each a slug (`home`, `pricing`, `guide`).
2. For each page choose a title of 60 characters or fewer and a one-line subtitle of 90 or fewer.
3. Request a background from `image-generation` through `launch/image-requests.json` where none exists; the product screenshot is preferred.
4. Render a 1200 by 630 PNG from an HTML template with headless Chrome: brand colour, title, subtitle, logo, screenshot on the right. Keep a 60 pixel margin so cropped previews still read. Keep each file under 300 KB.
5. Check in code: dimensions, file size, text contrast at least 4.5 to 1, text inside margins.
6. Write the tag block per page: `og:title`, `og:description`, `og:image` (absolute URL), `og:image:width`, `og:image:height`, `og:image:alt`, `og:url`, `og:type`, `og:site_name`, `og:locale` set to `en_GB`, `twitter:card` set to `summary_large_image`.
7. Once the site is live, verify with `requests`: the image URL returns 200 with an `image/png` content type, and the page HTML contains the tags. Failures go under `skipped` in `ventures/<slug>/board.json`; a site not yet live is not a failure, it is a retry next run.
8. Set this job to `done` in `board.json`.

## Output
- `ventures/<slug>/launch/og/<page-slug>.png`.
- `ventures/<slug>/launch/og/tags.html`: the tag block for each page under a comment naming the page. Applied by Charlie or the Build session alongside the SEO patch.
- `ventures/<slug>/launch/og/index.json`: `[{page, image, title, description, checks, live_ok}]`.

## The ladder
- Human-led: Charlie makes each share image in Canva's free tier.
- Human-assisted: the job renders; Charlie checks previews in Facebook's Sharing Debugger and LinkedIn's Post Inspector.
- Fully autonomous: a new page in the list gets an image and tags on the next run. This is the default.

## The human
What stays with Charlie: placing the tags on the site, and checking the previews on the platforms, which need his logins.

## Tools
Free first. Headless Chrome and ImageMagick on GitHub Actions, Pexels and Unsplash free stock (as of Oct 2026, check the limit), Canva free tier by hand, Gemini 2.5 Flash through `foundry.util.ask_json` for subtitle trimming.

## Build notes
- Not built yet. Stdlib plus `requests`; one HTML template with slots.
- Platform preview caches are sticky: if an image changes, change its file name rather than overwrite it.
- Fallback with no model: title and the first line of the description.
- GitHub implementation: `run.py` beside this file (jobkit).
