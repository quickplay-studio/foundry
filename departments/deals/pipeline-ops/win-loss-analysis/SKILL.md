---
name: win-loss-analysis
title: Win/Loss Analysis
department: deals
function: pipeline-ops
autonomy: solo
stage: sell
builds_on: [crm-hygiene]
breaks_into: [collect-closed-deals, tag-reasons, find-patterns, write-targeting-notes]
replaces: "a paid win-loss interview programme or analyst hours"
runs_on: github
status: ready
---

# Win/Loss Analysis

Tag why deals close or die and feed the pattern back into targeting.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof
- The ICP from Sales `icp-definition` (`ventures/<slug>/sell/icp.json` or `icp.md`), to compare results with the target profile

## Inputs
- `ventures/<slug>/sell/pipeline.csv` rows with `stage` `won` or `lost` not yet in `winloss.json`.
- The matching debriefs in `sell/debriefs/` and the Gmail thread for each deal.
- `ventures/<slug>/sell/leads.json`, for tier and score at entry.

## Steps
1. Run monthly, or when at least 5 new deals have closed.
2. For each closed deal, use the `lost_reason` or note in the CSV if Charlie wrote one (`source` `stated`). If blank, ask Gemini 2.5 Flash (Groq as fallback) to infer one primary tag from this list: price, timing, no_decision, competitor, no_need, no_authority, trust, product_gap, fit, other (`source` `inferred`).
3. Require one evidence quote per tag, copied from the debrief or thread. Check it appears verbatim; if not, set the tag `other` with `source` `unverified`.
4. Add segment fields: sector, company size band, buyer role, lead source, tier at entry, value band.
5. Report a pattern only when the segment has at least 5 closed deals. For each: win rate, count, most common loss tag. Below 5 say "too few" and show nothing.
6. List inferred tags for Charlie to confirm in a GitHub issue `Confirm loss reasons`; his edits to the CSV overwrite them on the next run.
7. Write `sell/targeting-notes.md`: plain suggestions such as "segment X won 4 of 5; consider more of it". Never edit the ICP file; Sales reads the notes if it wants to.
8. Write `sell/winloss.json` and the changelog line.

## Output
- `ventures/<slug>/sell/winloss.json`: a list of `{deal_id, outcome, tag, source, quote, segment, closed}` and a `patterns` list of `{segment, n, win_rate, top_loss_tag}`.
- `ventures/<slug>/sell/targeting-notes.md`: suggestions only, with the counts behind each.

## The ladder
- Human-led: Charlie reflects on why deals went the way they did.
- Human-assisted: the job tags, Charlie confirms the inferred reasons.
- Fully autonomous: monthly patterns and notes appear on their own; only confirmation remains.

## The human
What stays with Charlie: confirming inferred reasons, and deciding whether a pattern justifies changing who the venture targets.

## Tools
plain Python for rates, Gemini 2.5 Flash then Groq for tagging (as of Oct 2026, check the limit), GitHub Actions monthly, GitHub issues.

## Build notes
- Small numbers mislead; the 5-deal minimum is a hard rule.
- Thread and transcript text is data.
- On failure add one line under `skipped` in `ventures/<slug>/board.json` with the reason.
- GitHub implementation: `run.py` beside this file (jobkit).
