---
name: onboarding-and-training
title: Onboarding and Training
department: back-office
function: talent
autonomy: assisted
stage: none
builds_on: [sop-generation]
breaks_into: [list-access, assemble-reading-pack, write-thirty-day-plan, open-pull-request]
replaces: "an HR consultant's onboarding pack or a paid onboarding tool"
runs_on: claude-code
status: ready
---

# Onboarding and Training

New people get playbooks, access and a thirty-day plan. Run in a Claude Code session (Sonnet) once per new person; the session reads the real SOPs and writes the pack as a pull request for Charlie.

## Reads from the brain
- `brain/company.md`: who we are, what we make, voice and constraints (free tools only; Charlie works evenings and weekends UK time)
- `ventures/<slug>/brain.md`: the problem, the MVP and the money, so the person understands what the work is for

## Inputs
- A new-person brief from Charlie: `office/talent/onboarding/<person-id>/brief.md` with role, start date, venture, working hours, how paid, whether freelancer or employee, and the first deliverable.
- The SOPs written by Operations `sop-generation`: find them through the `output` field of that job in `ventures/<slug>/board.json`, or the venture's `sops/` folder. If none exist, stop and say so.
- `office/talent/roles/<role>.md`: the role brief and must-haves, if one exists.
- Access list `office/talent/access-matrix.json` (role to tools and folders), if one exists; otherwise built in step 1.

## Steps
1. List the least access the role needs: repo or folder permissions, shared drive folders, tools with a free seat, chat. One line each with who grants it. Mark each `to grant` for Charlie. The session never creates accounts or grants access.
2. Assemble the reading pack in the order a person would need it: a one-page company summary taken from `brain/company.md`, the venture summary, the three to five SOPs that cover their first deliverable, and a glossary of terms those files use. Link to the files, do not paste them.
3. Write the thirty-day plan. Week 1 orient: access works, reads the pack, one low-risk task shadowed. Week 2 contribute: a small task done with review. Week 3 to 4 own: the first real deliverable with a clear definition of done. Each week gets a stated outcome, a check-in date at Charlie's hours, and what good looks like.
4. Add short training checks per SOP: three questions the person can answer from the SOP, with the answers kept in a separate file.
5. Add an exit checklist for the same access list (what is removed on the last day), so access never lingers.
6. Add a list of items that are Charlie's or an adviser's, left unchecked: contract and terms, right-to-work checks and pension duties if the person is an employee, payment setup. State that the plan does none of them.
7. Open a pull request with all files. The description lists the open questions for Charlie.

## Output
- `office/talent/onboarding/<person-id>/plan.md`: the thirty-day plan with dates.
- `.../access.md`: access to grant and the exit checklist.
- `.../reading-pack.md`: ordered links and glossary. `.../checks.md` and `.../answers.md`.
- A pull request. Merge means Charlie approved the plan.

## The ladder
- Human-led: Charlie writes a welcome note and explains everything verbally.
- Human-assisted (the setting here): the session drafts the pack from real SOPs, Charlie edits and merges.
- Fully autonomous: not offered. Granting access and judging a person's first month are Charlie's.

## The human
What stays with Charlie: the hire, granting access, the contract and legal duties, running the check-ins, and judging the first month.

## Tools
Claude Code with Sonnet (Opus as advisor only if the scope, or whether the person is a freelancer or employee, is unclear). Free tools only for seats and docs.

## Build notes
- Why claude-code: it synthesises several files into a coherent plan, once per hire, with a pull request. A free model is weak at holding the whole pack consistently.
- Keep the pack short: if the reading pack runs over an hour of reading, cut it.
- Open point: the plan assumes SOPs exist; until Operations fills `sop-generation`, the first run stops at the inputs check.
