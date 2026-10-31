---
name: contract-drafting
title: Contract Drafting
department: legal
function: documents
autonomy: assisted
stage: clear
builds_on: [entity-and-structure]
breaks_into: [pick-contract-type, assemble-from-clauses, tailor-terms, write-review-note]
replaces: "a solicitor drafting a services agreement and SLA, typically several hundred pounds each"
runs_on: claude-code
status: ready
---

# Contract Drafting

Services agreements and SLAs from a clause library.

For B2B ventures and contractors. Consumer terms belong to `terms-of-service`.

## Reads from the brain
- `brain/company.md`: voice (plain, short sentences, no hype), offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof (the service, the buyer, the price)
- `ventures/<slug>/clear/entity-and-structure.md`: the supplier party

## Inputs
- The deal: customer type and size, services, deliverables, price, payment terms, term and renewal, support and uptime promised, data handled, who owns the output.
- Supplier details from `entity-and-structure`. Customer details stay as blanks.
- A request for a services agreement, an SLA, or a contractor agreement.

## Steps
1. Pick the document: services agreement, SLA schedule, or contractor agreement (the contractor version carries the IP assignment used by `ip-assignment`).
2. Open the clause library at `departments/legal/documents/contract-drafting/clauses.md`. If it does not exist, create it with these headings, each clause tagged `unreviewed` or `reviewed` with a date and a note: definitions, services, fees and payment, term and termination, service levels, intellectual property, confidentiality, data protection, liability, force majeure, changes, notices, dispute resolution and governing law. Only clauses a solicitor has reviewed are marked `reviewed`.
3. Assemble the document from the library. Tailor the commercial terms from the deal facts. Never leave a clause the deal does not need.
4. Check the law the clauses depend on: Unfair Contract Terms Act 1977 (liability caps and exclusions must be reasonable in B2B; no exclusion for death or personal injury by negligence); Late Payment of Commercial Debts (Interest) Act 1998 (statutory interest and fixed recovery costs if no payment term is set; payment terms should be explicit); Consumer Rights Act 2015 if any consumer could be party; the rule against penalty clauses (service credits must be a price adjustment, not a punishment).
5. If the service processes the customer's personal data, add the UK GDPR Article 28 processor terms (subject matter, duration, instructions, security, sub-processors, deletion, audit) and cross-check against `data-protection`.
6. For contractors, check status for tax (HMRC "Check employment status for tax" tool) and flag if the work looks like employment. Add IP assignment, moral rights waiver and confidentiality; the assignment must be in writing and signed.
7. SLA: define uptime and response measures that the product can actually meet (from monitoring data if it exists), exclusions, service credits as the sole remedy, and the reporting method. Do not promise more than the stack delivers.
8. Write a review note: choices made, clauses unreviewed, blanks, and the three questions most useful for a solicitor.

## Output
- `ventures/<slug>/clear/contracts/<type>-<counterparty-slug>.md`: the draft agreement, with blanks in square brackets. Opened as a draft pull request.
- `ventures/<slug>/clear/contracts/<type>-review-note.md`: the review note.
- `departments/legal/documents/contract-drafting/clauses.md` updated when a better clause emerges (pull request only).
- Not legal advice. Drafts are checked by Charlie or a solicitor before use.

## The ladder
- Human-led: a solicitor drafts from the deal sheet.
- Human-assisted: the default. The job assembles and tailors; Charlie reads every clause and a solicitor reviews before any signature on a deal that matters.
- Fully autonomous: not allowed. Contracts bind Charlie or the company; the job never sends or signs.

## The human
What stays with Charlie: the commercial terms, who signs, sending the contract, negotiation, accepting any liability cap, and solicitor review before signing any contract with real value, a long term or unlimited liability.

## Tools
Free first. A Claude Code session (Sonnet; Opus as advisor for a liability or IP conflict) for drafting. Firecrawl free tier (500 credits as of Oct 2026, check the limit) to read legislation.gov.uk and gov.uk pages. Gemini 2.5 Flash or Groq for the clause completeness check on GitHub. No paid tools.

## Build notes
- The clause library is the asset: each approved clause is reused across ventures, so a solicitor reviewing the library once covers many contracts.
- Keep documents short: a services agreement for a small deal fits in two to four pages.
- Tests offline: assert required headings, blanks marked, no dash characters, and `unreviewed` clauses are listed in the review note.
