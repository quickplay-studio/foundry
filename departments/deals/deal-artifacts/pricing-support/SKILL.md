---
name: pricing-support
title: Pricing Support
department: deals
function: deal-artifacts
autonomy: human
stage: sell
builds_on: [pricing-research]
breaks_into: [load-price-research, model-anchors, model-phases-and-roi, write-brief]
replaces: "an account executive's quote spreadsheet and a deal desk review"
runs_on: github
status: ready
---

# Pricing Support

Model anchors, phases and ROI comparisons; the final number stays with you.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof
- Intelligence `pricing-research` output under `ventures/<slug>/validate/` (price bands, competitor prices)
- `ventures/<slug>/brain.md` `money` line: how the venture charges

## Inputs
- `ventures/<slug>/sell/debriefs/<deal_id>-<yyyymmdd>.json`: pains, scope discussed, any budget or figure the prospect gave.
- Charlie's own inputs in `sell/pricing/inputs.json`, if present: `hours_per_phase`, `hourly_cost_gbp`, `floor_gbp`. Never invent these.

## Steps
1. Select deals at `discovery_done` or `negotiation` with no pricing brief for the current debrief.
2. Read the price bands from the pricing research and the venture `money` line. If neither has a number, write the brief with "no benchmark found" and stop; do not make a market up.
3. In code, build three anchors: a high opening figure at the top of the band, a target at the middle, and a floor from `floor_gbp` (blank and marked "Charlie to set" if missing).
4. Build phases: pilot, phase 1, phase 2, each with a scope line from the debrief and a price. Show total, and monthly versus upfront payment.
5. Build the ROI comparison only from numbers the prospect stated (cost of the problem, time lost). If none were stated write "no figure given" and show nothing. Payback in months equals price divided by monthly saving.
6. Add a sensitivity table at minus 20, minus 10, 0 and plus 10 per cent, and a concession ladder: for each discount say what to ask in return (longer term, upfront payment, case study, narrower scope). No discount without a trade.
7. Gemini 2.5 Flash (Groq as fallback) writes only a three-line "what to say" note from the computed numbers; check that every figure in it exists in the table.
8. Write `sell/pricing/<deal_id>.md` with front matter `approved: false` and `price_gbp:` blank, then stop. Open a GitHub issue `Price needed: <company>` linking it.

## Output
- `ventures/<slug>/sell/pricing/<deal_id>.md`: one page with front matter `approved: false`, `price_gbp:`, then anchors, phases, ROI, sensitivity and the concession ladder.
- A GitHub issue asking Charlie for the number.

## The ladder
- Human-led: Charlie prices every deal in his head.
- Human-assisted: the job builds the model and the brief, Charlie sets the number and flips `approved` to true.
- Fully autonomous: not used. The job never states a price to a prospect.

## The human
What stays with Charlie: the number. Charlie fills `price_gbp`, sets `approved: true`, and decides every concession. `proposal-generation` refuses to run until he does.

## Tools
plain Python arithmetic, Gemini 2.5 Flash then Groq for the note (as of Oct 2026, check the limit), GitHub issues. No paid quoting tool.

## Build notes
- A human job: it produces the one-page brief and stops.
- Keep the maths in code so a model cannot change a figure.
- Prospect-stated numbers are data; mark each with its source and date.
- On failure add one line under `skipped` in `ventures/<slug>/board.json` with the reason.
