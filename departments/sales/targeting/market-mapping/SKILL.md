---
name: market-mapping
title: Market Mapping
department: sales
function: targeting
autonomy: solo
stage: sell
builds_on: [icp-definition]
breaks_into: [translate-icp-to-filters, query-company-register, dedupe-and-size, report-coverage]
replaces: "a ZoomInfo or Apollo seat used for market sizing"
runs_on: github
status: ready
---

# Market Mapping

List every company in a vertical that fits the ICP before any campaign starts.

## Reads from the brain
- `brain/company.md`: constraints, what we will not do
- `ventures/<slug>/brain.md`: who, problem
- `ventures/<slug>/sell/icp.md`: the `icp` JSON block (SIC prefixes, size bands, regions, exclusions)

## Inputs
- The `icp` block.
- Secret `COMPANIES_HOUSE_API_KEY` (Charlie registers for the free key himself). Optional `FIRECRAWL_API_KEY`.

## Steps
1. Gate: `ventures/<slug>/audit.json` must say `model: b2b`; otherwise write a line under `skipped` in `board.json` and stop.
2. For each segment build a Companies House advanced search: `sic_codes` from the ICP, `company_status=active`, `location` from the region, and an incorporation date at least 12 months back unless the ICP wants new companies.
3. Call `GET https://api.company-information.service.gov.uk/advanced-search/companies` with the key as the basic-auth username and an empty password. Page with `start_index` and `size` as the current docs say. Keep under the rate limit (600 requests per five minutes at last check; as of Oct 2026, check the limit).
4. Keep limited companies, PLCs and LLPs only. These are corporate subscribers under PECR, so the map starts on lawful ground.
5. Drop rows whose name or SIC matches the ICP exclusions. Dedupe on `company_number`.
6. Where a vertical is mostly sole traders (local trades, salons), note `register_covered: no` for that segment and leave it to web-and-maps-scraping.
7. Write `market-map.csv` and `market-map.md`. In the report give the count per segment, the share with a known website, the register pull date, and a recommended first slice of 200 companies (narrowed by region or size) for the first campaign.

## Output
- `ventures/<slug>/sell/market-map.csv`: `company_number,company,segment,sic_codes,incorporated_on,postcode,region,company_type,source,collected_on`.
- `ventures/<slug>/sell/market-map.md`: counts, gaps, the first slice.
- Read by database-mining, trigger-detection and lookalike-modelling.

## The ladder
- Human-led: Charlie searches the register by hand and pastes the rows into the CSV.
- Human-assisted: the job pulls the map and Charlie picks the first slice.
- Fully autonomous: the job pulls, sizes and picks the slice by smallest region that holds 200 companies.

## The human
What stays with Charlie: approving the first slice and deciding what to do about segments the register cannot cover.

## Tools
Companies House API (free key; as of Oct 2026, check the limit and terms). Firecrawl free tier only to find a missing website. Gemini 2.5 Flash for the coverage paragraph. No paid list.

## Build notes
- Write rows as they arrive and keep `market-map-state.json` with the last `start_index`, so a run cut by the Actions time limit resumes.
- Tests use a saved API response fixture; never call the live API in tests.
- Re-run quarterly. New companies join the map; none are deleted, only marked `inactive`.
- GitHub implementation: `run.py` beside this file (jobkit).
