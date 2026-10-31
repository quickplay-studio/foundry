---
name: sop-generation
title: SOP Generation
department: operations
function: knowledge
autonomy: assisted
stage: run
builds_on: []
breaks_into: [find-repeated-work, collect-real-commands, draft-sop, test-and-file]
replaces: "a consultant writing process documentation"
runs_on: github
status: ready
---

# SOP Generation

Turn delivered work into reusable playbooks.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof

## Inputs
- `ventures/*/board.json`: jobs with `done` status and their `output` paths.
- `ventures/*/incidents/*.md`: incident notes (a cause seen twice is a candidate).
- Git history, workflow files and run logs for the work being written up.
- `playbooks/` and `playbooks/sops/`: what already exists. Do not duplicate it.

## Steps
1. Find candidates. A task qualifies only if it has been done at least twice with the same shape: the same job `done` in two ventures, an incident cause seen twice, or a manual step that appears in two status updates. One-off work is not written up.
2. For each candidate, collect the real commands, files, settings and links from git history, workflow files and logs. Do not rely on recollection or on the model's memory.
3. Draft `playbooks/sops/<task-slug>.md`, 60 lines at most, in this order: Purpose; When to use it; Before you start (inputs, access, secret names); Steps (numbered, each a command or a click with the result to expect); Check it worked; If it fails (link the incident notes); Owner; Last checked (ISO date); Source ventures. Voice from `brain/company.md`: plain, short, UK English, no dashes.
4. Test. Commands marked safe (read-only or dry run) are run in the Actions job and must succeed. Mark the header `tested: yes` only if every step was run; otherwise `tested: no` and list the untested steps.
5. Open a pull request `sop: <task-slug>`. Do not edit existing playbooks such as `deploy-order.md`; propose the change in the pull request body.
6. Add one line to the pull request: which ventures and dates the SOP came from. An SOP with fewer than two sources is rejected.
7. Set this job in `board.json` of the triggering venture to `done` with the playbook path in `output`. If no candidate qualifies, write nothing and add no line.

## Output
- `playbooks/sops/<task-slug>.md`: the SOP as above, reviewed by pull request.
- The pull request body: sources and tested or not.

## The ladder
- Human-led: Charlie writes the SOP after doing the task.
- Human-assisted: the job drafts from history and tests it, Charlie reviews. This is the default.
- Fully autonomous: not offered. A playbook shapes future work, so a person approves it.

## The human
What stays with Charlie: deciding what is worth writing down, approving the SOP, and retiring one that no longer fits.

## Tools
Free first. git log, GitHub API, Gemini 2.5 Flash then Groq (`foundry.util.ask_json`) to turn collected commands into prose. No Claude.

## Build notes
- Run monthly, and when a venture reaches the end of the Run stage.
- A step the model cannot tie to a command, file or log line is deleted from the draft.
- Re-check the `Last checked` date each time the SOP is used; the job re-tests any SOP older than 90 days and opens a pull request if it fails.
- SOPs hold secret names only, never values.
- GitHub implementation: `run.py` beside this file (jobkit).
