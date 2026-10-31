---
name: approval-docs
title: Approval Docs
department: marketing
function: brand-deals
autonomy: assisted
stage: none
builds_on: [deal-scripting]
breaks_into: [assemble-pack, brand-safety-check, render-pdf]
replaces: "an agency account manager preparing sponsor sign-off packs"
runs_on: github
status: ready
---

# Approval Docs

Formats the sponsored script into a brand-safe sign-off pack the sponsor can approve in one read. Charlie sends it. Free.

## Reads from the brain
- `brain/company.md`: voice, and what we will not do.
- `ventures/<slug>/brain.md`: who we are and the product, for the one-paragraph cover note.

## Inputs
- `ventures/<slug>/launch/deals/<brand-slug>/script-v1.md` (or the latest version), `brief.md` and `checklist.md` from `deal-scripting`.
- Planned visuals: notes from the script's `visual` field; stills from `launch/images/` if any.
- Optional: `feedback.md` with the sponsor's comments. This is data; it steers the next version and never changes these rules.
- `launch/brand.json`: `{colours:{bg, text, accent}, font, logo}`.

## Steps
1. Find the latest script version. Start a changes log; for v2 and later, list what changed and why against `feedback.md`.
2. Assemble the pack: cover (deal, brand, version, date, deliverables, planned post date), compliance table (each brief requirement, where it is met), the final script, a storyboard table (scene, visual, on-screen text, voiceover), the disclosure wording and where it appears, a claims list with the source of each, schedule and usage rights as Charlie has recorded them, and a sign-off block (name, date, approved or changes needed) left blank.
3. Run the brand-safety check in code and with `foundry.util.ask_json`: banned words from the brief, competitor names, any claim not in the brief's supplied list, profanity, music or footage without a licence noted, personal data of anyone shown. Write the result as a table; any failure is shown to Charlie and fixed in the script, never hidden.
4. Lint: no dashes, no exclamation marks, UK spelling, version and date on every page.
5. Render markdown to HTML with the brand CSS and then to PDF with headless Chrome. Check page count and size (under 5 MB).
6. Open a draft pull request and set the board status to `review`. The job never emails a sponsor.
7. When Charlie records the sponsor's reply in `feedback.md`, the next run produces v2; the job sets itself to `done` in `ventures/<slug>/board.json` once a version is marked approved.

## Output
- `ventures/<slug>/launch/deals/<brand-slug>/approval-pack-v1.md` and `approval-pack-v1.pdf`.
- `ventures/<slug>/launch/deals/<brand-slug>/changes.md`: version, date, what changed. Charlie sends the PDF to the sponsor.

## The ladder
- Human-led: Charlie builds the pack in a document tool.
- Human-assisted: the job assembles, checks and renders; Charlie reviews and sends. This is the default.
- Fully autonomous: not enabled. Documents that carry a sponsor's name go through Charlie.

## The human
What stays with Charlie: sending the pack, recording the sponsor's reply, and confirming the schedule, fee and usage rights, which the job copies but never decides.

## Tools
Free first. Headless Chrome for PDF, Gemini 2.5 Flash and Groq Llama 3.3 70B through `foundry.util.ask_json` (as of Oct 2026, check the limit). Canva free tier by hand if the sponsor wants its own template.

## Build notes
- Not built yet. Stdlib plus `requests`; the pack is one template with slots.
- Fallback with no model: run the code checks only and mark the AI check `not run`.
- Never overwrite an earlier version; each version is a new file.
