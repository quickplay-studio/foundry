---
name: contact-enrichment
title: Contact Enrichment
department: sales
function: enrichment
autonomy: solo
stage: sell
builds_on: [list-building]
breaks_into: [read-published-contacts, find-director-names, hunter-lookup, queue-linkedin-lookups]
replaces: "Apollo, Lusha or paid Hunter credits"
runs_on: github
status: ready
---

# Contact Enrichment

Add an email, phone and LinkedIn profile to every lead.

## Reads from the brain
- `brain/company.md`: constraints, what we will not do (no bought lists, no guessed addresses)
- `ventures/<slug>/sell/icp.md`: the titles worth reaching

## Inputs
- `sell/leads.csv`: rows with `suppressed=no`, `subscriber_type=corporate` and a blank `email`. Individuals get no email enrichment.
- Secrets: `FIRECRAWL_API_KEY`, `COMPANIES_HOUSE_API_KEY`, `HUNTER_API_KEY` (all optional, free plans).
- `sell/inbox/linkedin-urls.csv`: `id,linkedin_url`, pasted by Charlie.

## Steps
1. Gate: `audit.json` must say `model: b2b`, else write a `skipped` line in `board.json` and stop.
2. Pass 1, free and published only: Firecrawl reads the homepage, `/contact`, `/about`, `/team` and the footer. Take addresses and phone numbers that appear there. A named business address is `email_basis=named`; a role address (info@, hello@, sales@) is allowed for a corporate subscriber and is `email_basis=role`. Record the page as `source_url`.
3. Names: where no named person was found, use the active director from Companies House as `contact_name`. Leave the email blank unless one is published.
4. Pass 2, after fit-scoring has run: use the Hunter free plan on tier A first, then B. Domain search for the address pattern, email finder for the named person. Accept only a result with a confidence of 80 or more. Stop at 80 percent of the month's credits (as of Oct 2026, check the limit).
5. Never guess an address from a pattern and send to it. A pattern is a search aid; only a published or verified address goes into `email`.
6. Phone: take the main business number from the site or Maps record. Do not store personal mobiles.
7. LinkedIn: no scraping. For tier A, write `linkedin-todo.md` with a search link per person (`https://www.linkedin.com/search/results/people/?keywords=<name>%20<company>`). Charlie opens each from his own account and pastes the profile URL into `inbox/linkedin-urls.csv`. The next run copies it into `linkedin_url`.
8. Write `email`, `email_basis`, `phone`, `linkedin_url`, `source_url`. Never overwrite a non-blank value. Leave `email_status` blank for email-verification.
9. UK GDPR: named business contacts are personal data. The basis is legitimate interests; keep the source and date on every row and honour objections at once.

## Output
- Updated `ventures/<slug>/sell/leads.csv` and `ventures/<slug>/sell/linkedin-todo.md`.

## The ladder
- Human-led: Charlie finds each contact by hand.
- Human-assisted: the job fills what is published, Charlie does the LinkedIn lookups.
- Fully autonomous: both passes run weekly; the LinkedIn column still waits for Charlie.

## The human
What stays with Charlie: LinkedIn lookups from his own account, and the Hunter, Firecrawl and Companies House sign-ups.

## Tools
Firecrawl free tier, Companies House API, Hunter free plan, Gemini 2.5 Flash for page extraction (as of Oct 2026, check each limit). No paid enrichment.

## Build notes
- Extract with a regex first, Gemini only for ambiguous pages, to save free quota.
- Tests: a page fixture with a role address and a named address; assert a guessed pattern is never written.
