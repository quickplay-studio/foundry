---
name: access-collection
title: Access Collection
department: operations
function: onboarding
autonomy: assisted
stage: build
builds_on: [kickoff-pack]
breaks_into: [read-checklist, check-secrets-present, chase-missing, record-status]
replaces: "a project coordinator chasing logins and keys by email"
runs_on: github
status: ready
---

# Access Collection

Chase and verify every credential and key a build needs, stored as secrets only.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof

## Inputs
- `ventures/<slug>/kickoff/access.md`: one row per secret (name, purpose, required, state).
- The venture repo `quickplay-studio/<slug>` once `project-scaffolding` has made it. Before that, check Foundry's own secrets only.
- Secrets arrive as environment variables in the check workflow. The job never reads them from a file.

## Steps
1. Parse the rows of `access.md`. Each row becomes `{name, required, state}`.
2. Run the workflow `.github/workflows/access-check.yml` in the venture repo (create it from the snippet in Build notes if missing). For each name it tests only `[ -n "$NAME" ]` and prints `NAME: present` or `NAME: missing`. It never prints a value, a length or a prefix.
3. For each present key, make one read-only call that needs no write access: list models for Gemini and Groq, an anonymous-role select on a known table for Supabase. Record only the HTTP status as `ok` (2xx) or `rejected` (401 or 403). Treat a 429 as `ok but rate limited` and retry once the next day.
4. For each `missing` or `rejected` required row, write one instruction line: "Add secret NAME in quickplay-studio/<slug>: Settings, Secrets and variables, Actions. Free tier: <service>. Paste the value nowhere else." Never ask for a card.
5. Open one GitHub issue titled `access: <slug>` with the checklist. On later runs update the same issue and comment at most once every 48 hours.
6. When every required row is `ok`, write `access-status.json`, close the issue and set this job to `done` in `board.json`.
7. If a required row is still not `ok` after 7 days, add a line under `skipped` in `board.json` (job, reason naming the secret, date) and stop chasing. The stage is not blocked; jobs that need that secret skip themselves.

## Output
- `ventures/<slug>/kickoff/access-status.json`: `{"checked": "<ISO>", "items": [{"name": "GEMINI_API_KEY", "required": true, "state": "ok|missing|rejected"}]}`.
- A GitHub issue `access: <slug>` in the venture repo, the only place Charlie is asked for anything.

## The ladder
- Human-led: Charlie checks each key by hand and ticks the list.
- Human-assisted: the job checks and chases, Charlie adds the secrets. This is the default.
- Fully autonomous: not offered. A person must create the account and paste the key.

## The human
What stays with Charlie: creating each free account, generating the key, adding it as a repository secret, and rotating any key the check calls `rejected`.

## Tools
Free first. GitHub Actions secrets and the GitHub API (`GH_TOKEN`). One read-only HTTP call per service. No model, no Claude.

## Build notes
- Snippet for the check step: `env: {GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}}` then `[ -n "$GEMINI_API_KEY" ] && echo "GEMINI_API_KEY: present" || echo "GEMINI_API_KEY: missing"`. Add one line per secret.
- GitHub masks secret values in logs, but do not rely on it: print no value in any form.
- Free tiers change. Beside each service note "as of Oct 2026, check the limit".
- A key found in a file, issue or log is an incident: add it under `incidents` in `board.json` and tell Charlie to rotate it.
