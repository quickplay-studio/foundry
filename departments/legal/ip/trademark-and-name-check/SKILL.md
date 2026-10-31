---
name: trademark-and-name-check
title: Trademark and Name Check
department: legal
function: ip
autonomy: solo
stage: clear
builds_on: []
breaks_into: [make-name-variants, search-registers, check-domains-and-stores, score-and-flag]
replaces: "a trade mark attorney's clearance search, typically a few hundred pounds per name"
runs_on: github
status: ready
---

# Trademark and Name Check

Check the venture name against UK and EU trademark registers, Companies House, domains and app stores.

A screening search, not clearance. It finds the obvious conflicts cheaply so a bad name dies before it is built on.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof (the goods and services decide the trade mark classes)

## Inputs
- Venture slug and the working name (and up to two backup names) from `idea.json` or `brain.md`.
- Markets: UK always; EU and US only if the brain says the product sells there.

## Steps
1. Build variants: the exact name, plural and singular, spaced and joined, common misspellings, phonetic matches (Metaphone in code), and obvious translations (Gemini 2.5 Flash). Keep the list under 15.
2. Pick Nice classes from the product: 9 downloadable software and apps, 42 software as a service, 35 online services and advice, 36 finance, 41 education, 44 health, plus the class of the venture's main goods or services.
3. UK IPO "Search for a trade mark" (gov.uk): search each variant as exact and as similar-sounding, in the chosen classes. Record owner, class, status (registered, pending, dead). Pending and registered marks count. If the page cannot be read by Firecrawl, write the exact searches for Charlie to run and set this check to unverified.
4. EUIPO eSearch plus, only if the EU is a market. EU marks do not cover the UK. Also read the WIPO Global Brand Database for international marks.
5. Companies House: call the Public Data API `search/companies` endpoint (free key, `COMPANIES_HOUSE_API_KEY`, within the stated rate limit) for each variant. Flag identical or "too like" live company names and dissolved ones. For a sole trader name, read gov.uk "Choose a business name" for sensitive words and identical registered marks.
6. Domains: an RDAP lookup for the name in `.com`, `.co.uk` and `.app`; a not-found reply means likely free. Never buy; list prices for Charlie.
7. App stores: the iTunes Search API (free, country `gb` and `us`, entity software) for exact and near names. Google Play has no API: read the store search page with Firecrawl or set it to unverified. Also check the GitHub user and organisation name.
8. Passing off: Firecrawl search for the name plus the product category. A business already trading under a similar name in the same field is a risk even without a registered mark.
9. Score each hit red (identical or near-identical live mark or business in the same or related class), amber (similar in a distant class, or taken domain with alternatives) or green. Overall flag: stop if any red, caution if any amber or unverified check, else clear.
10. Rank the name and backups. If the name is stop, say which backup is best and why.

## Output
- `ventures/<slug>/clear/name-check.md`: first line `FLAG: clear`, `FLAG: caution` or `FLAG: stop`, the reason, then a table (register, query, class, hit, owner, status, score), unverified checks, domain prices, and sources read with dates.
- `ventures/<slug>/clear/name-check.json`: `{name, flag, hits: [...], unverified: [...]}`.
- Not legal advice. Drafts are checked by Charlie or a solicitor before use.

## The ladder
- Human-led: Charlie runs the UK IPO and EUIPO searches by hand from the variant list.
- Human-assisted: the job runs the searches and Charlie reviews the amber hits.
- Fully autonomous: the default for this job. It writes the file and board entry; a stop blocks the clear gate until Charlie picks a backup name or overrides.

## The human
What stays with Charlie: choosing and buying the domain, deciding whether to file a UK trade mark (a fee payable to the UK IPO; check the current fee on gov.uk), overriding an amber, and paying a trade mark attorney if a hit in his class is close.

## Tools
Free first. Companies House Public Data API (free key), UK IPO and EUIPO search pages via Firecrawl (free tier 500 credits as of Oct 2026, check the limit), iTunes Search API, RDAP, Gemini 2.5 Flash or Groq for variants and scoring. No paid search tools.

## Build notes
- The UK IPO and EUIPO search pages are dynamic and may not be readable. The job must degrade to `unverified` with the searches listed, never to green.
- Keep variant generation deterministic in code; the model only adds translations and scores borderline hits.
- Tests offline: fixture API replies for a clean name, a live company clash and a registered mark clash.
- GitHub implementation: `run.py` beside this file (jobkit).
