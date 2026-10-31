---
name: fit-scoring
title: Fit Scoring
department: sales
function: enrichment
autonomy: solo
stage: sell
builds_on: [account-enrichment, icp-definition]
breaks_into: [load-icp-weights, score-firmographics, score-pain-and-triggers, assign-tiers]
replaces: "HubSpot's paid lead scoring or Apollo scoring"
runs_on: github
status: ready
---

# Fit Scoring

Score each lead against the ICP so effort goes where it converts.

## Reads from the brain
- `brain/company.md`: constraints
- `ventures/<slug>/sell/icp.md`: the `icp` block with `weights`, `keywords`, `exclusions`

## Inputs
- `sell/leads.csv`, `sell/accounts.csv`, and `sell/triggers.csv` if present.
- Secrets `GEMINI_API_KEY`, `GROQ_API_KEY`.

## Steps
1. Gate: `audit.json` must say `model: b2b`, else write a `skipped` line in `board.json` and stop.
2. Firmographic (default weight 40): segment SIC match, size band in the ICP, region, age. Each is 1, 0.5 or 0; the script sums the fractions of the weight.
3. Pain (25): Gemini reads the lead's `notes` and the website snippet and returns an integer 0 to 5 against the ICP pains, with a one-sentence reason. Fallback to Groq, then a keyword count from the ICP. Score is the integer divided by 5, times the weight.
4. Trigger (20): the strongest live trigger for the account: `high` full weight, `medium` 60 percent, `low` 30 percent, none 0.
5. Reachability (15): verified named email full weight, `likely` or role email 60 percent, phone only 30 percent, nothing 0.
6. `fit_score` is the sum, rounded half up, 0 to 100. Tier A is 70 or more, B is 45 to 69, C is below 45.
7. A disqualifier match (an ICP exclusion or a set `status_flag`) sets tier `X` with the reason. Individuals are scored as normal with `no-email` added to `fit_reason`; they never enter an email touch.
8. Write only `fit_score`, `tier` and `fit_reason` (one line). Touch no other column.
9. Print the tier counts. If under 20 percent of leads are A or B, say so in `list-report.md`: the list or the ICP needs rethinking, and more sending will not fix it.

## Output
- Updated `ventures/<slug>/sell/leads.csv`.
- Tier decides effort. A gets a dossier, LinkedIn, video and a call. B gets email and one LinkedIn note. C and X get nothing.

## The ladder
- Human-led: Charlie ranks the list by eye.
- Human-assisted: the job scores, Charlie moves a few rows between tiers.
- Fully autonomous: re-scores after enrichment and after any new trigger.

## The human
What stays with Charlie: overriding a tier. An override is a non-blank `tier` with `fit_reason` starting `manual:`, and the job leaves it alone.

## Tools
Python standard library for the sums, Gemini 2.5 Flash then Groq for the pain score (as of Oct 2026, check the limit). No paid scoring.

## Build notes
- Run twice: once after account-enrichment, once after email-verification, since reachability changes.
- Tests: a lead per tier, one disqualified, one manual override that must survive.
- GitHub implementation: `run.py` beside this file (jobkit).
