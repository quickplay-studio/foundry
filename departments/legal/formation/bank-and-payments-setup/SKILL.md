---
name: bank-and-payments-setup
title: Bank and Payments Setup
department: legal
function: formation
autonomy: human
stage: clear
builds_on: [entity-and-structure]
breaks_into: [list-payment-routes, compare-costs-and-terms, check-regulatory-fit, write-brief]
replaces: "a banking and payments set-up consultation, often free from a bank adviser but biased to one provider"
runs_on: github
status: ready
---

# Bank and Payments Setup

Which account and payment provider fit the venture; you open them.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints (free tools only, no card on file, nothing pay-as-you-go until revenue)
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof (price, billing period, who pays, countries)
- `ventures/<slug>/clear/entity-and-structure.md`: who will own the account

## Inputs
- The chosen structure and the owner's legal name.
- How the product takes money: app store in-app purchase, web checkout, direct debit, invoice, or none yet; one-off or recurring; expected price and volume; countries.
- Whether the product holds or moves other people's money (a marketplace, wallet or split payment).

## Steps
1. Decide whether money handling is regulated. If the venture holds, pools or transfers customer money, that is a payment service or e-money activity under the Payment Services Regulations 2017 and Electronic Money Regulations 2011 and needs FCA authorisation or a regulated partner; set the flag stop and send to `regulatory-screen`. Check the FCA Register for any named provider.
2. List the payment routes that fit: app store billing (Apple and Google take a commission on digital goods and offer reduced rates for small developers; read both current rate pages), a payment service provider for web card payments (for example Stripe or PayPal), direct debit for recurring payments (for example GoCardless), and a merchant of record service that also accounts for VAT (for example Paddle). These are candidates to verify, not a recommendation.
3. For each candidate read the current pricing and terms page with Firecrawl. Record: set-up cost, monthly fee, fee per transaction (all must be revenue-only, with no card on file, no subscription and no up-front payment, to meet the rule), payout time, refund and chargeback handling, VAT handling, UK sole trader eligibility, prohibited business types, and where funds are held.
4. Business bank account criteria: eligible for the chosen structure, free tier or free first period (read the current terms), FSCS protection (read the current limit on the FSCS site) or safeguarding arrangements for e-money, ability to receive from the chosen provider, and bank terms on business use of a personal account. Do not recommend a bank; list the criteria and 2 to 3 options that match, with sources.
5. Note identity checks that Charlie must pass (proof of identity, address, a business description). He opens everything; the job never creates an account or enters credentials.
6. Note costs that cannot be avoided: Apple's annual Developer Program fee, Google Play's one-off registration fee, and a domain name. Check the amounts; Charlie approves each before any venture spends.
7. Flag: stop if the venture is a regulated payment activity; caution if the only workable route has a monthly or up-front cost; else clear.
8. Write a one-page brief: recommended route, alternative, true cost at the expected volume, what Charlie opens first, and what stays on hold until revenue. Then stop.

## Output
- `ventures/<slug>/clear/bank-and-payments.md`: first line `FLAG: clear`, `FLAG: caution` or `FLAG: stop`, then the brief, a comparison table (provider, set-up, monthly, per transaction, payout, VAT, eligible), the cost list needing Charlie's approval, and sources read with dates.
- Not legal advice. Drafts are checked by Charlie or a solicitor before use.

## The ladder
- Human-led: Charlie compares providers and opens accounts himself.
- Human-assisted: the default. The job prepares the brief and the numbers; Charlie opens the accounts.
- Fully autonomous: not allowed. No agent holds a card, a login or a payout account; the job only re-reads fees quarterly and raises caution on a change.

## The human
What stays with Charlie: choosing, opening and verifying every account, any fee, the first payout, and an accountant or solicitor if funds are held for others.

## Tools
Free first. Firecrawl free tier (500 credits as of Oct 2026, check the limit) to read pricing, terms, FCA Register and FSCS pages; Gemini 2.5 Flash or Groq to extract fee tables; a small Python script for the cost at volume. No accounts are created.

## Build notes
- Fees change often; the fee table is always read fresh and dated.
- Writes the chosen providers to `board.json` only after Charlie records them; `payment-tracking` reads this.
- Tests offline with saved pricing page fixtures.
