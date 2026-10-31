---
name: privacy-policy
title: Privacy Policy
department: legal
function: documents
autonomy: assisted
stage: clear
builds_on: [data-protection]
breaks_into: [load-data-map, draft-sections, check-against-product, write-review-note]
replaces: "a solicitor or online generator producing a privacy notice, from free templates to a few hundred pounds"
runs_on: claude-code
status: ready
---

# Privacy Policy

Draft the privacy policy from what the product actually collects.

The policy says what the product does, in plain words. It is written from the data map, not from a template.

## Reads from the brain
- `brain/company.md`: voice (plain, short sentences, no hype), offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof
- `ventures/<slug>/clear/data-protection.md` and `data-map.json`: the facts to write from
- `ventures/<slug>/clear/entity-and-structure.md`: who the controller is

## Inputs
- `data-map.json`: data types, purposes, lawful bases, processors, transfers, retention, ICO fee answer.
- Controller name, address and contact email. Missing details stay as marked blanks for Charlie.
- After build: the repo's real data collection, cookies and third-party scripts for the check in step 6.

## Steps
1. Load the data map. If it is missing or flagged stop, write a skipped line in `board.json` and end.
2. Draft the notice using the headings the ICO's UK GDPR guidance on the right to be informed requires: who we are and how to contact us; what we collect and where from; why, and the lawful basis for each purpose; who we share it with (named processors and categories); transfers outside the UK and the safeguard; how long we keep each type; your rights (access, correction, deletion, restriction, portability, objection, rights around automated decisions) and how to use them; the right to complain to the ICO; whether providing data is required; cookies and similar technology with a link to the cookie settings (PECR consent for non-essential cookies); changes to the policy and the date.
3. Add a separate short section for under-18s if the data map says they are likely users, written at a reading level they can follow (ICO Children's code transparency standard).
4. Say what the product does not do. If it uses an AI model provider with user content, state it and the provider's role; do not claim "we never share data" if processors exist.
5. Use plain English. Short sentences, active voice, headings a user can scan, no legal filler. Each lawful basis in one line, with a one-sentence reason.
6. Check against the product: every data item and third-party service in the repo or the plan appears in the policy; every claim in the policy is true in the product (retention, deletion, encryption wording). Mark mismatches in the review note. Check store requirements: the Apple privacy labels and Google Play Data safety form must match the policy (see `platform-and-ad-compliance`).
7. Write a review note: the mapping from data map rows to policy sections, blanks, assumptions, open questions for a solicitor or data protection adviser.

## Output
- `ventures/<slug>/clear/privacy-policy.md`: the draft policy with blanks in square brackets, and `ventures/<slug>/clear/privacy-review-note.md`. Opened as a draft pull request; `board.json` set to waiting for review.
- Not legal advice. Drafts are checked by Charlie or a solicitor before use.

## The ladder
- Human-led: a data protection adviser writes the notice from the data map.
- Human-assisted: the default. The job drafts and cross-checks; Charlie confirms facts and publishes; a solicitor reviews if special category or children's data are involved.
- Fully autonomous: only the re-check after a data change, which opens a pull request and never edits live text.

## The human
What stays with Charlie: confirming each statement matches the product, signing off before launch, publishing and linking the policy in the product and the store listing, and a solicitor for health, finance or children's data.

## Tools
Free first. A Claude Code session (Sonnet) for the drafting. Gemini 2.5 Flash or Groq on GitHub for the data map to policy cross-check, with placeholders instead of real personal data. Firecrawl free tier (500 credits as of Oct 2026, check the limit) to read the ICO page on the right to be informed.

## Build notes
- The policy must change when the data map changes. Re-run on any `data-map.json` change.
- Tests offline: a fixture data map, assert every row appears, blanks are marked and no dash characters are present.
- The policy is not the lawful basis; consent screens and cookie banners are build work that follows from it.
