---
name: tam-market-sizing
title: TAM / Market Sizing
department: intelligence
function: markets
autonomy: solo
stage: validate
builds_on: [vertical-analysis]
breaks_into: [define-buyer, count-buyers, price-and-model, scenario-range]
replaces: "an analyst's market-size workbook"
runs_on: github
status: ready
---

# TAM / Market Sizing

How many buyers actually fit, and what the prize is worth.

## Reads from the brain
- `brain/company.md`: default market (UK, then English-speaking), constraint that ventures pay for themselves
- `ventures/<slug>/brain.md`: who, money (the revenue the venture must reach), mvp

## Inputs
- `ventures/<slug>/validate/vertical-analysis.json`: the vertical line, counts and sources. If missing, stop and log under `skipped`.
- `ventures/<slug>/validate/pricing-research.json` if it exists (use `band`); otherwise the paid prices found in the vertical analysis, or the brain's `money` line.
- Env: `GEMINI_API_KEY`, `GROQ_API_KEY`; optional `COMPANIES_HOUSE_API_KEY`.

## Steps
1. Define the buyer in one sentence with filters: country, age band, household type, business size, sector. One model call; the filters are saved as data.
2. Count top-down. ONS API (`api.beta.ons.gov.uk/v1`, free, no key) for UK population, households and age bands. Nomis API (`nomisweb.co.uk/api/v01`, free, light use without a key) for UK business counts by size and sector. For a second market, World Bank API (`api.worldbank.org/v2`, free, no key) population for the US, Canada, Australia, Ireland or New Zealand. Check each limit as of Oct 2026. Apply each filter as a stated ratio with its source link.
3. Cross-check bottom-up. From `competitors` in the teardown if present, or the App Store results in the vertical analysis: rating count times an assumed users-per-rating multiple. Use 100 as base, 30 and 300 as bounds, and label it an assumption.
4. Price and model. Annual revenue per buyer from the pricing band: monthly price times 12 times a retention factor (state it), or one-off price times purchases a year.
5. Compute in code, never with the model: TAM is buyers times annual revenue per buyer. SAM is the share reachable through the channels the brain's `who` implies (state the share and the reason). SOM for year one is SAM times reach share times conversion, in low, base and high cases. Write every assumption beside its number. Base conversion for a free-to-paid product is 1 percent of those reached, low 0.3, high 3; these are starting values.
6. Compare top-down and bottom-up. If they differ by more than 5 times, say so and mark the lower-confidence one.
7. Signal in code. The floor is the year-one revenue in the brain's `money` line; if none is given, use GBP 6,000 and say that it is a default. `pass`: base SOM at least 2 times the floor. `warn`: between 1 and 2 times, or the two methods differ by more than 5 times. `fail`: base SOM below the floor.

## Output
- `ventures/<slug>/validate/tam-market-sizing.md`: buyer definition, funnel table (TAM, SAM, SOM low, base, high in GBP), assumptions list, the cross-check, what would move the number most. Under 400 words.
- `ventures/<slug>/validate/tam-market-sizing.json`: `job`, `signal`, `confidence`, `reason`, `sources`, `buyer`, `counts` (value, source), `tam`, `sam`, `som` (low, base, high), `floor`, `assumptions`. `data-visualisation` reads this for the funnel chart.
- Mark the job done in `ventures/<slug>/board.json`.

## The ladder
- Human-led: Charlie builds the sizing in a spreadsheet from ONS tables.
- Human-assisted: the job finds the counts and does the sums; Charlie challenges the reach and conversion assumptions.
- Fully autonomous: runs after the vertical analysis on every venture and feeds the report.

## The human
What stays with Charlie: the reach and conversion assumptions, which decide the answer and are judgement, and the revenue floor in the brain.

## Tools
ONS API, Nomis API, World Bank API, Companies House API (optional), Gemini 2.5 Flash (free tier, about 10 requests a minute and 250 a day, check), Groq, GitHub Actions. No Claude.

## Build notes
- Runner script with the funnel arithmetic as plain functions; unit test the sums. A figure with no source link is rejected before it is written.
- Official statistics lag; state the year of every count.
- Tests offline with saved ONS and Nomis responses.
