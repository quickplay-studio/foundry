---
name: proof-matching
title: Proof Matching
department: sales
function: outreach-writing
autonomy: solo
stage: sell
builds_on: [personalisation-research]
breaks_into: [inventory-proof, match-pain-to-proof, verify-proof-lines]
replaces: "a sales enablement tool such as Highspot"
runs_on: github
status: ready
---

# Proof Matching

Pick the case study or proof point that fits each prospect's industry and problem.

## Reads from the brain
- `brain/company.md`: voice, "Offers and proof", what we will not do
- `ventures/<slug>/brain.md`: proof, mvp, money

## Inputs
- `sell/icp.md` pains, `sell/customers.csv`, and any notes Charlie leaves in `ventures/<slug>/proof/`.
- `sell/dossiers/` Proof hint lines.

## Steps
1. Gate: `audit.json` must say `model: b2b`, else write a `skipped` line in `board.json` and stop.
2. Inventory only true proof, each with a source. Rank: (a) a customer result Charlie has confirmed in writing, (b) a pilot or trial result, (c) a working demo link, (d) public demand evidence, the Lodestone `proof` links where people asked for this, (e) a stated price and terms.
3. For each ICP pain pick the strongest item that answers it. Each segment gets a primary and a fallback.
4. Write each proof line in 25 words or fewer: what happened, to whom, the number and where it came from. Name a customer only with written permission.
5. Never invent a customer, logo, quote, number or "trusted by" line. If only (d) or (e) exist, say so plainly: people in this field keep asking for this, here is the thread. Offer a pilot only if `money` in the brain allows it.
6. Check each line against its source. Set `verified` with the date. Unverified lines are not written.
7. For tier A leads with a closer match (same SIC prefix or trigger) set a per-lead override.

## Output
- `ventures/<slug>/sell/proof.json`: `{"segments":{"<segment>":{"primary":{"type":"demand","line":"...","source":"url","verified":"YYYY-MM-DD"},"fallback":{...}}},"leads":{"<id>":"<proof key>"}}`.
- Read by cold-email-drafting, linkedin-messaging, cold-call-scripting, video-prospecting.

## The ladder
- Human-led: Charlie picks the proof for each segment.
- Human-assisted: the job inventories and drafts the lines, Charlie confirms any customer claim.
- Fully autonomous: refreshes when `customers.csv` or the brain `proof` changes; a customer claim still needs Charlie's written confirmation first.

## The human
What stays with Charlie: permission from any customer to be named, and the truth of every number.

## Tools
Gemini 2.5 Flash then Groq to phrase the lines (as of Oct 2026, check the limit). The source check is code, not a model.

## Build notes
- A new venture has no customers. Honest demand evidence plus a clear price beats a made-up case study; the job must produce that, not skip.
- Tests: an input with no customers must yield type `demand` lines only.
