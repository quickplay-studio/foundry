---
name: listing-optimisation
title: Listing Optimisation
department: commerce
function: listings
autonomy: solo
stage: launch
builds_on: [product-selection, landing-page-copy]
breaks_into: [read-channel-rules, find-keywords, draft-listing, check-limits-and-claims]
replaces: "a listing copywriter or a paid keyword and listing tool"
runs_on: github
status: ready
---

# Listing Optimisation

Titles, bullets, descriptions and keywords per marketplace, in the house voice, within each platform's rules.

Produces ready-to-paste listing copy for each channel the venture sells on. It publishes nothing.

## Reads from the brain
- `brain/company.md`: voice (plain, direct, short sentences, no hype, no exclamation marks), offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof (what the product does, who for, the price, the proof points)

## Inputs
- `ventures/<slug>/idea.json`: `kind` and `channels`.
- `ventures/<slug>/commerce/shortlist.json`: the picked product, its complaint themes and competitor listings.
- `ventures/<slug>/launch/landing-page.md`: the landing page copy, for claims and tone.
- `ventures/<slug>/commerce/compliance.md`: required warnings, banned claims and category rules.
- `ventures/<slug>/commerce/landed-cost.json`: the selling price.
- Public pages: the channel's listing style guide, top competing listings and their search suggestions.

## Steps
1. Read `idea.json`; stop with a `skipped` line if the kind is not a commerce kind. Take the channel list (default: the primary channel for the kind).
2. For each channel, read the current listing rules from its seller help centre: title length, banned words, image and bullet rules, prohibited claims. Record the limits and the date read. Check the limit each run, as they change.
3. Build the keyword set: the product's search terms from competing listings and search suggestions, ranked by how often they appear in the leading titles. Keep 10 to 20 terms, with one primary term per listing.
4. Draft per channel, using only facts from the brain, the landing page and the supplier data:
   - Title: primary term first, then the key attribute, size or count, and a differentiator. No capital-letter shouting, no promotional words such as "best" or "sale" where the channel bans them.
   - Five bullets on Amazon style channels: one benefit each, with the fact behind it.
   - Description: the price and what it does in the first two lines; short sentences; delivery and returns in plain words.
   - Search terms or tags field: remaining keywords, no repeats of the title.
   - TikTok Shop: a short title, a video-led description and the product attributes the category requires.
5. Answer the top complaint themes from `shortlist.json` honestly in the copy (size guide, what is not included). Do not claim a benefit that the sample check or the supplier data does not support.
6. Check every draft: within character limits, no medical or unsupported claims, no competitor brand names, no "free" claims that do not hold, every compliance warning present, UK spelling, no dashes, no exclamation marks.
7. Write one variant per channel and one alternate title for testing. Flag any listing whose category needs approval.

## Output
- `ventures/<slug>/commerce/listings.json`: `{venture, date, product_id, channels: [{channel, rules_read: {url, date}, title, alt_title, bullets, description, search_terms, attributes, warnings, checks: {title_len, limit, passed}}]}`.
- `ventures/<slug>/commerce/listings.md`: the same as copy-and-paste text. Read next by `catalogue-sync`, `product-photography-brief` and the ad brief.

## The ladder
- Human-led: Charlie writes the copy; the job only checks the limits.
- Human-assisted: Charlie edits the drafts before upload.
- Fully autonomous: the default for drafting. Uploading to a live shop is Charlie's.

## The human
What stays with Charlie: reading the copy once, uploading it, and any claim about what the product does.

## Tools
Free first. Firecrawl free tier (500 credits as of Oct 2026, check the limit) and Apify free monthly credit to read competing listings and the seller help centres; Gemini 2.5 Flash or Groq to draft; code for the length and banned-word checks. No paid keyword tools.

## Build notes
- Limits come from the page read that run, not from memory; store the value and the date beside it.
- Code, not the model, enforces limits and the banned-word list.
- Tests offline: fixtures for a title over the limit, a missing warning, and a channel with no help-centre page.
