---
name: landing-page-copy
title: Landing Page Copy
department: marketing
function: creation
autonomy: solo
stage: launch
builds_on: [audience-analysis, pricing-research]
breaks_into: [pick-promise, draft-sections, check-claims, write-copy-file]
replaces: "a freelance conversion copywriter, roughly a few hundred pounds a page"
runs_on: github
status: ready
---

# Landing Page Copy

Writes the copy for the whole landing page as one markdown file: hero, proof, offer, FAQ and CTA. The page is measured on one metric: sign-ups. Free.

## Reads from the brain
- `brain/company.md`: voice. Say the price and what it does in the first two lines; proof over adjectives; no hype, no exclamation marks, no dashes.
- `ventures/<slug>/brain.md`: problem, who, gap, MVP, money, proof. Every claim on the page comes from here.

## Inputs
- `ventures/<slug>/launch/insights/audience.json` (`audience-analysis`): questions, objections, language bank.
- The price from Intelligence's `pricing-research` (look in `ventures/<slug>/validate/`); if it names no price, the `money` line in `brain.md`. If neither states a price, add a line under `skipped` in `ventures/<slug>/board.json` and stop.
- Optional: `launch/insights/competitors.md` for what competitors promise.

## Steps
1. Pick one reader and one promise: the biggest question in `audience.json` that the MVP answers. Write both in one line each at the top of your working notes.
2. Ask `foundry.util.ask_json` for each section as JSON, one call per section, passing only the brain, the price, the promise and the language bank.
3. Hero: a headline of 10 words or fewer; a subhead of two lines, the first stating what the product does and the second the price; one button label; one risk line under the button only if true (for example "No card needed", when the signup has none).
4. Proof: only what the brain supports: the demand evidence in `proof` with its source, the numbers from `audience.json`, and what the MVP does today. No testimonials, user counts, logos or press that do not exist.
5. Offer: what the visitor gets (three to five lines from the MVP), the price and billing terms, what is not included.
6. FAQ: five to seven questions from `audience.json`, always covering price, cancellation, and what happens to their data. Answers use only brain facts; no fact, no question.
7. CTA: one closing line and the same button verb as the hero. One action on the whole page: sign up.
8. Lint in code: sentences 20 words or fewer, no dashes, no exclamation marks, no hype words, UK spelling. Build a claims table: each number or claim mapped to its source line in the brain or `audience.json`. Remove any copy with no source.
9. Write the files and set this job to `done` in `board.json` with `output` and `updated`.

## Output
- `ventures/<slug>/launch/landing-page.md`:
```
# Landing page copy: <venture title>
Measured on: sign-ups (completed sign-up form per 100 visitors). Nothing else.
## Hero
## Proof
## Offer
## FAQ
## CTA
```
  Each section holds copy only, ready to paste into the page. Charlie reads it; `ad-creative`, `seo-and-geo` and `lead-magnet-builds` build on it.
- `ventures/<slug>/launch/landing-page.claims.json`: `[{claim, source}]`, so every statement can be traced.

## The ladder
- Human-led: Charlie writes the page.
- Human-assisted: the job drafts; Charlie edits the hero and the price line.
- Fully autonomous: copy is written and handed to the Build session. This is the default; Charlie still reads before it goes live.

## The human
What stays with Charlie: confirming the price, approving any claim about results, installing sign-up tracking, and putting the copy on the page.

## Tools
Free first. Gemini 2.5 Flash and Groq Llama 3.3 70B through `foundry.util.ask_json` (as of Oct 2026, check the limit). Firecrawl free tier to read a competitor's page. A hard rewrite can be done in a Claude Code session with Sonnet.

## Build notes
- Not built yet. Stdlib plus `requests`; the lint and the claims table are tested functions.
- Do not A/B test with fewer than about 100 sign-ups per variant; ship one version and change one thing at a time.
- Fallback with no model: assemble sections from the brain and mark the file `draft: template`.
