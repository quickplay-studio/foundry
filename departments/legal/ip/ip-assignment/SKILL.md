---
name: ip-assignment
title: IP Assignment
department: legal
function: ip
autonomy: assisted
stage: none
builds_on: [contract-drafting]
breaks_into: [inventory-assets, test-ownership, draft-assignment, update-register]
replaces: "a solicitor's IP ownership review and assignment deeds, usually a few hundred pounds per engagement"
runs_on: claude-code
status: ready
---

# IP Assignment

Make sure work done by contractors or tools is owned by the venture.

By default a freelancer owns the copyright in what they write, and a venture only owns it if a signed document says so.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof
- `ventures/<slug>/clear/entity-and-structure.md`: who the owner is (Charlie personally or a company)

## Inputs
- Every asset the venture uses: code, copy, design, logo, name, domain, app store account, data, prompts, AI-generated media.
- Who created each one and how: Charlie, a contractor, a friend, a stock source, an AI tool, an open source package.
- Any agreements already signed (from `clear/agreements/`).

## Steps
1. Build an inventory of assets and their creators from the repo, `brain.md` and Charlie's answers. One row per asset.
2. Test ownership for each row against the Copyright, Designs and Patents Act 1988. Author owns first (section 11); employees' work in the course of employment belongs to the employer; an assignment must be in writing and signed by the assignor (section 90(3)); moral rights need a written waiver (section 87). Commissioned unregistered designs belong to the designer unless assigned (Intellectual Property Act 2014 changed the old rule). Patents Act 1977 section 39 governs employee inventions.
3. Check the owner of each non-document asset: the domain registrant, the app store developer account, social handles, the trade mark applicant. These must be the venture's owner, not a contractor or friend.
4. Check the AI and tool terms: read the current terms of each generator or coding tool used (Firecrawl page read) for who owns output, commercial use limits and whether free-tier inputs can be used for training. UK law on copyright in computer-generated works is under review; see UK IPO guidance. Record the position and the date read.
5. Check Charlie's side: ask him to confirm the work was not made on an employer's time or equipment and that any employment-contract outside-interests clause is satisfied.
6. For every gap, draft the fix: a short IP assignment and moral rights waiver for a contractor (reuse the assignment clause from the `contract-drafting` clause library), a confirmatory assignment for work already done, a domain or account transfer note. Plain English, one page each.
7. Flag: stop if the core code, name or brand is owned by someone who has not assigned it; caution if only minor assets, AI output or account ownership are open; else clear.

## Output
- `ventures/<slug>/clear/ip-register.md`: first line `FLAG: clear`, `FLAG: caution` or `FLAG: stop`, then the register table (asset, creator, basis of ownership, document, gap, action) and sources read with dates.
- `ventures/<slug>/clear/agreements/ip-assignment-<creator-slug>.md`: one draft per gap, left as a draft pull request.
- Not legal advice. Drafts are checked by Charlie or a solicitor before use.

## The ladder
- Human-led: Charlie or a solicitor writes each assignment from scratch.
- Human-assisted: the default. The job builds the register and drafts the fixes; Charlie sends and signs them (electronic signature is valid for a simple assignment; a deed needs witnessing).
- Fully autonomous: the register only. Drafting and sending stay with a human because the other party has to sign.

## The human
What stays with Charlie: contacting the contractor, getting the signature, paying any consideration, deciding what to do if a creator refuses, and a solicitor for anything worth more than the cost of review (the core code of a venture that is making money, a sale of the business).

## Tools
Free first. Claude Code session (Sonnet, Opus advisor only if ownership is disputed) for the drafting; Firecrawl free tier (500 credits as of Oct 2026, check the limit) for tool terms; Companies House and UK IPO search to confirm registered owners. No paid tools.

## Build notes
- Runs after `contract-drafting`, which supplies the assignment clause and the contractor agreement the fixes attach to. Re-run when a new contractor or tool is added.
- Keep the register as the single record; the build handoff job and any buyer due diligence read it.
- Never invent a signatory or a date. Unknown fields stay blank for Charlie.
