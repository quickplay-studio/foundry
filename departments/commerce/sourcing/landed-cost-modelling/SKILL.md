---
name: landed-cost-modelling
title: Landed Cost Modelling
department: commerce
function: sourcing
autonomy: solo
stage: validate
builds_on: [supplier-research]
breaks_into: [gather-cost-inputs, compute-landed-cost, apply-fees-and-returns, set-break-even-cpa]
replaces: "a margin calculator subscription or a sourcing agent's costing sheet"
runs_on: github
status: ready
---

# Landed Cost Modelling

Unit cost plus shipping, duty, VAT, platform fees, payment fees and returns, into a margin per unit and a break-even ad cost.

Produces the cost model for the picked product. The launch stage's ad brief reads `break_even_cpa` from it.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints (no ad spend without Charlie's approval; UK first)
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof (selling price band, VAT status, margin floor)

## Inputs
- `ventures/<slug>/idea.json`: `kind` and `channels`.
- `ventures/<slug>/commerce/suppliers.json`: price breaks, shipping, lead time, country.
- `ventures/<slug>/commerce/shortlist.json`: the picked product and its price band.
- `ventures/<slug>/commerce/data/costs.json` (optional, Charlie's overrides): selling price, VAT registered yes or no, order quantity, fee rates he has seen in his own seller account.
- Public rates: UK Global Tariff commodity code lookup on gov.uk, HMRC import VAT and duty guidance, current Amazon UK, TikTok Shop UK and Shopify fee pages, payment processor fee page.

## Steps
1. Read `idea.json`; stop with a `skipped` line if the kind is not a commerce kind. Take the first channel in `channels` as the primary one and model the others as extra columns.
2. Pick the supplier (the ranked first, or Charlie's override), the order quantity and the selling price (the midpoint of the price band unless overridden). Mark the whole model `provisional` if the product pick or supplier is not confirmed.
3. Find the commodity code and the duty rate on gov.uk for the product and origin. If the code is unclear, record the two likeliest codes and use the higher duty rate. Duty is charged on customs value, which is goods plus freight and insurance to the UK border.
4. Compute per unit, in GBP, with the exchange rate and date recorded:
   - `unit_cost`: supplier price at the chosen quantity.
   - `shipping`: freight to the UK plus UK delivery to the customer, split per unit.
   - `duty`: rate times customs value. Zero for UK-sourced stock.
   - `vat`: import VAT recoverable if Charlie is VAT registered, otherwise a cost. Also state the output VAT inside the selling price (20 per cent standard rate where it applies; a seller below the registration threshold charges none).
   - `platform_fee`: referral or commission rate times the selling price, plus fixed fees, from the channel's current fee page.
   - `payment_fee`: processor percentage plus fixed fee, where the channel does not bundle it.
   - `returns_allowance`: expected return rate for the category times the cost of a return (outbound lost, return postage, refund of goods that cannot be resold). Default 8 per cent of sales for general goods and 20 per cent for fit-dependent goods, stated as an assumption.
5. `margin_per_unit` = net selling price (excluding output VAT) minus unit_cost, shipping, duty, import VAT cost, platform_fee, payment_fee and returns_allowance. Also give `margin_pct`.
6. `break_even_cpa` = `margin_per_unit`: the most Charlie can pay in ads per sale before the sale loses money. Add `target_cpa` at 60 per cent of it as the figure the ad brief should aim for. If `margin_per_unit` is below zero, set `break_even_cpa` to 0 and `verdict` to `no-go`.
7. Run a sensitivity table: selling price minus 10 per cent, unit cost plus 10 per cent, returns doubled. Show the break-even CPA for each.
8. Write the output. Every rate has a source URL and a date.

## Output
- `ventures/<slug>/commerce/landed-cost.json`: `{venture, date, product_id, supplier_id, channel, currency: "GBP", fx: {rate, date}, selling_price, qty, unit_cost, shipping, duty, vat, platform_fee, payment_fee, returns_allowance, margin_per_unit, margin_pct, break_even_cpa, target_cpa, verdict, provisional, assumptions: [], sources: [{what, url, date}], sensitivity: []}`.
- `ventures/<slug>/commerce/landed-cost.md`: the same as a table. Read next by `pricing-and-offers` and the launch ad brief.

## The ladder
- Human-led: Charlie fills a spreadsheet from his own quotes.
- Human-assisted: Charlie supplies real quotes and fee screenshots; the job recomputes.
- Fully autonomous: the default. The arithmetic is code; the model only extracts rates from pages.

## The human
What stays with Charlie: confirming VAT status with HMRC or an accountant, the final selling price, and any order. The model is an estimate until real quotes replace the assumptions.

## Tools
Free first. Firecrawl free tier (500 credits as of Oct 2026, check the limit) to read gov.uk tariff pages and fee pages; a free public exchange rate API; Gemini 2.5 Flash or Groq to extract rates; plain Python for the sums. No paid costing tools.

## Build notes
- All arithmetic in code with half-up rounding to pence; the model never does sums.
- A rate that cannot be found is an explicit assumption in the file, never silently zero.
- This is not tax advice; duty and VAT treatment is confirmed by Charlie before an order.
- Tests offline: fixtures for UK-sourced stock, an imported product with duty, a negative margin, and a missing supplier file.
