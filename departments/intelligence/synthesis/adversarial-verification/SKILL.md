---
name: adversarial-verification
title: Adversarial Verification
department: intelligence
function: synthesis
autonomy: assisted
stage: validate
builds_on: [research-reports]
breaks_into: [extract-claims, check-evidence, argue-the-opposite, rule-on-verdict]
replaces: "a sceptical second analyst reviewing the work"
runs_on: github
status: ready
---

# Adversarial Verification

Claims get attacked before they get believed; the kill decision is yours.

## Reads from the brain
- `brain/company.md`: constraints (nothing regulated without a human and a solicitor), what we will not do, voice
- `ventures/<slug>/brain.md`: problem, who, gap, mvp, money, proof

## Inputs
- `ventures/<slug>/validate/report.md` (status `unchallenged`), `verdict.json`, every `<job>.json` and `.md`, and `charts/*.json` if present.
- Env: `GEMINI_API_KEY`, `GROQ_API_KEY`; optional `FIRECRAWL_API_KEY`.
- This runs after `research-reports` and `data-visualisation`, and before Charlie reads anything.

## Steps
1. Extract claims. Gemini 2.5 Flash (free tier, about 10 requests a minute and 250 a day as of Oct 2026, check) lists every atomic claim in the report as JSON: id, text, kind (number, absence such as "no competitor does X", trend, price, quote), cited source ids, and `central` true if the verdict depends on it.
2. Check in code, no model. For each cited URL: fetch with `requests` (HEAD, then GET) and confirm a 200. Confirm the figure or quoted string appears in the page text or in the saved API response. Re-do the arithmetic of the TAM funnel and the pricing percentiles from the JSON. A claim with no source, a dead link or a mismatch is `failed`.
3. Attack the absences. For each "no competitor does X" or "nobody charges for Y" claim, run three searches built to disprove it: App Store search API (free, no key, about 20 calls a minute), Hacker News Algolia API (about 10,000 requests an hour), and one Firecrawl search (500 free credits one-off, check; cap 10). Any credible hit marks the claim `contradicted`, with the link.
4. Argue the opposite. Use a different model family from the writer: if the report was written by Gemini, call Groq free tier (about 30 requests a minute and 1,000 a day on the 70B model, check); otherwise Gemini. Give it only the evidence files and ask for the strongest case against the verdict and its three most dangerous objections, each with a test that could be run. Run each test that fits the free tools and record the result.
5. Rule in code. `stands`: no central claim failed or contradicted. `weakened`: one central claim failed, or any objection test supported the opposite case. `overturned`: two or more central claims failed, the arithmetic is wrong, or an absence claim the verdict rests on is contradicted. If the model call fails, run steps 2 and 3 alone and say the opposite-case pass was skipped.
6. Propose, never apply. For `weakened` or `overturned`, propose a replacement verdict line one step more cautious (GO to PIVOT, PIVOT to NO-GO) with the reasons. A NO-GO that rests on a failed claim is flagged for a second look rather than flipped.
7. Open a draft pull request on branch `validate/<slug>` that sets line 2 of `report.md` to `Challenge: <outcome>, <n> claims checked, <m> failed` and adds a short Challenge section under the verdict, plus `attack.md` and `attack.json`. Set the board entry to `awaiting Charlie`.

## Output
- `ventures/<slug>/validate/attack.md`: outcome, claims table (id, claim, check, result, link), the opposite case and test results, the proposed line if any. Under 500 words.
- `ventures/<slug>/validate/attack.json`: `outcome`, `claims_checked`, `failed`, `contradicted`, `objections`, `proposed_line`, `models`.
- A draft pull request as above. Charlie sees the report only through it.

## The ladder
- Human-led: Charlie plays devil's advocate on his own report.
- Human-assisted: the job checks, attacks and proposes; Charlie decides what to do with the outcome. This is the default.
- Fully autonomous: not allowed for the kill decision; only the checks in steps 2 and 3 run unattended.

## The human
What stays with Charlie: the decision to kill, pivot or proceed, and the validate gate in `board.json`. The job never edits the verdict line itself.

## Tools
`requests` fetch checks, App Store search API, Hacker News Algolia API, Firecrawl, Gemini 2.5 Flash, Groq, GitHub Actions and `GH_TOKEN` for the pull request. Claude Code only if Charlie wants a deeper second opinion on a `weakened` result.

## Build notes
- `foundry.util`'s model chain needs a way to prefer Groq for step 4 (a small `prefer` argument); the build session adds it, not this department.
- Keep the check code separate from the model code so tests run offline: fixtures for a dead link, a figure not on the page, a wrong sum and a contradicted absence.
- About 6 model calls and under 10 Firecrawl credits per venture.
- GitHub implementation: `run.py` beside this file (jobkit).
