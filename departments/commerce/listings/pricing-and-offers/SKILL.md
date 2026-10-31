---
name: pricing-and-offers
title: Pricing and Offers
department: commerce
function: listings
autonomy: assisted
stage: launch
builds_on: [landed-cost-modelling, pricing-research]
breaks_into: [set-margin-floor, build-price-ladder, design-bundles-and-offers, check-law-and-margin]
replaces: "a pricing consultant or a paid repricing tool"
runs_on: github
status: ready
---

# Pricing and Offers

Price points, bundles and launch offers that clear the margin floor; Charlie approves any price.

Produces a price ladder and a short list of offers, each tested against the cost model. Nothing goes live until Charlie approves it.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints (say the price in the first two lines; Charlie approves every budget line)
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof (price band, margin floor, VAT status)

## Inputs
- `ventures/<slug>/idea.json`: `kind` and `channels`.
- `ventures/<slug>/commerce/landed-cost.json`: unit_cost, shipping, duty, vat, platform_fee, payment_fee, returns_allowance, margin_per_unit, break_even_cpa.
- `ventures/<slug>/validate/pricing-research.md`: competitor and market price points.
- `ventures/<slug>/commerce/listings.json` if it exists: the channels.
- Optional: `ventures/<slug>/commerce/data/price-limits.json`, Charlie's own floor or ceiling.

## Steps
1. Read `idea.json`; stop with a `skipped` line if the kind is not a commerce kind. Mark the output `provisional` if `landed-cost.json` is provisional.
2. Set the margin floor: the larger of Charlie's floor in the brain and 25 per cent of the net selling price. Compute the minimum price that clears it after all costs in `landed-cost.json`, recomputing the platform and payment fees at each price.
3. Read the market range from `pricing-research.md`. If the market median is below the minimum price, set `verdict` to `reprice-or-drop` and say which cost line is the problem.
4. Build the price ladder: entry (just above the minimum), standard (near the market median) and premium (only if a feature or pack size supports it). Show for each the price including VAT, margin per unit, margin per cent and the new `break_even_cpa`. Use plain price points (for example 19.99), consistently.
5. Design 2 to 4 offers. Each must show its own margin and must not drop the net margin below the floor: a multi-buy or bundle that raises average order value, a launch price for the first 14 days with an end date, free delivery above a threshold set from the average order value, and a creator or affiliate sample budget if `affiliate-and-creator-programme` applies.
6. Check the law and the platforms: the price shown includes VAT; a "was" price must be a genuine price the product was sold at recently (Price Marking Order and CMA pricing guidance, DMCC Act 2024 on drip pricing); no countdown that resets; no fake scarcity; the delivery cost shown before payment. Check each channel's promotions rules for allowed discount types.
7. Rank the options and recommend one. Give a plain reason with the numbers.
8. Write the files and set this job to `review` in `board.json` for Charlie's approval.

## Output
- `ventures/<slug>/commerce/pricing.json`: `{venture, date, product_id, margin_floor, min_price_gbp, ladder: [{tier, price_gbp, margin_per_unit, margin_pct, break_even_cpa}], offers: [{id, type, price_gbp, starts, ends, margin_per_unit, passes_floor, channels}], recommended, verdict, provisional, checks}`.
- `ventures/<slug>/commerce/pricing.md`: the same as a table with the recommendation and its reason. Read next by `catalogue-sync` and the launch ad brief.

## The ladder
- Human-led: Charlie sets prices from his own sums.
- Human-assisted: the default. The job proposes and checks; Charlie approves any price.
- Fully autonomous: not offered. Price changes are Charlie's.

## The human
What stays with Charlie: approving every price, every discount and every offer, and the decision to run a launch price.

## Tools
Free first. Gemini 2.5 Flash or Groq to read the market range and word the offers; code to compute margins; Firecrawl free tier (500 credits as of Oct 2026, check the limit) to read the platforms' promotion rules. No paid repricing tools.

## Build notes
- All arithmetic in code; the model never does the sums.
- An offer that fails the floor is listed as `rejected` with its margin, not removed silently.
- Tests offline: fixtures for a price below the floor, a bundle that passes, and a market median under the minimum price.
- GitHub implementation: `run.py` beside this file (jobkit).
