---
name: seo-and-geo
title: SEO and GEO
department: marketing
function: distribution
autonomy: solo
stage: launch
builds_on: [landing-page-copy]
breaks_into: [audit-page, write-metadata, add-structured-data, write-site-files]
replaces: "an SEO freelancer or a paid site audit tool"
runs_on: github
status: ready
---

# SEO and GEO

Makes the site legible to search engines and to language models: metadata, structured data, a sitemap, crawler rules and a plain answer block. The job writes a patch pack; Charlie or the Build session applies it to the site repo. Free.

## Reads from the brain
- `brain/company.md`: voice and constraints.
- `ventures/<slug>/brain.md`: what the product is, who it is for, price, proof. Structured data states only these facts.

## Inputs
- `ventures/<slug>/launch/landing-page.md` (`landing-page-copy`): the copy and the FAQ.
- `launch/channels.json`: `site` is the live URL. If it is empty, skip the live audit and write the pack from the copy.
- `launch/insights/audience.json` for the language bank and questions.
- Optional: `launch/inputs/vidiq-keywords.json`, keyword research exported from Charlie's vidIQ account.
- PageSpeed Insights API for speed (free; as of Oct 2026, check the limit).

## Steps
1. Audit the live page (our own site) over plain HTTP. Check: one H1; title 60 characters or fewer; meta description 140 to 160; heading order; alt text on images; canonical link; `lang="en-GB"`; viewport tag; HTML under 100 KB. Run PageSpeed Insights for mobile and note the scores.
2. Choose keywords: one primary phrase and three secondary from the language bank and any vidIQ export. Use words people type, not our jargon.
3. Write metadata with `foundry.util.ask_json`: title, meta description, H1 suggestion, each including the primary phrase once and the price or what it does.
4. Write JSON-LD: `SoftwareApplication` (name, description, `offers` with price in GBP) and `FAQPage` from the FAQ section. This helps machines read the page; it is not a promise of rich results.
5. Write `sitemap.xml`, `robots.txt` (allow all, with the sitemap line; AI crawlers allowed by default and noted for Charlie to change) and `llms.txt` (a short markdown summary and links to the key pages; a proposed convention with no guaranteed effect).
6. For answer engines, write a visible answer block of 60 words or fewer: what it is, who it is for, the price, how it works. Plain HTML, near the top, with dates where facts can change.
7. Write `patch.md`: for each file or snippet, the exact place in the site repo `quickplay-studio/<slug>`. Record that Charlie must submit the sitemap in Search Console himself.
8. Set this job to `done` in `ventures/<slug>/board.json`; a failed fetch goes under `skipped`.

## Output
- `ventures/<slug>/launch/seo/report.md`: audit table (check, pass or fail, fix).
- `ventures/<slug>/launch/seo/metadata.json`, `jsonld.json`, `sitemap.xml`, `robots.txt`, `llms.txt`.
- `ventures/<slug>/launch/seo/patch.md`: where each piece goes. Read by `og-and-share-surface` and the Build session.

## The ladder
- Human-led: Charlie edits the site's head and files himself.
- Human-assisted: the job writes the pack; Charlie or a Build session applies it.
- Fully autonomous: the job opens a pull request on the site repo; this needs Charlie to give the workflow a token for that repo, so it is off by default.

## The human
What stays with Charlie: applying the patch, verifying the site in Search Console, and deciding which crawlers to allow.

## Tools
Free first. PageSpeed Insights API, Google Search Console (Charlie's login), vidIQ keyword research on his account, Gemini 2.5 Flash and Groq through `foundry.util.ask_json` (as of Oct 2026, check the limit). Firecrawl free tier to read competitor titles.

## Build notes
- Not built yet. Stdlib plus `requests`; the HTML audit uses `html.parser`. Each check is a small tested function.
- Fallback with no model: title from the H1 and price line, description from the first two lines of the hero.
- Do not stuff keywords; one primary phrase once per field.
