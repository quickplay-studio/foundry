---
name: terms-of-service
title: Terms of Service
department: legal
function: documents
autonomy: assisted
stage: clear
builds_on: [entity-and-structure, consumer-law-check]
breaks_into: [gather-facts, assemble-clauses, tailor-to-product, check-against-rules]
replaces: "a solicitor drafting website or app terms, typically several hundred pounds"
runs_on: claude-code
status: ready
---

# Terms of Service

Draft the terms for the product from the brain's offer and the market's rules.

A draft, in plain English, that a solicitor can review quickly before the product takes money.

## Reads from the brain
- `brain/company.md`: voice (plain, short sentences, no hype), offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof (the offer, price and who pays)
- `ventures/<slug>/clear/entity-and-structure.md`, `consumer-law-check.md`, `regulatory-screen.json`, and `data-protection.md` if present

## Inputs
- The trading party: owner name or company name and number, address for notices, contact email. Missing details stay as marked blanks for Charlie.
- The offer: what is sold, price, billing period, trial, cancellation and refund choices, customer type (consumer, business or both), countries.
- The rules list from `consumer-law-check` and the flag from `regulatory-screen`. Stop and report if the screen is stop.

## Steps
1. Read the inputs. If `consumer-law-check` or `entity-and-structure` is missing, write a skipped line in `board.json` and end.
2. Check the clause library at `departments/legal/documents/contract-drafting/clauses.md`. Reuse clauses marked reviewed; if the file does not exist yet, draft without it. Never copy text from another company's terms.
3. Draft in this order: who we are and how to contact us; what the service is and what it is not (no advice where the screen said so); account and age limit (13 in the UK, higher if the screen says); price, payment and renewal stated before purchase; the 14-day cancellation right and the digital content exception wording from the Consumer Contracts Regulations 2013; refunds and what to do if it does not work (Consumer Rights Act 2015 remedies); acceptable use; user content and our licence to it; our intellectual property; availability and changes (with a valid reason for change, as the grey list requires); limits on liability; ending the contract; complaints and ADR statement; governing law (England and Wales for UK consumers, who keep the right to their local courts); contact for legal notices.
4. Never exclude what the law will not let you: liability for death or personal injury by negligence (Unfair Contract Terms Act 1977 section 2), consumer statutory rights (Consumer Rights Act 2015 sections 31 and 47), or fraud. Terms that are unfair or non-transparent are not binding on consumers (Part 2 of the Act).
5. For business customers add the reasonableness test (Unfair Contract Terms Act 1977), but defer full B2B terms to `contract-drafting`.
6. Add the information required on a website under the Electronic Commerce (EC Directive) Regulations 2002 and, for a company, the Companies Act 2006 disclosures.
7. Link the privacy policy and cookie notice; do not repeat them.
8. Run a self-check: each rule in the `consumer-law-check` list maps to a clause; mark any unmatched rule. Read the draft aloud for plain English; no clause longer than 80 words if it can be split.
9. Write a short review note listing choices made, assumptions, blanks, and questions for the solicitor.

## Output
- `ventures/<slug>/clear/terms-of-service.md`: the draft terms with blanks in square brackets, and `ventures/<slug>/clear/terms-review-note.md` with the mapping to rules and open questions. Opened as a draft pull request; `board.json` set to waiting for review.
- Not legal advice. Drafts are checked by Charlie or a solicitor before use.

## The ladder
- Human-led: a solicitor drafts the terms; the job supplies the offer and the rules list.
- Human-assisted: the default. The job drafts and self-checks; Charlie fills blanks and a solicitor reviews before the first payment.
- Fully autonomous: not allowed for live terms. The job may regenerate the draft when the offer or price changes, again as a pull request.

## The human
What stays with Charlie: filling in blanks, choosing refund and cancellation terms, publishing the terms, the solicitor review before taking money, and re-approving after any change in the offer.

## Tools
Free first. A Claude Code session (Sonnet; Opus as advisor only if two rules conflict) because drafting needs judgement. Gemini 2.5 Flash or Groq can run the clause-to-rule check on GitHub. Firecrawl free tier (500 credits as of Oct 2026, check the limit) to read legislation.gov.uk when a section needs confirming.

## Build notes
- Keep the draft under about 2,000 words for a small consumer product. Use headings the customer can scan.
- Use only the owner name and details from `entity-and-structure`; never add personal details.
- Tests offline: fixture brains for a consumer subscription and a free app; check every rule has a clause, no dash characters, and blanks are marked.
