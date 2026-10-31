---
name: marketplace-compliance
title: Marketplace Compliance
department: commerce
function: marketplace
autonomy: solo
stage: clear
builds_on: [consumer-law-check]
breaks_into: [classify-product, check-uk-product-safety, check-labelling, check-marketplace-policies]
replaces: "a product compliance consultant's pre-listing review"
runs_on: github
status: ready
---

# Marketplace Compliance

Product safety, labelling, restricted categories and marketplace policies checked before anything is listed.

Produces a compliance note for the picked product. It is the gate before samples, listings and shop setup. Not legal advice.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints (nothing regulated without a human and a solicitor: finance, health, children, gambling)
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof (what the product is, who uses it, health or child angle)

## Inputs
- `ventures/<slug>/idea.json`: `kind` and `channels`.
- `ventures/<slug>/commerce/shortlist.json`: the picked product (or the top one, marked provisional).
- `ventures/<slug>/commerce/suppliers.json`: country of origin, certificates claimed, importer details.
- `ventures/<slug>/clear/consumer-law-check.md`: the consumer rules already listed.
- Public pages: gov.uk product safety guidance, legislation.gov.uk, the TikTok Shop and Amazon seller help centres (prohibited and restricted products, category approval, listing policies).

## Steps
1. Read `idea.json`; stop with a `skipped` line if the kind is not shop, tiktok-shop or dropshipping. List the channels (default tiktok-shop for kind tiktok-shop).
2. Classify the product: electrical or battery powered, toy or childcare, cosmetic or personal care, food or drink, supplement or health claim, textile or clothing, pet, medical or measuring device, knife or age-restricted, general consumer good. A product can sit in several classes.
3. UK product safety, from gov.uk and legislation.gov.uk, with the date read: the General Product Safety Regulations 2005 (safe product, traceability, recall duty); the Product Safety and Metrology regime (the Product Regulation and Metrology Act 2025 and its regulations; check what has commenced and what it asks of online sellers and marketplaces); and the product-specific rules for each class, for example the Electrical Equipment (Safety) Regulations 2016 and UK plug rules, the Toys (Safety) Regulations 2011, the UK Cosmetics Regulation, food labelling and allergen rules, textile fibre labelling.
4. Marking: state whether UKCA or CE marking applies for Great Britain, and what applies in Northern Ireland, from the gov.uk guidance for that product class. Record the assessment route, the UK responsible person or importer needed, and the evidence a supplier must provide (test reports, declaration of conformity). A certificate claimed on a supplier page is `claimed` until Charlie holds a copy.
5. Labelling and documents: product name, importer or responsible person name and UK address, batch or type number, warnings and age grading, instructions in English, country of origin where required, WEEE and batteries and packaging producer obligations if they apply.
6. Claims: no health, medical or safety claim without evidence; no "eco" or "natural" claim without support (CMA Green Claims Code); no brand, licence or lookalike risk.
7. Marketplace policies: read each channel's current prohibited and restricted products pages and listing policies. Mark each as `allowed`, `needs-approval`, `restricted` or `prohibited`, with the URL and date. Include seller identity and returns requirements the channel sets.
8. Set the flag. `stop`: the product is prohibited by law or a channel, it is a health, supplement, medical, finance, gambling or children's product that the company rule sends to a human and solicitor and no sign-off is recorded in the brain, or a required marking cannot be obtained. `caution`: a restricted class where certificates, a responsible person or channel approval are not yet in hand. `clear`: nothing restricted and the evidence is in hand.
9. Write the note and a document request list for the supplier. Update `board.json`: `stop` blocks `sample-and-quality-check` and `tiktok-shop-setup`.

## Output
- `ventures/<slug>/commerce/compliance.md`: first line `FLAG: clear`, `FLAG: caution` or `FLAG: stop`, then the product classes, the rules that apply and why, the markings and documents needed, labelling requirements, channel policy status per channel, open questions and sources with dates read.
- `ventures/<slug>/commerce/compliance.json`: `{flag, classes, rules: [{name, source, applies, evidence_needed, evidence_held}], channels: [{channel, status, url, date}], documents_to_request: []}`. Read next by `sample-and-quality-check`, `listing-optimisation` and `tiktok-shop-setup`.

## The ladder
- Human-led: Charlie reads gov.uk and the seller policies himself.
- Human-assisted: Charlie confirms the flag and asks a solicitor or Trading Standards about anything marked caution.
- Fully autonomous: the default for the first check and the re-check at each channel policy change. A `stop` is never overridden by an agent.

## The human
What stays with Charlie: overriding or accepting any flag, getting test reports and certificates, and a solicitor review for anything regulated.

## Tools
Free first. Firecrawl free tier (500 credits as of Oct 2026, check the limit) to read gov.uk, legislation.gov.uk and the seller help centres; Gemini 2.5 Flash or Groq to map the rules to the product; Charlie may also use the free Trading Standards business advice. No paid compliance services.

## Build notes
- Rules and policy lists are read live each run with the date recorded, not taken from memory.
- Any doubt resolves to the stricter flag.
- Tests offline: fixtures for a plain homeware item (clear), a USB electrical (caution), a supplement (stop) and a page that cannot be read.
