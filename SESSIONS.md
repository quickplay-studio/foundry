# Sessions

One Claude Code session per department, Sonnet doing the work, Opus consulted at hard decisions. Each session fills the stubs in one folder of `departments/` and nothing else. Start every session by pasting the brief below and `/advisor opus` for the decisions marked advisor.

## Done
- Session 0 (31 Oct 2026): index, scaffold, brain template, audit engine, launch pipeline, deploy order, map page, Lodestone hook spec.

## Brief for a department session
Paste, replacing `<dept>`:

> Foundry, department session: `<dept>`. Read `CLAUDE.md`, `departments/<dept>/README.md` and `templates/SKILL.template.md`, then `brain/company.md` once. For every `SKILL.md` under `departments/<dept>/` with `status: stub`: fill the body so a Sonnet session or a GitHub Actions job could run it with no other context, set `runs_on` to `github` (free model, scheduled or triggered) or `claude-code` (needs judgement), set `replaces` to what a person or paid tool would cost, fill `breaks_into` with the two to four sub-steps the job splits into, write the ladder and the human line honestly, and change `status` to `ready`. Where a free service does the work (Firecrawl, Apify, public APIs, Gemini, Groq) name it and the free tier limit. Do not invent tools we do not have. Keep each skill under 120 lines. Run `python -m pytest -q tests` before committing. Commit per function with the message `<dept>: <function>`. Consult the advisor only on jobs where the autonomy level or the free-tool choice is in doubt.

## Order
1. `intelligence` (validate stage runs first on every venture)
2. `legal` (clear stage; add the UK sources each job must check)
3. `operations` (build stage; includes the venture repo template under `templates/venture/`)
4. `marketing` (launch stage; the ad brief format lives in `ad-creative`)
5. `customer`
6. `back-office` (the weekly run and the kill rule)
7. `sales`
8. `deals`
9. Audit, dashboards and CLI session: make `audit.py` consult filled skills' `breaks_into`, build the six command centres in `dashboards/` from `ventures/*/board.json`, finish `cli/foundry.sh`.
10. Lodestone hook session: apply `LODESTONE_HOOK.md` in the Lodestone repo and on the pinned Lodestone page.

## Weekly drop
Every Sunday the Ideas Inbox batch may add one job to `map/tree.json`; `python -m foundry.scaffold` creates its stub; the next department session fills it.
