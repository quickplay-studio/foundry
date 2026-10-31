# Sessions

One Claude Code session per department, Sonnet doing the work, Opus consulted at hard decisions. Each session fills the stubs in one folder of `departments/` and nothing else. Start every session by pasting the brief below and `/advisor opus` for the decisions marked advisor.

## Done
- Session 0 (31 Oct 2026): index, scaffold, brain template, audit engine, launch pipeline, deploy order, map page, Lodestone hook spec.
- Session 1 (31 Oct 2026, eight Sonnet agents in parallel): every department filled; job runner (`foundry/jobs.py`, `jobs.yml`); Radar page and `foundry/dashboards.py`; venture template; Lodestone Deploy button and sync steps; split into public code repo and private `foundry-ventures` data repo because private-repo Actions were blocked on the account.

## Open points from the department agents
- Operations: no job builds the MVP itself; `project-scaffolding` opens one issue per MVP bullet for a Claude Code session in the venture repo. Decide whether an `mvp-build` job is wanted.
- Intelligence: `adversarial-verification` wants a `prefer` argument on `util.ask_json` to force Groq against Gemini; `tech-stack-detection` needs `foundry/data/fingerprints.json`; `vertical-analysis` installs pytrends in its own step.
- Legal: UK IPO and EUIPO search pages may not read through Firecrawl; the skill then says unverified and flags caution. Apple, Google Play, domain and trade mark fees are flagged for Charlie, never paid by an agent.
- Customer and Operations chose thresholds (auto-reply confidence 0.85, 80 percent usage warning, 90 percent pass on agent evaluation) that Charlie may want to tune.
- Contracts between jobs that need a check once two departments run together: `validate/<job>.json` shapes, `sell/market-map.json`, `meetings/<date>-<title>.json`, `qa/result.json`.

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
8b. `commerce` (shops, TikTok Shop, dropshipping; added 31 Oct 2026)
9. Hardening session: make `audit.py` consult filled skills' `breaks_into`; give `foundry/jobs.py` tool calls (Firecrawl, Apify, Companies House) so GitHub jobs can fetch, not only reason; the open points above.
10. First real ventures: `quickplay-daily` (channel) and a real product in `tiktok-shop-pilot`; watch the validate stage run, fix what breaks. Lodestone hook later (`docs/LODESTONE_LATER.md`).

## Weekly drop
Every Sunday the Ideas Inbox batch may add one job to `map/tree.json`; `python -m foundry.scaffold` creates its stub; the next department session fills it.
