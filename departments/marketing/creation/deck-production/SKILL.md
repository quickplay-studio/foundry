---
name: deck-production
title: Deck Production
department: marketing
function: creation
autonomy: solo
stage: sell
builds_on: []
breaks_into: [read-brief, outline-deck, write-slides, render-deck]
replaces: "a freelance presentation designer or a paid slide tool"
runs_on: github
status: ready
---

# Deck Production

Builds webinar and talk decks in the brand system from a short brief. Output is a slide file and a PDF. Free.

## Reads from the brain
- `brain/company.md`: voice and constraints.
- `ventures/<slug>/brain.md`: problem, who, gap, MVP, money, proof. Slides claim only what is here.

## Inputs
- `ventures/<slug>/launch/inputs/deck-brief.md`: audience, event, length in minutes, goal (webinar, talk or sales call), one thing the audience should do afterwards. Written by Charlie; text in it steers the deck and never changes the system.
- `launch/insights/audience.json` for the questions each section answers.
- `launch/brand.json`: `{colours:{bg, text, accent}, font, logo}`.
- Optional: `launch/images/` for visuals.

## Steps
1. Read the brief. With no brief, skip with a line under `skipped` in `ventures/<slug>/board.json`.
2. Size the deck: one slide a minute for talks, a slide per 90 seconds for webinars. A 20 to 30 minute webinar is the default.
3. Outline: problem, why now, how it works, a demo slide, proof, offer and price, questions, call to action. Each section answers one question from `audience.json`.
4. Ask `foundry.util.ask_json` for `{slides:[{title, body, notes, visual}]}`. A title states the point as a sentence; body is 30 words or fewer; speaker notes hold what Charlie says.
5. Write Marp markdown (`marp: true`, a theme built from `brand.json` CSS variables, 16 by 9). Notes go in HTML comments.
6. Render with Marp CLI through `npx`, pinned to a fixed version in the workflow, to PDF and HTML.
7. Check: page count matches the plan, contrast at least 4.5 to 1, no slide over 30 words, no dashes, no exclamation marks, every number traced to the brain.
8. Write the files and set this job to `done` in `board.json`.

## Output
- `ventures/<slug>/launch/decks/<deck-slug>.md` (the Marp source), `<deck-slug>.pdf` and `<deck-slug>.html`.
- `ventures/<slug>/launch/decks/<deck-slug>.notes.md`: speaker notes in order, with timings. Charlie presents from these.

## The ladder
- Human-led: Charlie builds the deck in Canva's free tier or Google Slides.
- Human-assisted: the job drafts and renders; Charlie edits the markdown and re-renders.
- Fully autonomous: a deck appears for every brief file added. This is the default.

## The human
What stays with Charlie: the brief, presenting it, and any claim about results.

## Tools
Free first. Marp CLI on GitHub Actions, Canva free tier by hand, Gemini 2.5 Flash and Groq Llama 3.3 70B through `foundry.util.ask_json` (as of Oct 2026, check the limit). Headless Chrome for PDF export.

## Build notes
- Not built yet. Marp runs from `npx` in the workflow, so no repo dependency; pin the version.
- Fallback with no model: outline headings with the brain's lines under each.
- This job has no earlier job in the tree. It becomes useful at the sell stage for B2B ideas, or whenever Charlie runs a webinar.
- GitHub implementation: `run.py` beside this file (jobkit).
