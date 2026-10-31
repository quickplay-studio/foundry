---
name: catalogue-sync
title: Catalogue Sync
department: commerce
function: listings
autonomy: solo
stage: build
builds_on: [listing-optimisation]
breaks_into: [merge-sources, validate-catalogue, export-channel-files, report-drift]
replaces: "a multichannel listing or feed management tool subscription"
runs_on: github
status: ready
---

# Catalogue Sync

One product catalogue file feeding the store, the marketplace and the ad feed; stock and price stay consistent.

Produces one master catalogue and a ready-to-upload file per channel. It uploads nothing and holds no seller login.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints (free tools only; never create accounts)
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof

## Inputs
- `ventures/<slug>/idea.json`: `kind` and `channels`.
- `ventures/<slug>/commerce/listings.json`: titles, bullets, descriptions, search terms per channel.
- `ventures/<slug>/commerce/pricing.json`: the approved price (only prices Charlie has approved are used; otherwise the file is marked `provisional`).
- `ventures/<slug>/commerce/photo-brief.json` and the images Charlie drops in `commerce/data/images/`.
- `ventures/<slug>/commerce/data/stock.csv`: `sku,stock,supplier_stock,updated` exported or typed by Charlie.
- `ventures/<slug>/commerce/suppliers.json`: lead times and the chosen supplier.

## Steps
1. Read `idea.json`; stop with a `skipped` line if the kind is not a commerce kind. Take the channels from it.
2. Merge the sources into one record per sellable variant: `sku`, title, description, price, currency, stock, weight, dimensions, barcode if any, brand, condition, image files, supplier id, lead time, category per channel, country of origin.
3. Validate each record. Required: unique sku, price above the margin floor from `pricing.json`, at least one image that meets the channel's size rule, a UK-English title within each channel's limit, a weight (for shipping), a country of origin, and the warnings from `compliance.md`. Rejected records go to `errors` with the reason; they are left out of channel files.
4. Set availability from stock: `in stock` above the safety level (2 units, or Charlie's value), `out of stock` at zero, `preorder` only if the lead time is stated in the listing. For dropshipping use `supplier_stock` and the supplier lead time.
5. Export one file per channel in that channel's current format, with the field names read from its help centre that run: a Shopify product CSV, a Google Merchant Centre or Meta catalogue feed (TSV or CSV), the TikTok Shop bulk upload template, an Amazon inventory file. Write only the formats for channels named in `idea.json`.
6. Compare with the previous run's `catalogue.json`. List price, stock and title changes per channel. If a price differs between channels for the same sku, flag it unless a channel-specific price is recorded on purpose.
7. Write the run summary and commit the files. If `stock.csv` is older than 7 days, add a staleness warning at the top of the report.

## Output
- `ventures/<slug>/commerce/catalogue.json`: `{venture, date, provisional, items: [{sku, title, description, price_gbp, stock, availability, weight_g, dims_cm, barcode, images, supplier_id, lead_time_days, origin, channels: {channel: {category, title, price_gbp}}}], errors: []}`.
- `ventures/<slug>/commerce/feeds/<channel>.csv`: one upload file per channel.
- `ventures/<slug>/commerce/catalogue-report.md`: errors, drift and changes since the last run. Read next by `inventory-watch` and `order-routing`.

## The ladder
- Human-led: Charlie maintains a spreadsheet and uploads by hand.
- Human-assisted: the job builds the files; Charlie uploads them.
- Fully autonomous: the default for the files and the drift check. Uploading needs a seller login, which agents never hold.

## The human
What stays with Charlie: uploading the feeds, keeping `stock.csv` current, and fixing records the job rejects.

## Tools
Free first. GitHub Actions on a schedule; Python stdlib for CSV and JSON; Firecrawl free tier (500 credits as of Oct 2026, check the limit) to read the channels' upload templates. No paid feed tools.

## Build notes
- Channel field names change; read the template page each run and keep the date in the report.
- Half-up rounding to pence; prices as strings with two decimals in the export.
- Tests offline: fixtures for a valid item, a missing image, a price below the floor, a stale stock file and two channels with different prices.
- GitHub implementation: `run.py` beside this file (jobkit).
