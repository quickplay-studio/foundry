---
name: affiliate-and-creator-programme
title: Affiliate and Creator Programme
department: commerce
function: marketplace
autonomy: assisted
stage: launch
builds_on: [product-selection, listing-optimisation]
breaks_into: [set-commission-ceiling, define-sample-offer, build-creator-list, draft-outreach]
replaces: "an influencer marketing agency or a paid creator discovery tool"
runs_on: github
status: ready
---

# Affiliate and Creator Programme

Commission rates, sample offers and outreach lists for creators who could sell the product; Charlie approves commissions.

Produces a commission proposal, a sample offer, a creator list and outreach drafts. It sends nothing and sets no commission.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints (no unsolicited email outside the law; Charlie approves every budget line)
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof (who buys, the niche, the proof points)

## Inputs
- `ventures/<slug>/idea.json`: `kind` and `channels`.
- `ventures/<slug>/commerce/landed-cost.json`: `margin_per_unit`, `break_even_cpa`, `target_cpa`, unit cost and shipping.
- `ventures/<slug>/commerce/pricing.json`: the approved price.
- `ventures/<slug>/commerce/listings.json`: the product claims creators may repeat.
- `ventures/<slug>/commerce/data/creators.csv` (optional): creators Charlie exports or notes from TikTok's creator marketplace or his own feed: `handle,platform,followers,niche,url,contact_route`.
- Public pages: the channel's affiliate programme and commission rules, public creator pages the site's terms allow.

## Steps
1. Read `idea.json`; stop with a `skipped` line if the kind is not a commerce kind. Stop with a note if `landed-cost.json` is missing or its margin is not positive.
2. Set the commission ceiling. A creator sale replaces an ad sale, so the most the venture can pay per sale is `break_even_cpa`. Express it as a percentage of the net price. Propose three tiers: open collaboration (a rate near 40 per cent of the ceiling), targeted creators (about 60 per cent) and top performers (up to 80 per cent after proven sales). Show the margin left at each. Read the channel's own minimum and maximum commission from its help page and keep inside them.
3. Define the sample offer: how many units, the cost to the venture (unit cost plus shipping), and the rule for who qualifies (public posting history in the niche, an audience that matches the buyer, no obvious engagement buying). Cap total sample spend at the figure in `budget.json`; if none is set, propose a figure and mark it for approval.
4. Build the creator list of 30 to 60 candidates from `creators.csv` and from public pages that the site's terms allow reading. For each: handle, platform, followers, niche fit, recent content in the niche, an engagement estimate from the visible likes and comments, and the contact route (in-platform invitation, a business email the creator publishes for collaborations, or an agent). Mark any with a sign of bought followers or an unrelated audience as `excluded`.
5. Write the outreach drafts in the house voice: short, say the product, the commission and the sample in the first two lines, no pressure, an easy no. Use the platform's invitation or message where it exists. Do not email individuals who have not published a contact route for collaborations; bulk or automated sending is not part of this job (PECR).
6. Add the rules creators must follow, for the brief: clear disclosure of gifted products and paid or commission-based posts (ASA and CAP Code, CMA guidance; the platform's own branded content toggle), only claims already in `listings.json`, no fake or incentivised reviews (DMCC Act 2024), no medical claims.
7. Add a tracking plan: a unique code or link per creator or the platform's own attribution, and what counts as a sale (after the return window, so refunded orders do not earn commission).
8. Write the files and set this job to `review`; Charlie approves rates, the sample spend and the list.

## Output
- `ventures/<slug>/commerce/creators/programme.md`: the commission tiers with margin at each, the sample offer, the rules and the tracking plan.
- `ventures/<slug>/commerce/creators/outreach-list.csv`: `handle,platform,followers,fit_score,contact_route,status,notes`, status starting at `proposed`.
- `ventures/<slug>/commerce/creators/messages.md`: outreach drafts and follow-ups, all marked draft.

## The ladder
- Human-led: Charlie finds creators and sets terms himself.
- Human-assisted: the default. The job proposes terms and a list; Charlie approves, invites and ships samples.
- Fully autonomous: not offered. Commission and samples spend Charlie's money.

## The human
What stays with Charlie: setting every commission in the channel's seller centre, ordering and sending samples, sending each message, and any payment to a creator.

## Tools
Free first. Gemini 2.5 Flash or Groq to score fit and draft messages; Firecrawl free tier (500 credits as of Oct 2026, check the limit) or Apify free monthly credit for public pages the terms allow; Charlie's own creator marketplace exports. No paid creator databases.

## Build notes
- Commission arithmetic in code, half-up rounding.
- Creators' personal data stays in the private repo; no lists in public issues.
- Tests offline: fixtures for a healthy margin, a margin too thin for any commission, and a creator list with bought-follower signs.
