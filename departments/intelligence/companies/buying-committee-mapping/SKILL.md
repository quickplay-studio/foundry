---
name: buying-committee-mapping
title: Buying-Committee Mapping
department: intelligence
function: companies
autonomy: assisted
stage: sell
builds_on: [company-deep-dive]
breaks_into: [list-named-people, infer-roles, map-concerns, flag-gaps]
replaces: "a sales researcher's stakeholder map"
runs_on: claude-code
status: ready
---

# Buying-Committee Mapping

Who decides: economic buyer, champion, blockers.

## Reads from the brain
- `brain/company.md`: voice, constraints, what we will not do (no bought lists, no unsolicited email outside the law)
- `ventures/<slug>/brain.md`: problem, who, gap, mvp, money, proof

## Inputs
- `ventures/<slug>/sell/accounts/<account-slug>/deep-dive.json`: entity, `people` (name, title, source), `signals`, `posture`, `fit`. If missing, run `company-deep-dive` first or log under `skipped`.
- Optional `tech-stack.json` and `funding.json` from the same folder.
- Env: optional `FIRECRAWL_API_KEY` (500 free credits one-off as of Oct 2026, check; cap 10 per account), `GH_TOKEN`.

## Steps
1. List the named people already in `deep-dive.json`. Add more only from public business sources: the team page, press releases, conference speaker pages and Companies House officers, found with up to three Firecrawl searches ("<company> head of <function>", "<company> finance director", "<company> procurement"). Keep name, title, source URL and date.
2. Fix the company size band from the deep dive: under 50 people, 50 to 250, over 250. Role patterns differ by band: in a small firm the founder or managing director is usually both economic buyer and champion; in a larger one the budget sits with a department head and sign-off with finance or procurement.
3. Assign each person one role hypothesis: economic buyer (signs or owns the budget), champion (feels the problem and would push internally), user, technical evaluator, blocker (legal, procurement, IT security, a rival tool's owner), influencer. Give confidence (high, medium, low) and the evidence, a title, a posted job, a quote. Never assert a role without evidence; use `unknown` where there is none.
4. For each person with medium or high confidence, write what they probably care about, taken from the deep dive's stated priorities and the venture's `problem`, and the likeliest objection, with the source behind it.
5. Flag gaps: no economic buyer found, no technical evaluator, two plausible economic buyers. Suggest the cheapest public way to close each (a job post, a talk, the filings), never a guess.
6. Write both files and open a draft pull request for Charlie to review. Spend an Opus advisor consult only if two economic buyers conflict or the evidence is thin on everyone.

## Output
- `ventures/<slug>/sell/accounts/<account-slug>/committee.md`: a role table (person, title, role, confidence, evidence), concerns and objections, gaps and a suggested first contact with the reason. One page.
- `ventures/<slug>/sell/accounts/<account-slug>/committee.json`: `people` (name, title, role, confidence, evidence, url, concerns, objection), `gaps`, `suggested_first_contact`, `researched`. `person-research` and `network-mapping` read it.
- A draft pull request; mark the account `awaiting Charlie` in `ventures/<slug>/board.json`.

## The ladder
- Human-led: Charlie maps the committee from LinkedIn, the website and calls.
- Human-assisted: the session proposes roles with evidence; Charlie corrects them. This is the default.
- Fully autonomous: not advised; a wrong economic buyer wastes the first message.

## The human
What stays with Charlie: confirming roles, choosing the first contact, and any call to a person to verify the committee.

## Tools
Firecrawl, Companies House API, GitHub API; a Claude Code session with Sonnet doing the work, Opus as advisor only for conflicts. No LinkedIn scraping, no bought data.

## Build notes
- Runs as `claude-code` because inferring roles from thin public evidence needs judgement and honest uncertainty; a free model over-asserts. One account per session.
- Public business information only. No home addresses, no personal social media, no family details; this is a business role map.
- Test with a fixture deep dive that has two plausible economic buyers; the output must flag it, not choose.
