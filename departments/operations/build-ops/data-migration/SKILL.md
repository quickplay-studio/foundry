---
name: data-migration
title: Data Migration
department: operations
function: build-ops
autonomy: human
stage: build
builds_on: [integration-builds]
breaks_into: [profile-source, map-fields, dry-run-and-reconcile, write-go-brief]
replaces: "a data engineer's migration project or a paid migration service"
runs_on: claude-code
status: ready
---

# Data Migration

Move and clean data between systems without losing a row; you press go.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof

## Inputs
- A read-only export or read-only access to the source (file, CSV, API).
- The target schema (Supabase table definitions or the venture repo's data model) and the integration client from `integration-builds`.
- Any field mapping hints Charlie has written in `ventures/<slug>/migration/notes.md`.

## Steps
1. Keep the data out of git. Put the working copy in `migration/data/` and make sure `.gitignore` lists it. Only counts, hashes and the scripts are committed.
2. Profile the source and write `migration/profile.json`: row count per table, null rate per column, duplicate count on the key, odd encodings, date formats in use.
3. Write `migration/mapping.csv`: `source_field, target_field, transform, rule_for_bad_values`. Every source field appears. A field with no target is listed as `dropped: <reason>`, never omitted.
4. Write `migration/migrate.py`: idempotent (upsert on a stable key), dry run by default, `--go` required to write. Stdlib plus `requests`.
5. Dry run into a scratch target: a local SQLite file or a second free-tier Supabase project, never the live target. Reconcile and write `migration/reconcile.json`: per table, source rows = loaded rows + rejected rows, plus a checksum over the key column on both sides.
6. Pass rule: zero unexplained rows. Every reject is a line in `migration/rejects.csv` with the reason. Any gap in the arithmetic is a fail; fix the mapping and repeat.
7. Check that a full backup of the target exists and record its file name and sha256 in the brief. If none exists, the brief says so at the top.
8. Write `migration/brief.md`, one page, then stop. Never run `--go`. Set this job in `board.json` to `review` with the brief path in `output`.

## Output
- `ventures/<slug>/migration/brief.md` (read by Charlie): what moves, row counts, rejects with reasons, backup status, the command to run (`python migrate.py --go`), how to roll back, the three checks to make afterwards.
- Alongside it in the venture repo: `migration/mapping.csv`, `profile.json`, `reconcile.json`, `rejects.csv`, `migrate.py`.

## The ladder
- Human-led: Charlie runs every step; the session only drafts the brief. This is the default.
- Human-assisted: the session builds and dry-runs, Charlie presses go.
- Fully autonomous: not offered. A person presses go.

## The human
What stays with Charlie: pressing go, confirming the backup exists, deciding what to do with rejects, and checking the live target afterwards.

## Tools
Free first. Python stdlib, SQLite, the free Supabase tier (as of Oct 2026, check the limit). Claude Code with Sonnet to write the script; Opus as advisor on any lossy transform. No paid migration tool.

## Build notes
- Never delete from the source. Never write to the target without `--go`.
- If the data holds personal information, stop and ask Legal `data-protection` first; do not send rows to any free-tier model.
- A migration with more rows than the target's free-tier limit is a `skipped` line in `board.json`, not a partial load.
- Dates to ISO, money to integer pence, text to UTF-8 with trailing spaces trimmed. Log each transform in the mapping, not in the code only.
- Rollback is restoring the backup. Say so in the brief in one sentence.
