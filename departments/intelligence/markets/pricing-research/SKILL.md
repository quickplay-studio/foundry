---
name: pricing-research
title: Pricing Research
department: intelligence
function: markets
autonomy: solo
stage: validate
builds_on: [competitor-teardown]
breaks_into: [collect-prices, normalise-to-gbp, find-anchors, recommend-band]
replaces: "a pricing consultant's benchmark study"
runs_on: github
status: ready
---

# Pricing Research

What the market charges, the anchors and the packaging patterns.

## Reads from the brain
- `brain/company.md`: voice, constraint that every venture must pay for itself, default UK buyer
- `ventures/<slug>/brain.md`: who, gap, mvp, money (the price and model the venture hopes to charge)

## Inputs
- `ventures/<slug>/validate/competitor-teardown.json`: the competitor list with URLs and app ids. If it is missing, stop and write one line under `skipped` in `board.json`.
- Env: `GEMINI_API_KEY`, `GROQ_API_KEY`; optional `FIRECRAWL_API_KEY`.

## Steps
1. Load `competitors`. For each, take the store price from the App Store lookup API (`itunes.apple.com/lookup?id=<id>&country=gb`, free, no key, about 20 calls a minute per IP as of Oct 2026, check).
2. Collect every plan. Fetch the pricing page with `requests` after checking robots.txt; read the in-app purchase list from the app's store page (`apps.apple.com/gb/app/id<id>`). Where the page needs JavaScript use Firecrawl (500 free credits one-off as of Oct 2026, check; about 1 credit a page; cap this job at 15). Capture per plan: name, price, billing period, what is included, free-tier limits, trial length.
3. Normalise to GBP per month in code: annual divided by 12, one-off shown separately and as a 12-month amount. Convert USD and EUR with the Frankfurter API (ECB rates, free, no key). Mark whether the price includes VAT; UK consumer prices do, many business quotes do not.
4. Find willingness to pay. Hacker News Algolia API (free, no key, about 10,000 requests an hour) and Reddit public JSON (no key, about 10 requests a minute, descriptive User-Agent): search the category with "worth paying", "too expensive", "subscription", "would pay". Add price remarks from 1 and 2 star reviews already in the teardown. Keep the quote, the figure and the link.
5. Compute anchors in code: minimum, 25th percentile, median, 75th percentile, maximum of paid monthly prices. Count packaging patterns: free plus paid, free trial, one-off, subscription, per seat, usage based. Gemini 2.5 Flash (free tier, about 10 requests a minute and 250 a day, check; Groq as fallback) names the pattern buyers expect and the one they complain about, citing the quotes.
6. Recommend a band for the MVP in code: low, base and high in GBP and the billing model. The base sits between the 25th percentile and the median, rising to the 75th percentile only when the top gap in the teardown has 10 or more evidence items. Compare it with the `money` line in the venture brain and say plainly whether the venture's own number fits.
7. Signal in code. `pass`: three or more paying price points found and two or more willingness-to-pay items. `warn`: one or two price points, or no willingness-to-pay quotes. `fail`: no competitor charges anything, or the band's high end is below what the brain's `money` line needs.

## Output
- `ventures/<slug>/validate/pricing-research.md`: plan table in GBP per month, anchors, patterns, recommended band with one-paragraph reasoning, up to 6 quotes with links. Under 500 words.
- `ventures/<slug>/validate/pricing-research.json`: `job`, `signal`, `confidence`, `reason`, `sources`, `credits`, `plans` (competitor, plan, gbp_month, period, includes), `anchors` (min, p25, median, p75, max), `patterns`, `band` (low, base, high, model), `wtp_quotes` (quote, url).
- Mark the job done in `ventures/<slug>/board.json`; failures under `skipped`.

## The ladder
- Human-led: Charlie reads each pricing page and sets the price by instinct and a spreadsheet.
- Human-assisted: the job builds the table and a band; Charlie adjusts the number.
- Fully autonomous: runs after the teardown on every venture and passes the band to the report and to `tam-market-sizing`.

## The human
What stays with Charlie: the actual price and model he is willing to stand behind, and any pricing test with real customers.

## Tools
App Store lookup API, Firecrawl, Hacker News Algolia API, Reddit public JSON, Frankfurter API, Gemini 2.5 Flash, Groq, GitHub Actions. No Claude.

## Build notes
- Runner script; stdlib `statistics` for percentiles. Prices are public list prices only; do not scrape behind a login.
- Percentile rule and the 10-item test are starting values; tune after five ventures.
- Tests offline with saved pricing page HTML fixtures, including a page with annual-only pricing.
