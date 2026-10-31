---
name: icp-definition
title: ICP Definition
department: sales
function: targeting
autonomy: solo
stage: sell
builds_on: []
breaks_into: [read-venture-brain, draft-segments, set-scoring-weights, update-from-outcomes]
replaces: "the segment research share of an SDR salary, or a sales consultant's positioning workshop"
runs_on: claude-code
status: ready
---

# ICP Definition

Write and keep the ideal customer profile per vertical: size, pains, buying triggers.

## Reads from the brain
- `brain/company.md`: voice, constraints, what we will not do
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof
- `ventures/<slug>/audit.json`: the `model` field. Sales runs only when it is `b2b`

## Inputs
- The three files above.
- Once they exist: `ventures/<slug>/sell/sent.csv`, `replies.csv` and `leads.csv`, for the monthly update.

## Steps
1. Gate: if `audit.json` does not say `model: b2b`, add a line under `skipped` in `board.json` ("no business buyer") and stop.
2. From `brain.md` list who pays, what they do now instead, and what the MVP fixes. Treat the `proof` links as evidence of pain. Add no fact that is not in the brain.
3. Split the buyers into one to three segments. For each: a plain name, UK SIC 2007 code prefixes, employee band, region, and the job title that signs off.
4. For each segment write three pains in the buyer's own words, three buying triggers that can be seen from outside (new director, hiring for a named role, share allotment filing, funding news, stack change), and disqualifiers (too small, regulated sector Charlie cannot serve, competitor).
5. Set scoring weights that sum to 100: `firmographic`, `pain`, `trigger`, `reachability`. Default 40, 25, 20, 15.
6. Write the offer line from `money` and `mvp`: price and what it does, in two lines.
7. Write `icp.md` (shape below), ending with a fenced `json` block named `icp` that other jobs parse.
8. Monthly, once `sent.csv` holds 100 sends or more: compare reply and meeting rate by segment, tier and trigger. Change a filter only where the gap holds over at least 30 sends per cell. Log each change in the Changelog.

## Output
- `ventures/<slug>/sell/icp.md`. Sections: Offer, Segments, Pains, Triggers, Disqualifiers, Weights, Changelog.
- The `icp` block: `{"segments":[{"name","sic_prefixes","size_bands","regions","titles","keywords","exclusions"}],"weights":{"firmographic":40,"pain":25,"trigger":20,"reachability":15},"offer":"..."}`.
- Read by market-mapping, database-mining, web-and-maps-scraping, social-mining, lookalike-modelling, fit-scoring and cold-email-drafting.

## The ladder
- Human-led: Charlie writes `icp.md` himself in the shape above.
- Human-assisted: a Sonnet session drafts it from the brain and Charlie edits the segments.
- Fully autonomous: Gemini drafts it on deployment and the monthly update edits filters from outcomes, one segment change a month at most.

## The human
What stays with Charlie: confirming the segments before the first list is built, and ruling out any regulated vertical.

## Tools
Claude Code (Sonnet) for the first draft, reading the three brain files only. Gemini 2.5 Flash or Groq for the monthly update. The SIC 2007 code list is public; no paid data.

## Build notes
- One run per venture plus a monthly refresh, so the Claude cost is one short session.
- If no Claude session is free, run the same prompt through `foundry.util.ask_json`. The output must still parse the `icp` block.
- Outcomes beat the draft: after the first 100 sends the data wins over any guess in the file.
