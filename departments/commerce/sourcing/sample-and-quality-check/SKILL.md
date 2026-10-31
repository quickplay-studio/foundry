---
name: sample-and-quality-check
title: Sample and Quality Check
department: commerce
function: sourcing
autonomy: human
stage: build
builds_on: [supplier-research]
breaks_into: [choose-sample-order, write-inspection-checklist, set-pass-fail-rules, log-verdict]
replaces: "a sourcing agent's sample handling and a paid third-party inspection"
runs_on: github
status: ready
---

# Sample and Quality Check

What to order as a sample and what to check when it arrives; the ordering and the verdict are Charlie's.

Produces a one-page brief and an inspection sheet. It stops there. The job never orders, pays or judges.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints (nothing paid before revenue unless Charlie decides; he funds samples himself)
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof (what the buyer expects, price band, brand promise)

## Inputs
- `ventures/<slug>/idea.json`: `kind` and `channels`.
- `ventures/<slug>/commerce/suppliers.json`: the ranked suppliers, sample prices and the questions to ask.
- `ventures/<slug>/commerce/shortlist.json`: the picked product and its complaint themes.
- `ventures/<slug>/commerce/compliance.md` if it exists: the safety and labelling requirements.

## Steps
1. Read `idea.json`; stop with a `skipped` line if the kind is not a commerce kind. Read the ranked suppliers and the picked product.
2. Choose what to sample: the top-ranked supplier, plus the second-ranked if the sample prices together are under the cap in `budget.json` (otherwise one only). Name the exact variant, size, colour and quantity (usually one to three units), and the packaging to request.
3. Write the order sheet for Charlie: supplier, link, variant, sample price, delivery cost and time, what to ask for with it (certificate copies, UK responsible person, retail packaging, barcode), and the total. State plainly that Charlie places and pays for the order.
4. Write the inspection checklist from the complaint themes and the compliance notes: build quality, materials and smell, dimensions against the listing, weight, finish, function over repeated use, packaging damage, labelling (name, address, batch, warnings, markings required by compliance), instructions in English, fit with the photos on the supplier page.
5. Add three tests that match the buyer's use, for example a seven-day use test, a wash or wipe test, a drop or stress test, and a photograph test (does it look as good as the listing under daylight and under a phone torch).
6. Set pass, caution and fail rules for each check before the sample arrives, so the verdict is not made after the fact. Any missing required marking or an unsafe finding is an automatic fail.
7. Write a results table with blank cells and a verdict line with `pass`, `pass with changes`, `fail` and a notes field. Photograph every unit on arrival, front, back, labels, packaging.
8. Write the files and set this job to `review` in `board.json`. When Charlie returns the filled sheet, record the verdict and the reasons in `board.json` and pass the failures back to `supplier-research`.

## Output
- `ventures/<slug>/commerce/sample-brief.md`: the order sheet, the inspection checklist, the tests and the pass rules, one page for each.
- `ventures/<slug>/commerce/sample-results.json`: `{product_id, supplier_id, ordered_by: "charlie", date_ordered: null, date_received: null, checks: [{id, check, pass_rule, result: null, photo: null}], verdict: null, notes: ""}` for Charlie to fill.

## The ladder
- Human-led: the default. The job writes the brief and stops.
- Human-assisted: after Charlie fills the sheet, the job totals it, flags any automatic fail and drafts the follow-up questions for the supplier.
- Fully autonomous: not offered. Nobody but Charlie orders a sample or gives a verdict.

## The human
What stays with Charlie: ordering and paying for the sample, inspecting it, the verdict, and whether to go ahead with a bulk order.

## Tools
Free first. Gemini 2.5 Flash or Groq to turn the complaint themes and compliance notes into checks; code to total the results. No paid inspection service until a venture has revenue.

## Build notes
- Agents never place or pay for the order, and never message the supplier.
- The pass rules are written before the sample arrives and are not edited afterwards.
- Dropshipping: the sample is the only way to see the packaging customers receive, so it is never skipped.
- Tests offline: fixtures for a supplier list with one and with two affordable samples, and a missing compliance file.
