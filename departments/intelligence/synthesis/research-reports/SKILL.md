---
name: research-reports
title: Research Reports
department: intelligence
function: synthesis
autonomy: solo
stage: validate
builds_on: [vertical-analysis, competitor-teardown, tam-market-sizing, pricing-research]
breaks_into: [collect-verdicts, compute-verdict-line, write-cited-report]
replaces: "an analyst's written report and recommendation"
runs_on: github
status: ready
---

# Research Reports

Any question into a structured, cited report with diagrams.

## Reads from the brain
- `brain/company.md`: voice (plain, short, no hype), constraints, what we will not do
- `ventures/<slug>/brain.md`: problem, who, gap, mvp, money, proof

## Inputs
- Validate mode: every `ventures/<slug>/validate/<job>.json` and `.md` from `regulatory-screen`, `vertical-analysis`, `competitor-teardown`, `pricing-research`, `tam-market-sizing`, `trend-monitoring`, `audience-analysis`. Each JSON carries `signal` (pass, warn, fail), `confidence` and `reason`. If a job left no JSON, read its `.md` and have the model extract a signal against the same rubric, marked `extracted`.
- Question mode: a GitHub issue labelled `research`, or a dispatch input `question`, with an optional venture slug.
- Env: `GEMINI_API_KEY`, `GROQ_API_KEY`; optional `FIRECRAWL_API_KEY` for question mode.

## Steps
1. Collect the sidecars. A job counts as missing if its JSON is absent or `skipped`. The core jobs are `regulatory-screen`, `vertical-analysis`, `competitor-teardown`, `pricing-research`, `tam-market-sizing`; `trend-monitoring` and `audience-analysis` support.
2. Compute the verdict line in code, first match wins. (a) Any core job missing: `NO-GO (provisional)`, naming the missing jobs and saying the cause is incomplete evidence, not the market; rerun first. (b) `regulatory-screen` is fail, or `tam-market-sizing` is fail, or two or more jobs fail: `NO-GO`. (c) Exactly one job fails, or three or more warn (a core job at `low` confidence counts as one extra warn): `PIVOT`, naming the failing job. (d) Otherwise `GO`. The line is `Verdict: <GO|NO-GO|PIVOT>. <one sentence naming the deciding jobs>. Confidence: <lowest core confidence>. Status: unchallenged.` Save it to `verdict.json` with the rule that fired.
3. Write the body with Gemini 2.5 Flash (free tier, about 10 requests a minute and 250 a day as of Oct 2026, check; Groq as fallback). The model may not change the verdict line; code checks that line 1 of the file equals the computed line and rewrites it if not. Sections: scorecard table (job, signal, one-line reason, confidence); why, three bullets; what would change the verdict, two or three bullets; evidence in seven short blocks, one per job, under 120 words each; for PIVOT up to three options, each tied to an evidence item (narrower segment, different price band, different channel); for NO-GO a line on what would reopen it; open questions; jobs skipped.
4. Cite everything. Every sentence containing a figure carries `[n]`, mapped to a numbered source list of URLs taken from the sidecars. Code scans the draft and removes or flags any sentence with a figure and no citation, except dates.
5. Add diagrams as Mermaid code blocks, which GitHub renders for free: a `quadrantChart` of competitors by price and breadth from `competitor-teardown.json`, and a `flowchart` of how the verdict was reached. Leave an empty pair of markers, `<!-- charts:start -->` and `<!-- charts:end -->`, for `data-visualisation`.
6. Question mode: same structure without the verdict line. Plan 3 to 5 sub-questions, search with Hacker News Algolia API (free, no key, about 10,000 requests an hour), Reddit public JSON (about 10 requests a minute) and Firecrawl (500 free credits one-off, check; cap 30), then write the report.
7. Hand off: `adversarial-verification` must run before Charlie sees the report. Set the board entry to `awaiting challenge`.

## Output
- `ventures/<slug>/validate/report.md`: the verdict line, then the sections above. Two pages at most. This is the file Charlie reads for the validate gate.
- `ventures/<slug>/validate/verdict.json`: `verdict`, `rule`, `deciding_jobs`, `confidence`, `missing`, `signals`.
- Question mode: `ventures/<slug>/research/<question-slug>.md`.
- Update `ventures/<slug>/board.json`; unrunnable parts go under `skipped`.

## The ladder
- Human-led: Charlie reads each job's file and writes the recommendation himself.
- Human-assisted: the job drafts the report; Charlie edits the line and the pivot options.
- Fully autonomous: the verdict is computed by rule and the report is written without review, after the challenge pass.

## The human
What stays with Charlie: reading the report, setting `gates.validate` to `passed` in `board.json`, and on a no-go confirming the reason that goes back to Lodestone as `dropped`.

## Tools
Gemini 2.5 Flash, Groq, Mermaid (rendered by GitHub), Hacker News Algolia API, Reddit public JSON, Firecrawl, GitHub Actions. No Claude.

## Build notes
- The verdict rule is plain Python so it is testable; unit test every branch, including a missing core job. Rule thresholds live in one constant block.
- Other departments' validate jobs are assumed to write `ventures/<slug>/validate/<job>.json` in this shape. Confirm when `regulatory-screen`, `trend-monitoring` and `audience-analysis` are built.
- Free budget per venture across the validate stage is roughly 30 model calls and under 70 Firecrawl credits, so the 500 one-off credits cover about seven ventures.
- Tests offline with sidecar fixtures for go, pivot, no-go and provisional.
