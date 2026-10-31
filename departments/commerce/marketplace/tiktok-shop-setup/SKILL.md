---
name: tiktok-shop-setup
title: TikTok Shop Setup
department: commerce
function: marketplace
autonomy: assisted
stage: build
builds_on: [marketplace-compliance]
breaks_into: [read-onboarding-rules, prepare-documents, fill-settings-sheet, write-checklist]
replaces: "an ecommerce consultant's marketplace onboarding service"
runs_on: github
status: ready
---

# TikTok Shop Setup

The checklist and settings to open and configure a TikTok Shop or a store on another marketplace; Charlie signs up and pays nothing before revenue.

Produces a checklist per channel and a sheet of the values to enter. It never creates an account, enters a password or a payment detail.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints (free tools only; no card on file; nothing paid before revenue)
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof (trading name, seller identity, price band)

## Inputs
- `ventures/<slug>/idea.json`: `kind` and `channels`. TikTok Shop UK is covered when kind is tiktok-shop or channels name it; Shopify and Amazon UK are added when channels name them.
- `ventures/<slug>/commerce/compliance.md`: the flag, the category rules, the documents needed.
- `ventures/<slug>/commerce/landed-cost.json` and `pricing.json`: prices and fees.
- `ventures/<slug>/commerce/suppliers.json`: dispatch times, return address, warehouse details.
- `ventures/<slug>/commerce/listings.json` and `catalogue.json` if they exist.
- Public pages: the TikTok Shop UK seller help centre, Shopify help centre, Amazon UK seller help pages and fee pages.

## Steps
1. Read `idea.json`; stop with a `skipped` line if the kind is not a commerce kind. Read the flag in `compliance.md`: if `FLAG: stop`, write only a note saying setup waits and why, and stop.
2. For each channel, read the current onboarding and fee pages. Record each requirement with its URL and the date read; check the limits and fees each run, as they change.
3. Build the TikTok Shop UK checklist: eligibility (UK seller, business type), the account type Charlie chooses (sole trader or limited company, see `entity-and-structure` if a company is considered), identity and business documents, a UK address and return address, bank account for payouts, VAT number if registered, product category and any category approval, brand authorisation if the product carries a brand, shipping template (handling time from the supplier lead time, carrier, delivery fee), returns policy that matches `returns-and-refunds`, first product listing fields, product video, affiliate settings left off until `affiliate-and-creator-programme` is approved, and the fees page (referral fee, payment fee, any monthly cost).
4. Add the equivalent for each other named channel. Shopify: plan and trial terms, domain, store policies pages, shipping zones, tax and VAT settings, payment provider onboarding, the legal pages from `clear/`, channel connection. Amazon UK: seller plan (compare the per-sale and monthly options on the plans page and note which has no fee before the first sale), identity verification, category approval, listing fields, fulfilment method, product safety documents.
5. Write the settings sheet: every value Charlie will type or select, with the figure from the brain or another file next to it (trading name, shipping template, dispatch days, return window, price, VAT status), so nothing is invented at the keyboard.
6. Order the checklist: what to prepare now (documents, photographs), what Charlie does in the seller centre, what to check before the first listing goes live, what to do after the first order. Mark each step `charlie`.
7. Add a money gate: list every step that could cost money (plan fees, a deposit or registration fee, a paid verification) and mark it `stop and ask`. Nothing on the list is done before Charlie approves it in `budget.json`.
8. Write the files and set this job to `review` in `board.json`.

## Output
- `ventures/<slug>/commerce/setup/<channel>-checklist.md`: ordered steps with a checkbox, owner, source URL and date.
- `ventures/<slug>/commerce/setup/settings.json`: `{channel: {setting: {value, source}}}`. The cost-bearing steps are listed at the top of each checklist.

## The ladder
- Human-led: Charlie follows the platform's own wizard.
- Human-assisted: the default. The job prepares the checklist and values; Charlie signs up and enters everything.
- Fully autonomous: not offered. Opening an account is Charlie's, with his identity and his bank details.

## The human
What stays with Charlie: creating each account, identity and bank details, accepting terms, paying any fee, and connecting the shop to `catalogue-sync` uploads.

## Tools
Free first. Firecrawl free tier (500 credits as of Oct 2026, check the limit) to read the seller help centres; Gemini 2.5 Flash or Groq to turn them into a checklist. No paid onboarding services.

## Build notes
- The help centres change often; every step carries its source URL and the date read.
- Never put credentials, identity numbers or bank details in any file.
- Tests offline: fixtures for a tiktok-shop venture, one with Shopify and Amazon added, and a stop flag.
