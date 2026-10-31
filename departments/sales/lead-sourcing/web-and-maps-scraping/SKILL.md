---
name: web-and-maps-scraping
title: Web and Maps Scraping
department: sales
function: lead-sourcing
autonomy: solo
stage: sell
builds_on: [icp-definition]
breaks_into: [build-search-queries, run-maps-actor, read-directory-pages, match-to-register]
replaces: "Outscraper or Apollo credits for local business lists"
runs_on: github
status: ready
---

# Web and Maps Scraping

Collect local businesses and niche directory entries as leads.

## Reads from the brain
- `brain/company.md`: constraints, what we will not do (no scraping against a site's terms)
- `ventures/<slug>/brain.md`: who, problem
- `ventures/<slug>/sell/icp.md`: segments, keywords, regions, exclusions

## Inputs
- `sell/icp.md`.
- Secrets `APIFY_TOKEN` and `FIRECRAWL_API_KEY` (both optional, free tiers). Without them the job writes a `skipped` line.
- `sell/directories.txt`: niche directory and trade-body member-list URLs, added by Charlie or proposed by the job.

## Steps
1. Gate: `audit.json` must say `model: b2b`, else write a `skipped` line in `board.json` and stop.
2. Build 5 to 10 search strings per segment ("<trade> in <town>") from the ICP keywords and regions.
3. Maps: run the Apify Google Maps actor with those strings, one location per run, a result cap of 50 on the first run. Check the free monthly credit first (as of Oct 2026, check the limit) and stop at 80 percent of it. Read the actor's page for its stated terms.
4. Directories: Firecrawl reads member-list pages. Fetch `robots.txt` first and read the site's terms. If either forbids it, skip the site and log it under `skipped`. No logged-in scraping.
5. Keep business facts only: name, address, phone, website, category. Do not keep reviewer names or review text.
6. Match each hit to Companies House by name and postcode. A match sets `company_number` and `subscriber_type=corporate`. No match means sole trader or partnership: `subscriber_type=individual`, kept for non-email routes only.
7. Business phone numbers are stored but not called until cold-call-scripting screens them against TPS and CTPS.
8. Dedupe on domain, then phone. Write rows with `source=google-maps` or the directory name, `source_url`, `collected_on`.

## Output
- `ventures/<slug>/sell/raw/maps.csv`, in the raw row shape (`leads.csv` columns from `company` to `collected_on`, no `id`).
- Merged by list-building. Individuals in this file are never emailed.

## The ladder
- Human-led: Charlie searches Maps and directories and types the rows.
- Human-assisted: the job runs the actor and reads directories, Charlie reviews the first 50.
- Fully autonomous: monthly Action within the credit cap.

## The human
What stays with Charlie: approving each new directory after the terms check. The free credit is the spending limit.

## Tools
Apify free monthly credit (Google Maps actor), Firecrawl free tier, Companies House API for the match (as of Oct 2026, check each limit). No paid scraper.

## Build notes
- Log credit used per run in `board.json` so the 80 percent stop is auditable.
- Tests: an actor output fixture with one limited company and one sole trader; assert the sole trader is `individual`.
