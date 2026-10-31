---
name: account-enrichment
title: Account Enrichment
department: sales
function: enrichment
autonomy: solo
stage: sell
builds_on: [list-building]
breaks_into: [pull-register-facts, fingerprint-tech-stack, track-open-roles]
replaces: "ZoomInfo or Apollo firmographic data"
runs_on: github
status: ready
---

# Account Enrichment

Attach firmographics, tech stack and headcount trend to each target account.

## Reads from the brain
- `brain/company.md`: constraints
- `ventures/<slug>/sell/icp.md`: the size bands, tech tags and keywords that matter

## Inputs
- `sell/leads.csv`, one account per `company_number` or `domain`.
- `sell/accounts.csv` from the previous run, and `sell/triggers.csv` if present.
- Secrets `COMPANIES_HOUSE_API_KEY`; optional `FIRECRAWL_API_KEY`.

## Steps
1. Gate: `audit.json` must say `model: b2b`, else write a `skipped` line in `board.json` and stop.
2. Firmographics from Companies House `/company/{number}`: status, type, incorporation date (so age), SIC codes, accounts category (micro-entity, small, medium, full), registered office postcode (so region). Drop accounts that are dissolved or have a strike-off notice and set `status_flag`.
3. Size: the accounts category is the free proxy. Micro is up to 10 employees, small up to 50, medium up to 250. Store it as `size_band` with `size_source=accounts-category`. Do not invent an exact headcount.
4. Tech stack: fetch the homepage with `requests`, respecting `robots.txt`. Apply `rules/tech-fingerprints.json` (meta generator, script URLs, response headers). Read the MX host through Google DNS over HTTPS to tell Google Workspace and Microsoft 365 from others. Store tags such as `wordpress;shopify;google-workspace`. Unknown stays blank.
5. Headcount trend: Firecrawl counts open roles on the careers page. Compare with the last run. `growing` if open roles rose or new roles appeared in two runs in a row, `shrinking` if roles vanished, else `flat`; blank if there is no careers page.
6. Add `recent_trigger` from the strongest live row in `triggers.csv`.
7. Write `accounts.csv`. Refresh each row every 90 days, tier A every 30. Every filled cell has a source in `source_urls`; blank beats wrong.

## Output
- `ventures/<slug>/sell/accounts.csv`: `domain,company_number,company,sic,incorporated_on,age_years,accounts_category,size_band,size_source,region,tech,open_roles,headcount_trend,status_flag,recent_trigger,enriched_on,source_urls`.
- Read by fit-scoring, lookalike-modelling and trigger-detection.

## The ladder
- Human-led: Charlie looks up each company on the register and its site.
- Human-assisted: the job fills the sheet, Charlie spot-checks five rows.
- Fully autonomous: runs after each list-building run and monthly after that.

## The human
What stays with Charlie: pasting a company's LinkedIn size band into the sheet by hand where headcount decides a tier A call.

## Tools
Companies House API, Firecrawl free tier, Google DNS over HTTPS, `requests` (as of Oct 2026, check each limit). No paid firmographic tool.

## Build notes
- Keep fingerprint rules in data, not code: a short JSON map of tag to pattern, easy to extend.
- Tests: homepage and DNS fixtures; assert an unknown stack stays blank and a dissolved company is flagged.
