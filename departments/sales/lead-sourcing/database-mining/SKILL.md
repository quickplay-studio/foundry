---
name: database-mining
title: Database Mining
department: sales
function: lead-sourcing
autonomy: solo
stage: sell
builds_on: [icp-definition]
breaks_into: [query-registers, pull-officers, find-websites, write-raw-rows]
replaces: "a ZoomInfo or Cognism data seat"
runs_on: github
status: ready
---

# Database Mining

Pull company and contact lists from structured databases and open registers.

## Reads from the brain
- `brain/company.md`: constraints, what we will not do (no bought lists, no scraping against terms)
- `ventures/<slug>/brain.md`: who, problem
- `ventures/<slug>/sell/icp.md`: segments, SIC prefixes, titles, exclusions

## Inputs
- `sell/icp.md`; `sell/market-map.csv` if market-mapping has run (use its first slice, else query inline).
- Secrets: `COMPANIES_HOUSE_API_KEY`; optional `FIRECRAWL_API_KEY`.
- `sell/raw/database-state.json`: resume point.

## Steps
1. Gate: `audit.json` must say `model: b2b`, else write a `skipped` line in `board.json` and stop.
2. For each company in the slice call Companies House `/company/{number}` (status, type, SIC, accounts category, registered office) and `/company/{number}/officers`.
3. Keep active officers only, as `contact_name` with role `Director` or `Secretary`. Do not store dates of birth or correspondence addresses. Skip corporate officers.
4. Website: Companies House does not hold it. Use Firecrawl search on the company name and town. Accept a domain only if the page text contains the exact company name or number; otherwise leave `domain` blank.
5. Other open registers when the ICP calls for them: Charity Commission register, FCA Financial Services Register (authorised firms as buyers), Food Standards Agency hygiene ratings, Contracts Finder for public-sector suppliers. Each is free, some need a key; as of Oct 2026, check the limit and terms. Never use a source whose terms forbid reuse; log the skip under `skipped`.
6. Set `subscriber_type` from the legal form: `corporate` for limited companies, PLCs, LLPs and public bodies; `individual` for everything else or unknown. Cold email goes to `corporate` only.
7. Leave `email` blank. Contact-enrichment fills it from published sources.
8. Write rows with `source` (register name), `source_url` (that record's page) and `collected_on`. Stop at the Actions time limit and save the resume point.

## Output
- `ventures/<slug>/sell/raw/database.csv`, in the raw row shape: the `leads.csv` columns from `company` to `collected_on` (`company,company_number,domain,website,segment,subscriber_type,contact_name,role,email,email_basis,phone,linkedin_url,source,source_url,collected_on`), no `id`.
- Merged by list-building.

## The ladder
- Human-led: Charlie exports from the register websites and pastes into `raw/database.csv`.
- Human-assisted: the job pulls the rows and Charlie spot-checks ten.
- Fully autonomous: weekly Action with the state file, no review.

## The human
What stays with Charlie: getting the free API keys and adding them as GitHub secrets, and approving any new register as a source.

## Tools
Companies House API, Firecrawl free tier, the other free registers above (as of Oct 2026, check the limit). Claude Code only if a register needs a bespoke parser.

## Build notes
- Cache each API response under `raw/cache/` (git-ignored) so a re-run costs no calls.
- Tests: fixtures for company and officer JSON; assert no date of birth reaches the CSV.
- GitHub implementation: `run.py` beside this file (jobkit).
