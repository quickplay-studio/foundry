---
name: supplier-research
title: Supplier Research
department: commerce
function: sourcing
autonomy: solo
stage: validate
builds_on: [product-selection]
breaks_into: [find-suppliers, extract-terms, check-supplier, rank-and-compare]
replaces: "a sourcing agent or a paid supplier-finding service"
runs_on: github
status: ready
---

# Supplier Research

Find and compare suppliers: price, minimums, lead time, location, reviews, UK delivery options.

Produces a comparison of three to six suppliers for the picked product, with the facts `landed-cost-modelling` needs. It contacts nobody.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints (free tools only; no scraping against a site's terms)
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof (price band, order size Charlie can afford, UK-first delivery promise)

## Inputs
- `ventures/<slug>/idea.json`: `kind` and `channels`. Dropshipping needs suppliers that ship direct to the customer; shop and tiktok-shop may use stock held by Charlie.
- `ventures/<slug>/commerce/shortlist.json`: the picked product (`pick`), or the top-ranked one marked provisional.
- Supplier pages: directory and marketplace listings, supplier websites, and the public reviews of each.
- Optional: supplier quotes or pages Charlie saves in `commerce/data/suppliers/`.

## Steps
1. Read `idea.json` and `shortlist.json`. Stop with a `skipped` line if the kind is not a commerce kind or no product is available.
2. Build 4 to 6 search queries for the product: UK wholesalers, UK dropship suppliers, and overseas manufacturers. Check each site's robots.txt and terms before reading it; log and skip any that forbid it.
3. Collect up to 12 candidate suppliers. For each extract: name, URL, country, price per unit at each quantity break, minimum order quantity, lead time to produce and to ship, shipping options and cost to the UK, whether UK stock is held, sample policy and sample price, branding or private-label options, listed certifications.
4. Check each candidate. UK companies: look up the name in the Companies House API (status active, incorporation date, accounts filed, directors not disqualified in the data returned). Overseas: record how long the supplier has traded on its platform, response rate, and the themes in its reviews. Mark a supplier `unverified` when evidence is thin.
5. Flag red flags: prices far below every other quote, no company details, payment only by bank transfer to a personal account, claims of certifications with no certificate number, reviews that are all recent and generic.
6. Rank the best 3 to 6 on landed price, minimum order, lead time, UK delivery, evidence and fit to the channel (dropshipping needs tracked UK delivery under 7 days or an honest delivery promise).
7. For each ranked supplier write the exact questions Charlie should ask before paying (certificate copies, UK importer or responsible person, packaging and labelling, defect and return terms, sample cost). Do not send them.
8. Write the output. Missing facts are recorded as `unknown`, never guessed.

## Output
- `ventures/<slug>/commerce/suppliers.json`: `{venture, date, product_id, suppliers: [{id, name, url, country, price_breaks: [{qty, unit_gbp}], moq, lead_time_days, ships_to_uk, uk_stock, delivery_days, delivery_cost_gbp, sample_price_gbp, certs_claimed, companies_house: {number, status}, review_themes, red_flags, verified: true|false, questions}], ranking: [ids], notes}`. Prices are converted to GBP with the rate and the date recorded.
- `ventures/<slug>/commerce/suppliers.md`: a short comparison table for Charlie. Read next by `landed-cost-modelling` and `sample-and-quality-check`.

## The ladder
- Human-led: Charlie searches directories and messages suppliers himself.
- Human-assisted: the job gathers and ranks; Charlie contacts the suppliers.
- Fully autonomous: the default for research. Contact, quotes, payment and orders are never autonomous.

## The human
What stays with Charlie: contacting any supplier, negotiating, paying, ordering a sample, and choosing the supplier.

## Tools
Free first. Firecrawl free tier (500 credits as of Oct 2026, check the limit) and Apify free monthly credit for reading supplier pages; Companies House API for UK supplier checks (`COMPANIES_HOUSE_API_KEY`, free); Gemini 2.5 Flash or Groq to extract terms into JSON. No paid sourcing tools.

## Build notes
- Free exchange rates from a public API; store the rate and date next to every converted price.
- Never fabricate a price or a certificate. A fact that was not on the page is `unknown`.
- Missing Companies House key: skip that check, log it, mark the supplier `unverified`.
- Tests offline: fixtures for a UK wholesaler page, an overseas listing with price breaks, and a page with no prices.
