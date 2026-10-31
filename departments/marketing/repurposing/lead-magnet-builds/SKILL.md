---
name: lead-magnet-builds
title: Lead-Magnet Builds
department: marketing
function: repurposing
autonomy: solo
stage: launch
builds_on: [landing-page-copy]
breaks_into: [pick-theme, write-guide, render-pdf, write-gate-page]
replaces: "a freelance writer and designer for a gated guide"
runs_on: github
status: ready
---

# Lead-Magnet Builds

Turns the content theme people ask about most into a short gated guide and the page that offers it. Free to produce; Charlie sets up the free email service.

## Reads from the brain
- `brain/company.md`: voice, and the rule that nothing regulated (finance, health, children, gambling) is written without a human and a solicitor.
- `ventures/<slug>/brain.md`: problem, who, MVP, money. The guide leads to the product at the end.

## Inputs
- `ventures/<slug>/launch/insights/audience.json`: top questions and the language bank.
- Optional: `launch/insights/performance.json` for themes that earned sign-ups.
- `launch/landing-page.md`: the voice and the product line the guide ends on.
- `launch/brand.json`: `{colours:{bg, text, accent}, font, logo}`.

## Steps
1. Pick one theme: the most-asked question in `audience.json` that the MVP helps with and that performance data does not contradict. If the theme touches a regulated area, add a line under `skipped` in `ventures/<slug>/board.json` and stop.
2. Outline a guide of 6 to 10 pages and no more than 1,500 words: the promise, 5 to 7 steps, a one-page checklist, a short last page that names the product and its price.
3. Ask `foundry.util.ask_json` for each section in turn, passing only the outline, the brain and the language bank. The guide teaches something useful without the product, and every fact comes from the brain or a source named on the page.
4. Lint in code: no dashes, no exclamation marks, no hype words, sentences 20 words or fewer, UK spelling, every number sourced.
5. Render markdown to HTML with the brand CSS, then to PDF with headless Chrome. Check page count and file size (under 2 MB).
6. Write the gate page copy: a headline naming the result, three bullets, one email field, a plain consent line (what they will get, how often, how to leave), and the thank-you text with the download link.
7. Write the files and set this job to `done` in `board.json`.

## Output
- `ventures/<slug>/launch/lead-magnet/guide.md` and `guide.pdf`.
- `ventures/<slug>/launch/lead-magnet/gate-page.md` with sections Headline, Bullets, Form, Consent, Thank-you.
- `ventures/<slug>/sell/ctas.json`: `[{keyword, asset, dm_text, platforms, gate_page}]`, the comment keywords that unlock each magnet, read by Deals `comment-cta-fulfilment`.
- `ventures/<slug>/launch/lead-magnet/index.json`: `{theme, pages, words, pdf, sources:[]}`. Read by `newsletter-and-broadcast` and `seo-and-geo`.

## The ladder
- Human-led: Charlie writes and designs the guide.
- Human-assisted: the job drafts and renders; Charlie reads it end to end before it goes behind the form.
- Fully autonomous: not used for the first guide. Later guides on the same theme can run unattended.

## The human
What stays with Charlie: reading the guide, choosing and setting up one free email service (for example the free tiers of MailerLite or Buttondown; as of Oct 2026, check the limit), placing the form, and the consent wording. Legal's `data-protection` and `privacy-policy` apply; this is not legal advice.

## Tools
Free first. Headless Chrome, Gemini 2.5 Flash and Groq Llama 3.3 70B through `foundry.util.ask_json`, Canva free tier for a cover (as of Oct 2026, check the limit). No account is created by the job.

## Build notes
- Not built yet. Stdlib plus `requests`; the lint and the PDF check are tested functions.
- Fallback with no model: outline plus brain facts as a checklist, marked `draft: template`.
- Never email the list from here; that is `newsletter-and-broadcast`.
