---
name: nda-and-agreements
title: NDA and Agreements
department: legal
function: documents
autonomy: assisted
stage: none
builds_on: []
breaks_into: [pick-template, fill-parties-and-terms, check-fit, write-cover-note]
replaces: "a solicitor drafting a one-off NDA, contractor or referral agreement, typically a hundred pounds or more each"
runs_on: claude-code
status: ready
---

# NDA and Agreements

NDAs, contractor and referral agreements from templates.

Short agreements for the small, frequent cases: sharing an idea, hiring a freelancer, paying for referrals.

## Reads from the brain
- `brain/company.md`: voice (plain, short sentences, no hype), offers, constraints (no unsolicited email, no buying lists)
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof (what is confidential, who is being engaged)
- `ventures/<slug>/clear/entity-and-structure.md`, if the structure has been chosen

## Inputs
- The type: one-way NDA, mutual NDA, contractor agreement, or referral agreement.
- The other party's name, role and purpose; what is shared or done; the duration; the fee or commission; the owner of the output. Unknown details stay as blanks.
- Our party: owner name or company from `entity-and-structure`; if there is no entity yet, Charlie in his own name.

## Steps
1. Check that an NDA is needed. For early idea validation, publicly available information needs no NDA; say so. Investors and large firms often refuse to sign one; note it.
2. Pick the template from the clause library at `departments/legal/documents/contract-drafting/clauses.md`. If the clause library is missing, draft from the headings below and mark everything `unreviewed`.
3. NDA headings: parties; what counts as confidential and what does not (public, already known, independently developed, required by law); permitted use; duration (a fixed term, for example two to five years, plus trade secrets for as long as they stay secret); return or deletion; no licence granted; remedies; governing law. Use the UK IPO guidance on keeping ideas confidential (gov.uk) for the background and keep the NDA mutual unless there is a reason.
4. Contractor agreement headings: services and deliverables; fees and payment timing (see the Late Payment of Commercial Debts (Interest) Act 1998); independent contractor status; IP assignment and moral rights waiver in writing signed by the contractor (Copyright, Designs and Patents Act 1988 section 90(3) and 87); confidentiality; data protection if personal data is touched; ending the work; liability. Check status with the HMRC "Check employment status for tax" tool; flag if the work looks like employment (IR35 for a company contractor, employment rights for an individual).
5. Referral agreement headings: what counts as a referral; commission and when it is due; no promises made on our behalf; honesty and disclosure of the relationship (CAP Code and the Digital Markets, Competition and Consumers Act 2024 on undisclosed incentives and fake reviews); data protection and consent for any contact details passed (UK GDPR and PECR); termination. If the referral is for a regulated financial product, stop and tell `regulatory-screen`; introducing customers to FCA-regulated products is itself regulated.
6. Check fit: no clause that restrains work beyond what is reasonable; for contractors no restriction that stops them earning a living; no gagging clause that stops reporting wrongdoing (Public Interest Disclosure Act 1998 protects it).
7. Write a one-page cover note in plain English: what the document does, what the other side must provide, how to sign (a simple agreement can be signed electronically; ask whether a deed is needed), and what to keep.

## Output
- `ventures/<slug>/clear/agreements/<type>-<counterparty-slug>.md`: the draft with blanks in square brackets, plus `<type>-<counterparty-slug>-note.md`. Opened as a draft pull request. A register line is added to `ventures/<slug>/clear/agreements/register.md` (party, type, date sent, date signed, expiry, owner of originals).
- Not legal advice. Drafts are checked by Charlie or a solicitor before use.

## The ladder
- Human-led: a solicitor drafts from the facts.
- Human-assisted: the default. The job fills the template and flags problems; Charlie checks it, sends it and keeps the signed copy.
- Fully autonomous: only the expiry reminder from the register, raised in `board.json`. The job never sends or signs.

## The human
What stays with Charlie: whether to share anything at all, the commercial terms, who signs, sending the document, and a solicitor for anything with a large fee, a long restriction or a regulated referral.

## Tools
Free first. A Claude Code session (Sonnet) for tailoring. Firecrawl free tier (500 credits as of Oct 2026, check the limit) to read gov.uk guidance. Gemini 2.5 Flash or Groq on GitHub for the fit check using placeholders, never real names or confidential facts (free tiers may use inputs for training).

## Build notes
- Template text comes from the contract-drafting clause library so one solicitor review covers all of them.
- Register is plain markdown so the human can edit it; the job only appends.
- Tests offline: fixture requests for each type, assert blanks marked, no dash characters, and the regulated referral case halts.
