---
name: platform-and-ad-compliance
title: Platform and Ad Compliance
department: legal
function: compliance
autonomy: solo
stage: launch
builds_on: []
breaks_into: [collect-launch-assets, check-store-policies, check-ad-rules, write-fix-list]
replaces: "a compliance review of store listings and ads by an agency or solicitor"
runs_on: github
status: ready
---

# Platform and Ad Compliance

App store, ad platform and UK advertising rules checked before anything is submitted or spent.

Nothing is submitted to a store or put in front of an ad platform until this job says clear or Charlie overrides a caution.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints (ad spend only with Charlie's approval)
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof
- `ventures/<slug>/clear/regulatory-screen.json` and `consumer-law-check.md`, if present

## Inputs
- Draft launch assets listed in `board.json`: store listing text and screenshots, landing page copy, ad creative and brief, captions, influencer briefs, review prompts.
- Which stores and ad platforms are planned, and the target countries.

## Steps
1. Collect each asset and the claim it makes: price, discount, "free", results, testimonials, health or money claims, comparisons, age targeting.
2. Apple App Store Review Guidelines: read the current text with Firecrawl. Check safety and user-generated content rules, in-app purchase rules for digital goods and subscriptions, subscription disclosure, privacy policy link and data collection labels, account deletion in app, sign-in options, kids category limits, and no misleading metadata.
3. Google Play Developer Policy Center: check User Data and the Data safety form, Payments and subscriptions, Families policy if children may use it, deceptive behaviour, and metadata and listing rules.
4. UK advertising: ASA and CAP Code for non-broadcast ads. Check misleading advertising (section 3), recognition of marketing and influencer disclosure (labels such as #ad), harm and offence, children, privacy and database practice, promotional marketing, distance selling, and the specific sections for health, financial products and gambling if the screen flagged them. Check substantiation: every claim needs evidence on file.
5. Pricing and reviews: the Digital Markets, Competition and Consumers Act 2024 rules on drip pricing, fake or incentivised reviews and subscription traps; CMA guidance on pricing and online reviews. Total price must be shown up front; no invented testimonials; no fake urgency.
6. Ad platforms: Meta Advertising Standards and Google Ads policies, including personalised ads limits, restricted categories (financial services need verification, health, gambling, age-restricted), prohibited claims, landing page matching, and sensitive targeting limits. Check TikTok or other platforms only if planned.
7. Marketing law: UK GDPR and PECR for email and SMS (consent, unsubscribe), cookies on landing pages.
8. Write a fix list: asset, rule, quote of the claim, required change. Flag stop for any asset that would be rejected or breaks the CAP Code; caution for unsubstantiated or unclear claims; else clear.

## Output
- `ventures/<slug>/clear/platform-and-ad-compliance.md`: first line `FLAG: clear`, `FLAG: caution` or `FLAG: stop`, the reason, then the fix list table, per-platform status (Apple, Google Play, Meta, Google Ads) and sources read with dates.
- `ventures/<slug>/clear/platform-and-ad-compliance.json`: rows for the ad-creative and publishing jobs to read.
- Not legal advice. Drafts are checked by Charlie or a solicitor before use.

## The ladder
- Human-led: Charlie reads each policy before submitting.
- Human-assisted: the job produces the fix list; Charlie approves the final assets and the budget.
- Fully autonomous: the default for the check. It cannot submit, publish or spend; Charlie pays the platform and records the campaign id.

## The human
What stays with Charlie: the approval of every ad budget line, store developer accounts and their fees (Apple and Google both charge to publish; check current amounts, nothing is paid before revenue), answering a store rejection, and a solicitor or ASA Copy Advice for a borderline claim.

## Tools
Free first. Firecrawl free tier (500 credits as of Oct 2026, check the limit) for policy pages; Gemini 2.5 Flash or Groq to test each claim against a checklist. The ASA's free Copy Advice service is a human option. No paid tools.

## Build notes
- Policy pages change; read them fresh each run and record the date. Keep a checklist in code, not in the prompt, so results are repeatable.
- Re-run on every new or edited asset. A failed read is `caution`, not `clear`.
- Tests offline: fixtures with a clean listing, an unsupported "best" claim, and an undisclosed influencer post.
- GitHub implementation: `run.py` beside this file (jobkit).
