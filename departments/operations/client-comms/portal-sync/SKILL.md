---
name: portal-sync
title: Portal Sync
department: operations
function: client-comms
autonomy: assisted
stage: none
builds_on: [portal-provisioning]
breaks_into: [collect-updates, filter-to-scope, leak-check, publish-and-verify]
replaces: "a person copying updates into a client portal by hand"
runs_on: github
status: ready
---

# Portal Sync

Session summaries and deliverables flow into the portal automatically.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof

## Inputs
- The venture repo's `portal/scope.json` (allow-list and `never` list) and `portal/build_status.py`, from `portal-provisioning`.
- In Foundry: `ventures/<slug>/board.json`, `status/latest.md`, `meetings/*-recap.md`, `qa/report.md`.
- `ventures/<slug>/deliverables/index.json`: `[{"title", "path", "share": true|false, "date"}]`. Only entries with `share: true` may leave Foundry.

## Steps
1. Trigger: a push to Foundry that changes `ventures/<slug>/**`, plus a daily run. Use a path filter so other ventures do not trigger it.
2. Build `status.json` using the allow-list only: `updated`, `stage`, `gates`, `jobs_done`, `jobs_total`, `next`, `latest_update` (the text of `status/latest.md` without its `Spend:` line), `deliverables` (title, url, date), `recaps` (date, title, url). Drop every field named in `never`.
3. Copy each shared deliverable into `portal/files/`. Small files only (PDF, markdown, CSV). A file without `share: true` is never copied, whatever its name.
4. Recaps: include a recap only when its date is in the past and `share` is true in its front matter. Default is not shared.
5. Leak check before anything is written: the output must contain no key pattern (`AIza`, `gsk_`, `sk-`), no pound figure from `budget.json`, no email address outside `scope.json` `allowed_emails`, no string from the `never` list. Any hit aborts the run and adds a `skipped` line to `board.json` naming the check, not the matched text.
6. Update one rolling branch `portal-sync` in the venture repo and open or refresh a single pull request with the new `status.json` and files.
7. After Charlie merges and the host redeploys, GET the live portal `status.json`. If its `updated` does not match within 24 hours, add an incident to `board.json` (`source: portal-sync`, severity `warn`).
8. Set this job in `board.json` to `done` with the pull request URL in `output`.

## Output
- `portal/status.json` and `portal/files/*` in the venture repo, via one rolling pull request.
- Lines in `board.json` `skipped` or `incidents` when a check stops the run or the live copy is stale.

## The ladder
- Human-led: Charlie copies updates in himself.
- Human-assisted: the job prepares a pull request, Charlie merges. This is the default.
- Fully autonomous: auto-merge of `status.json`-only changes after Charlie has merged three in a row unchanged in kind; scope and deliverables always need him.

## The human
What stays with Charlie: deciding what may be shared (`share: true`), merging, and approving any change to `scope.json`.

## Tools
Free first. GitHub Actions, the GitHub API, the venture's free host (Cloudflare Pages or Netlify, as of Oct 2026, check the limit). Python stdlib. No model, no Claude.

## Build notes
- The allow-list wins. A new field in `board.json` is invisible to the portal until someone adds it to `scope.json`.
- Never link to a private repo file from the portal; copy the file or leave it out.
- Keep the leak check as a separate function with its own test so it cannot be skipped by accident.
- Personal data of anyone in a recap is removed before sharing; when unsure, leave the recap out.
- GitHub implementation: `run.py` beside this file (jobkit).
