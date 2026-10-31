---
name: qa-and-verification
title: QA and Verification
department: operations
function: build-ops
autonomy: solo
stage: build
builds_on: [project-scaffolding]
breaks_into: [derive-checks, run-on-real-data, score-pass-or-fail, write-qa-report]
replaces: "a QA tester's pass over each release"
runs_on: claude-code
status: ready
---

# QA and Verification

Verify every build against real data before anyone else sees it.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof

## Inputs
- The venture repo `quickplay-studio/<slug>` at a named commit (the one being verified).
- The `mvp` bullets in `brain.md`.
- Real data: public datasets, live pages or documents Charlie has supplied in `qa/data/`. Never invented figures.
- `ventures/<slug>/kickoff/access-status.json` for which live checks can run.

## Steps
1. For each MVP bullet write one check in the venture repo's `qa/checks.json`: `{"id", "bullet", "how", "data", "expect"}`. `expect` is a plain sentence a stranger could judge.
2. Real data: each check runs on at least 10 real inputs where the product takes inputs. Synthetic inputs are allowed for edge cases only and are labelled `synthetic`. A check with no real data is `blocked`, never `pass`.
3. Run `python -m pytest -q tests`, then every check, then the generic checks: the page returns 200; no console errors; layout holds at 375px width; no secret in the repo (grep for `AIza`, `gsk_`, `sk-` and for any file named `.env`); no broken links; user-facing text has no em or en dash.
4. Score with these rules:
   - PASS: tests green, every MVP check passes on real data, every generic check passes, no critical finding.
   - FAIL: any red test, any failed MVP check, or any critical finding. Critical means a secret in the repo, a crash on first use, a wrong answer on real data, lost data, or a regulated feature Legal has not cleared.
   - BLOCKED: a check has no real data or a required secret is missing. The gate stays open.
   - Warnings (cosmetic, a page slower than 3 seconds) do not fail the build. List them.
5. Write the report. First line is the verdict word, then the commit SHA verified.
6. On FAIL open one issue per critical finding in the venture repo, then stop. This job does not fix. After the fix, re-run. After 3 failed loops stop and hand to Charlie.
7. Set this job in `board.json`: `done` on PASS, otherwise `blocked`, with the report path in `output`. Do not set `gates.build`; that is Charlie's.

## Output
- `ventures/<slug>/qa/report.md`: verdict line, commit SHA, one row per check (input, observed output, expected, result), findings with severity, warnings.
- `ventures/<slug>/qa/result.json`: `{"verdict": "PASS|FAIL|BLOCKED", "sha": "", "date": "", "checks": [{"id", "result"}]}`. `handoff-docs` reads this file.
- In the venture repo: `qa/checks.json`, re-run by `ci.yml` on every push.

## The ladder
- Human-led: Charlie tries the product by hand against a list.
- Human-assisted: the session writes and runs the checks, Charlie reads the report.
- Fully autonomous: the session does steps 1 to 7 and Charlie reads the verdict line. This is the default; the Build gate still needs Charlie to use the product once end to end.

## The human
What stays with Charlie: supplying real data the session cannot find, using the product once end to end, and setting `gates.build` to `passed`.

## Tools
Free first. pytest, `requests`, GitHub Actions. A headless browser step in Actions for the page checks (Playwright or Chromium on the runner is free). Claude Code with Sonnet to write the checks; Opus as advisor only when a finding is disputed.

## Build notes
- Pass and fail are judged against the product's own MVP, not against taste.
- Never mark a check `pass` from the code alone. Evidence is an observed output.
- Re-run on every push to `main` through `ci.yml`; a later red run reopens the verdict as FAIL.
- Keep the report under 100 lines. Link long output files rather than pasting.
