---
name: consumer-law-check
title: Consumer Law Check
department: legal
function: compliance
autonomy: assisted
stage: clear
builds_on: []
breaks_into: [classify-the-contract, list-the-rules, check-pricing-and-renewals, write-rules-page]
replaces: "a consumer law review of terms and checkout flow by a solicitor"
runs_on: github
status: ready
---

# Consumer Law Check

Pricing, cancellation, refunds and subscription rules the product must follow.

Produces the one-page list of rules the product and the terms must meet. `terms-of-service` is written from it.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof (price, free trial, billing period, who pays)

## Inputs
- How the product is sold: one-off, subscription, free trial, freemium, in-app purchase, web checkout, physical goods; who the buyer is (consumer or business); countries sold to.
- The planned price, trial length, billing period, renewal and cancellation flow, refund idea.

## Steps
1. Classify the contract: digital content, digital service, goods or mixed. Consumers or business? Consumer rules do not apply to a pure business sale (then see `contract-drafting`). If both are possible, treat the consumer case as the default.
2. Consumer Rights Act 2015: digital content must be of satisfactory quality, fit for purpose and as described (sections 34 to 47), with remedies including repair, replacement and refund; these rights cannot be excluded. Check the unfair terms rules (Part 2): fairness test, the grey list, and plain intelligible wording.
3. Consumer Contracts (Information, Cancellation and Additional Charges) Regulations 2013: pre-contract information, 14-day cancellation for distance sales, how it works for digital content (right lost only after express consent and acknowledgement before download or streaming starts) and for services started during the cancellation period (proportionate payment). Specify the checkout wording and records to keep.
4. Digital Markets, Competition and Consumers Act 2024: ban on unfair commercial practices, drip pricing and fake reviews (CMA direct enforcement with fines up to 10% of global turnover since April 2025), and the new subscription contract regime. Check on gov.uk whether the subscription rules have commenced and their exact requirements (pre-contract information, reminder notices, easy exit, cooling off).
5. Pricing display: price including VAT shown up front, no hidden fees, free trial conversion stated plainly, renewal price and date stated before the customer pays, cancel as easily as sign up. Price Marking Order for any goods.
6. Trader information: Electronic Commerce (EC Directive) Regulations 2002 (name, address, email, company or VAT number where it applies) and, for a company, the Companies Act 2006 disclosure rules.
7. Redress: Alternative Dispute Resolution for Consumer Disputes Regulations 2015 (tell consumers whether you will use an ADR provider), refund timing (generally within 14 days of the cancellation), and complaints route.
8. Store overlap: note where Apple or Google handles payment, refunds and renewals so the product does not promise what the store controls.
9. Write the one-page rules list: rule, source, what the product must do, which screen or term it affects. Flag stop if the business model depends on something unlawful (hidden renewal, no cancel); caution for any open question; else clear.

## Output
- `ventures/<slug>/clear/consumer-law-check.md`: first line `FLAG: clear`, `FLAG: caution` or `FLAG: stop`, then the one-page rules list, a checkout and cancellation wording checklist, open questions, and sources read with dates.
- Not legal advice. Drafts are checked by Charlie or a solicitor before use.

## The ladder
- Human-led: Charlie reads the Act and Regulations and writes the rules list himself.
- Human-assisted: the default. The job drafts the list as a draft pull request; Charlie confirms the pricing and cancellation decisions.
- Fully autonomous: only a re-check of the live checkout copy against the list after launch.

## The human
What stays with Charlie: the price, the trial and refund policy, the cancellation flow, and a solicitor review of the terms before the product takes money.

## Tools
Free first. Firecrawl free tier (500 credits as of Oct 2026, check the limit) to read legislation.gov.uk, gov.uk and CMA guidance; Gemini 2.5 Flash or Groq to map rules to the product. No paid tools.

## Build notes
- Statute text is read from legislation.gov.uk, not from the model's memory. Record the date read.
- The subscription regime start date is uncertain; the job must read the current gov.uk position each run.
- Tests offline: fixtures for a one-off app, a monthly subscription with trial, and a B2B-only product.
- GitHub implementation: `run.py` beside this file (jobkit).
