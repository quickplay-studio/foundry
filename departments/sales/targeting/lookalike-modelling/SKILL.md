---
name: lookalike-modelling
title: Lookalike Modelling
department: sales
function: targeting
autonomy: solo
stage: sell
builds_on: [icp-definition]
breaks_into: [read-customer-profile, score-market-map, write-lookalike-rows]
replaces: "the lookalike feature of a paid data tool (ZoomInfo, Apollo)"
runs_on: github
status: ready
---

# Lookalike Modelling

Build fresh target lists from the shape of the accounts that already bought.

## Reads from the brain
- `brain/company.md`: constraints
- `ventures/<slug>/brain.md`: who, money
- `ventures/<slug>/sell/icp.md`: segments and exclusions

## Inputs
- `sell/customers.csv`: `company_number,domain,won_on,value`. Written by Deals or by Charlie.
- `sell/accounts.csv` (account-enrichment) and `sell/market-map.csv`.
- `sell/leads.csv` and `sell/suppression.csv`, to avoid repeats.

## Steps
1. Gate: `audit.json` must say `model: b2b`, else write a `skipped` line in `board.json` and stop.
2. Count customers. Fewer than 5: write `skipped: fewer than 5 customers` and stop. A model from fewer is noise.
3. Make sure every customer has an `accounts.csv` row; run account-enrichment on the missing ones first.
4. Features per account: first three digits of SIC, size band, age band (under 3, 3 to 10, over 10 years), region, tech tags.
5. For each feature value compute lift: its share among customers divided by its share across the map. Keep values with lift of 1.5 or more and at least 3 customers behind them. Normalise lift into weights.
6. Score every map company not already in `leads.csv` or `suppression.csv`. Take the top 200.
7. Gemini writes one line of `notes` for the top 20 from the matching features. It adds no new facts.
8. Write `raw/lookalike.csv` in the raw row shape (the `leads.csv` columns from `company` to `collected_on`, no `id`, plus `notes`) with `source=lookalike` and `subscriber_type=corporate`. Write the weights to `lookalike-model.json`.
9. Re-run monthly or after every 3 new customers.

## Output
- `ventures/<slug>/sell/raw/lookalike.csv`: merged by list-building.
- `ventures/<slug>/sell/lookalike-model.json`: `{"built_on":"YYYY-MM-DD","customers":N,"weights":{"sic3:620":1.8}}`.

## The ladder
- Human-led: Charlie reads the customer list and names the common traits.
- Human-assisted: the job proposes the traits and weights, Charlie trims them.
- Fully autonomous: monthly Action rebuilds the model and the rows.

## The human
What stays with Charlie: marking which customers count as good fits (a discounted pilot may not be one).

## Tools
Python standard library for the lift maths; Gemini 2.5 Flash for the notes (as of Oct 2026, check the limit). No paid lookalike tool.

## Build notes
- Plain counting, no machine-learning library. The point is a transparent list Charlie can read.
- Idle until the first 5 customers; the skip line is the expected state for a new venture.
- Tests: a 6-customer fixture where one SIC prefix dominates, and a 4-customer fixture that must skip.
