---
name: handoff-docs
title: Handoff Docs
department: operations
function: knowledge
autonomy: assisted
stage: build
builds_on: [qa-and-verification]
breaks_into: [check-qa-passed, collect-facts, write-runbook, write-handoff-note]
replaces: "a developer's handover document and walkthrough"
runs_on: github
status: ready
---

# Handoff Docs

Clean documentation when a system ships.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof

## Inputs
- `ventures/<slug>/qa/result.json`: the verdict must be `PASS`, and its `sha` must equal the venture repo's current `main` commit. Otherwise stop with a `skipped` line in `board.json` ("QA not passed" or "docs would describe an unverified build").
- The venture repo `quickplay-studio/<slug>`: file tree, `app/`, workflows, `docs/integrations/*.md`, `docs/integrations/limits.md`, `qa/checks.json`.
- `ventures/<slug>/kickoff/access-status.json`, `monitors.json`, `usage-summary.json`, `board.json`.

## Steps
1. Check the QA verdict and sha as above.
2. Collect facts by script, not by reading and guessing: the file tree with one line per file from its first comment or docstring; environment variable names used in code (`os.environ`); workflows and their schedules; the live URL; integrations and their free-tier limits; the commands to run locally and to test.
3. Write `docs/handoff/runbook.md` in the venture repo: how to run locally (three commands at most); how to redeploy; how to roll back (revert the commit and redeploy); how to rotate a key (secret names only); what the monitors watch; what to do at each free-tier limit; who to tell if something breaks.
4. Write `docs/handoff/architecture.md`: one paragraph on how it fits together and the file list from step 2. No diagrams.
5. Write `docs/handoff/known-issues.md`: QA warnings, `skipped` lines, paths that were not tested.
6. Update the top-level `README.md`: what it is and the price in the first two lines, the live URL, how to run, how to test.
7. Verify: every path named in the docs exists; every command in the runbook is run in Actions with `--help`, `--dry-run` or as a test; no key pattern (`AIza`, `gsk_`, `sk-`); no em or en dash. Fix the docs until the script passes.
8. Write the one-page note for Charlie (see Output). Open a pull request `handoff: <slug>` in the venture repo. Set this job in `board.json` to `review` with the note path in `output`.

## Output
- Ships to Charlie: `ventures/<slug>/handoff.md`, one page, with: the product and its price in two lines; the live URL; the QA verdict, date and commit; what is live and what is not; what it costs now (expected nothing) with the free-tier table; the next three actions in order (use the product once end to end, set `gates.build` to `passed`, start the Launch stage); where everything is.
- In the venture repo: `docs/handoff/runbook.md`, `architecture.md`, `known-issues.md` and the updated `README.md`, via the pull request.

## The ladder
- Human-led: Charlie writes the handover himself.
- Human-assisted: the job drafts from facts and Charlie reads and merges. This is the default.
- Fully autonomous: not offered. This is what Charlie signs off the build on.

## The human
What stays with Charlie: reading the note, using the product once end to end, merging the pull request, and setting the Build gate.

## Tools
Free first. git, a fact-collection script in Python stdlib, GitHub Actions for the command checks. Gemini 2.5 Flash then Groq (`foundry.util.ask_json`) to turn facts into plain sentences. Claude Code only if the repo is too tangled for the script to describe.

## Build notes
- Facts come from files and code. The model words them; it never adds a feature, a price or a limit.
- If the product has changed since QA, re-run `qa-and-verification` first.
- Keep `handoff.md` to one page. Link to the runbook for detail.
- Voice from `brain/company.md`: plain, short, UK English, no dashes, no exclamation marks.
