---
name: context-maintenance
title: Context Maintenance
department: operations
function: knowledge
autonomy: solo
stage: run
builds_on: []
breaks_into: [collect-changes, rebuild-state-block, find-contradictions, log-decisions]
replaces: "a person keeping project notes and briefs up to date"
runs_on: github
status: ready
---

# Context Maintenance

Per-venture brain files stay current as work happens.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof

## Inputs
- `ventures/<slug>/brain.md` and the marker block at its end: `<!-- context:start sha=<last> -->` to `<!-- context:end -->`.
- `board.json`, `budget.json`, `status/latest.md`, `qa/result.json`, `meetings/*.json` (decisions), `incidents` in the board.
- The venture repo `README.md` and `docs/mvp.md`, and any live landing page text recorded in `board.json`.
- Git history of `ventures/<slug>/` since the `sha` in the marker.

## Steps
1. List what changed under `ventures/<slug>/` since the recorded sha. If nothing, stop with no commit.
2. Rebuild the block between the markers from the JSON files, no model: stage, last gate passed, MVP status (checks passed of total), price from `money`, spend and revenue in pounds, open incidents (count), open decisions, last updated. Put the new sha in the marker.
3. Append new decisions from `meetings/*.json` to `## Decisions` in `brain.md` as `date, decision, source file`. Append only; never rewrite a past line.
4. Look for contradictions between the core sections (`problem`, `who`, `gap`, `mvp`, `money`, `proof`) and the sources: the price in `money` against the README and landing copy; the `mvp` bullets against `qa/result.json`; a `proof` link that now returns an error. Check with string and HTTP tests in code.
5. Write each contradiction as a proposed edit in a pull request `context: <slug>`: file, old text, new text, reason, source line. The job does not edit the core sections itself.
6. Size cap: keep `brain.md` under 120 lines. If over, move the oldest `## Decisions` lines to `ventures/<slug>/archive/brain-<YYYY-MM-DD>.md` and leave a one-line pointer.
7. Commit the block and the decisions as `context: <slug>`. Set this job in `board.json` to `done` with the commit in `output`.
8. Never touch `brain/company.md`. A proposal for it goes in a pull request body for Charlie and is not committed.

## Output
- `ventures/<slug>/brain.md`: marker block refreshed, `## Decisions` appended. Read by every other job first.
- A pull request with proposed edits to the core sections, when contradictions exist.
- `ventures/<slug>/archive/brain-<date>.md` when trimming.

## The ladder
- Human-led: Charlie edits the brain by hand after each session.
- Human-assisted: the job proposes edits by pull request, Charlie merges. This is the default for the core sections.
- Fully autonomous: the marker block and the decisions list. They commit without review.

## The human
What stays with Charlie: approving changes to the problem, who, gap, mvp, money or proof; owning `brain/company.md`.

## Tools
Free first. GitHub Actions weekly and on a change to `board.json` or `meetings/`, git, Python stdlib plus `requests`. A model (Gemini then Groq) is optional for wording a proposed edit; the facts are found in code. No Claude.

## Build notes
- Every other job reads `brain.md` first, so size is a cost. Short beats complete.
- The marker block is generated, not hand-written. Say so in a comment line inside it.
- Numbers come from JSON. Do not let a model restate them.
- Idempotent: running twice on the same state produces no diff.
- GitHub implementation: `run.py` beside this file (jobkit).
