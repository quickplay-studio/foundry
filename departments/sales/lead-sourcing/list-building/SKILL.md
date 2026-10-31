---
name: list-building
title: List Building
department: sales
function: lead-sourcing
autonomy: solo
stage: sell
builds_on: [database-mining, web-and-maps-scraping, social-mining]
breaks_into: [load-raw-rows, classify-subscribers, dedupe-and-suppress, segment-and-write]
replaces: "the list-cleaning share of an SDR salary"
runs_on: github
status: ready
---

# List Building

Merge, dedupe and segment raw leads into a campaign-ready list.

## Reads from the brain
- `brain/company.md`: constraints, what we will not do (no bought lists, no unsolicited email outside the law)
- `ventures/<slug>/sell/icp.md`: segments and exclusions

## Inputs
- Every `sell/raw/*.csv` (database, maps, social, lookalike, and any list Charlie adds by hand).
- `sell/suppression.csv`: `email_or_domain,added_on,reason`. Unsubscribes, bounces and "no" replies land here.

## Steps
1. Gate: `audit.json` must say `model: b2b`, else write a `skipped` line in `board.json` and stop.
2. Normalise: lower-case domains and drop `www.`, trim names, put phones in +44 form, drop rows with no company and no contact route.
3. Classify `subscriber_type`. `corporate` only when a Companies House number shows a limited company, PLC or LLP, or the body is a public authority. Everything else, and anything unknown, is `individual`. Free-mail addresses (gmail.com, outlook.com, hotmail, yahoo, icloud) on a company row are personal: blank the email and note it.
4. Dedupe on `company_number + contact_name`, else `domain + contact_name`, else `email`. Keep the fuller row and the earliest `collected_on`; join `source` values with `;`.
5. Suppress: set `suppressed=yes` for any email or domain on `suppression.csv`. Never delete the row, so the "do not contact" memory survives re-imports.
6. Assign `segment` from the ICP filters. Rows matching none go to `leads-rejected.csv` with a reason.
7. Give new rows an `id` (`L0001`, `L0002`, ...). Existing ids never change.
8. Write `leads.csv` and `list-report.md`. The report opens with the PECR line: only `corporate` rows, with a business address, not suppressed, may receive cold email; sole traders and partnerships may not. It gives the email-eligible count, then counts by segment and source.

## Output
- `ventures/<slug>/sell/leads.csv`: `id,company,company_number,domain,website,segment,subscriber_type,contact_name,role,email,email_basis,phone,linkedin_url,source,source_url,collected_on,email_status,verified_on,fit_score,tier,fit_reason,suppressed,notes`. Later jobs fill the blank columns and never reorder them.
- `leads-rejected.csv` and `list-report.md` beside it.
- The CSV is the CRM. Charlie may import it into HubSpot's free CRM by hand; the CSV stays the source of truth.

## The ladder
- Human-led: Charlie merges the raw files in a spreadsheet.
- Human-assisted: the job builds the list, Charlie reads the report.
- Fully autonomous: runs after each sourcing job; the PECR filter has no override.

## The human
What stays with Charlie: reading the report before the first campaign, and adding any manual list to `raw/`.

## Tools
Python standard library only. Gemini 2.5 Flash only to settle ambiguous segment matches.

## Build notes
- Idempotent: running twice changes nothing. Tests: duplicate across two sources, a suppressed domain, a gmail.com address on a company row.
- `leads.csv` is the contract for every later Sales job; change columns only by appending.
