---
name: trigger-detection
title: Trigger Detection
department: sales
function: targeting
autonomy: solo
stage: sell
builds_on: [market-mapping]
breaks_into: [watch-filings, watch-hiring, watch-news, rank-triggers]
replaces: "a paid sales-signals subscription (ZoomInfo or Apollo alerts)"
runs_on: github
status: ready
---

# Trigger Detection

Watch targets for hiring, funding, stack and leadership changes that mean budget.

## Reads from the brain
- `brain/company.md`: constraints
- `ventures/<slug>/brain.md`: the problem, so hiring and news keywords match the pain
- `ventures/<slug>/sell/icp.md`: the Triggers section and `keywords`

## Inputs
- `sell/market-map.csv`, and `sell/leads.csv` once it exists (tier A and B first).
- `sell/triggers-state.json`: last filing and officer ids seen per company.
- Secrets `COMPANIES_HOUSE_API_KEY`; optional `FIRECRAWL_API_KEY`.

## Steps
1. Gate: `audit.json` must say `model: b2b`, else write a `skipped` line in `board.json` and stop.
2. Build the watch list: tier A and B leads, else the first slice of the map. Cap it at 300 companies so a run fits the free Actions minutes.
3. Filings: for each company call `/company/{number}/officers` and `/company/{number}/filing-history`. Compare with `triggers-state.json`. Triggers: `new-director`, `new-charge` (borrowing), `share-allotment` (form SH01, a funding signal), `address-change`.
4. Hiring: Firecrawl reads the careers or jobs page. Match open roles to the ICP keywords. Tier A weekly, tier B fortnightly.
5. News: read the Google News RSS search feed for the company name plus words such as raises, hires, appoints, launches, acquires. Keep only items naming the company.
6. Stack: for tier A, re-run the account-enrichment fingerprint and compare with `accounts.csv`. A changed tag is `stack-change`.
7. Every hit needs an `evidence_url` the job actually fetched; drop any hit without one. Gemini may write a summary of at most 20 words from the fetched text and may infer nothing beyond it.
8. Strength: `high` (leadership change, funding, hiring the exact role), `medium` (filing, news), `low` (anything else). Expiry 60 days after the event.
9. Append to `triggers.csv`; update the state file.

## Output
- `ventures/<slug>/sell/triggers.csv`: `date,company_number,domain,trigger_type,strength,evidence_url,summary,expires_on`.
- Read by fit-scoring (trigger weight) and personalisation-research (opener).

## The ladder
- Human-led: Charlie scans the news for his target list and types hits in.
- Human-assisted: the job lists hits weekly and Charlie deletes the false ones.
- Fully autonomous: weekly Action, evidence check, expiry, no review.

## The human
What stays with Charlie: reading the high-strength hits before a tier A message cites one.

## Tools
Companies House API, Firecrawl free tier, Google News RSS, Gemini 2.5 Flash then Groq (as of Oct 2026, check each limit). No paid signals feed.

## Build notes
- Poll, do not stream, until a venture needs speed; the Companies House streaming API is a later option.
- Dedupe on `company_number + trigger_type + evidence_url`.
- Tests: fixtures for officers, filings and an RSS feed; assert a hit without evidence is dropped.
