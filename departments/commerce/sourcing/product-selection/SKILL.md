---
name: product-selection
title: Product Selection
department: commerce
function: sourcing
autonomy: assisted
stage: validate
builds_on: [vertical-analysis, trend-monitoring]
breaks_into: [build-search-terms, collect-listings, screen-out-risk, score-and-rank]
replaces: "a product research VA or a paid product research tool subscription"
runs_on: github
status: ready
---

# Product Selection

Shortlist products with demand, margin and low return risk from marketplace and social signals; Charlie picks.

Produces a ranked shortlist of five to eight products with the evidence for each. Every later commerce job works on the product Charlie picks.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints (free tools only; nothing regulated without a human and a solicitor)
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof (the niche, the buyer, the price band, any margin floor or VAT status)

## Inputs
- `ventures/<slug>/idea.json`: `kind` and `channels`.
- `ventures/<slug>/validate/`: the vertical-analysis and trend-monitoring outputs (niche, rising terms, audience).
- Public pages: Amazon UK best sellers and new releases for the niche, TikTok Shop UK product pages, TikTok Creative Center top products, review pages of the leading listings.
- Optional: pages Charlie saved in `commerce/data/pages/`; `commerce/reviews/complaints.json` once a shop has live reviews (recurring complaints to avoid).

## Steps
1. Read `idea.json`. If `kind` is not shop, tiktok-shop or dropshipping, log a `skipped` line in `board.json` (reason: not a commerce venture) and stop. Note `channels`; if empty, assume tiktok-shop for kind tiktok-shop and shopify otherwise, and say so in the output.
2. Write 8 to 15 search terms from the brain niche, the vertical-analysis keywords and the rising terms in trend-monitoring. Tag each with the channel it serves.
3. Before the first fetch from a domain, read its robots.txt and terms. If automated reading is not allowed, fetch nothing from it, log it under `skipped` and use the pages in `commerce/data/pages/` instead.
4. For each term collect up to 20 listings: title, URL, price, rating, review count, rank or units-sold badge, seller count. For the leading five also collect the 1 to 3 star review themes (what buyers complain about).
5. Screen out and record each in `excluded` with the reason: health, supplements, children's products and finance (company rule); anything on a target channel's prohibited list; counterfeit, branded or licensed goods; age-restricted goods (knives, vapes, alcohol); items with a gov.uk product safety alert or recall.
6. Score the rest 0 to 100: demand 30 (rank, units sold, review velocity, rising term), margin 25 (selling price against a rough supplier price from one directory search), return risk 20 (size or fit dependent, fragile, compatibility problems, complaint themes; low risk scores high), competition 15 (no dominant seller, fixable complaints), compliance simplicity 10 (no electricals, cosmetics, toys or food). The model extracts and judges; code does the arithmetic and the ranking.
7. Keep the top 5 to 8. For each give the evidence lines (source, URL, what it shows), the price band, a rough unit cost, return risk, complaint themes and a one-sentence reason.
8. Write the output and set this job to `review` in `board.json`.

## Output
- `ventures/<slug>/commerce/shortlist.json`: `{venture, date, kind, channels, pick: null, products: [{id, name, score, demand: [{source, url, note}], price_band_gbp: [low, high], est_unit_cost_gbp, est_margin_pct, return_risk: "low|medium|high", complaint_themes, compliance_note, why}], excluded: [{name, reason}]}`.
- `ventures/<slug>/commerce/shortlist.md`: the same as a table with the evidence, for Charlie to read.
- Charlie sets `pick` to a product id. While `pick` is null, later jobs use the top-ranked product and mark their output `provisional`.

## The ladder
- Human-led: Charlie browses the marketplaces and picks from his own notes.
- Human-assisted: the default. The job gathers the evidence and ranks; Charlie picks.
- Fully autonomous: not offered. The pick commits money later, so it stays Charlie's.

## The human
What stays with Charlie: the pick, any exception to the exclusions (a regulated product), and the decision to go on to samples.

## Tools
Free first. Firecrawl free tier (500 credits as of Oct 2026, check the limit) and Apify free monthly credit (check the amount) to read listings, review pages and the TikTok Creative Center; Gemini 2.5 Flash, then Groq, for extraction and judgement; code for scoring. No paid research tools.

## Build notes
- Read only what a site's terms allow. A site that forbids it is replaced by pages Charlie saves by hand.
- Keep fetches small (20 listings per term, 5 review pages per product) to stay inside the free credits.
- Model output is parsed as JSON and validated. On failure fall back to a heuristic score from rank and price only, and log `skipped`.
- Tests offline: fixtures for a clean niche, a niche where half the candidates are excluded, and a missing key.
