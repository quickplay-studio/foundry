# Foundry

Foundry is Charlie's AI workforce: 167 agent jobs across 9 departments, every one a skill file that reads one company brain, plus an audit engine that marks the tree for a given venture and a launch pipeline that takes any venture (an app, a content channel, an online shop, a TikTok Shop, dropshipping, a service) through validate, clear, build, launch, sell, support and run. Modelled on SkillTree by Altari (137 jobs, 7 departments), with Legal and Commerce departments added. Standalone: ventures go in as one `idea.json` (`INTAKE.md`).

## Two repos

- `quickplay-studio/foundry` (this one, public): code, 151 skills, workflows, the map. Public so GitHub Actions costs nothing.
- `quickplay-studio/foundry-ventures` (private): `ventures/<slug>/`, `office/`, `radar-data.json`. The workflows check it out into `data/` with the `VENTURES_TOKEN` secret and push results back to it. Nothing in it is ever committed here.

## How it works

1. A venture goes into the private data repo as `ventures/<slug>/idea.json` (`INTAKE.md`: the GitHub web editor, `python -m foundry.intake`, or a Claude chat).
2. `.github/workflows/launch.yml` (every four hours) runs `python -m foundry.launch --all`: the audit engine (the free router first, then any Gemini or Groq key, then a heuristic) picks the jobs that apply to this idea, orders them by stage and dependency, and writes `brain.md`, `plan.md`, `board.json` and `budget.json` in the venture folder.
3. Departments run their jobs in stage order (`playbooks/deploy-order.md`). `.github/workflows/jobs.yml` runs every morning: `python -m foundry.jobs` takes the next ready `runs_on: github` jobs for each venture whose stage gate is open, has a free model do each one from its skill file and the brains, and writes the output into the venture folder. Solo jobs are marked done; assisted and human jobs are marked review for Charlie. `runs_on: claude-code` jobs wait for a Claude Code session (Sonnet, Opus as advisor). Charlie moves a stage on by setting its gate to `passed` in `board.json`.
4. Ads are the one thing that costs money: Marketing writes the brief, Charlie approves the budget and pays the platform. Back Office tracks spend and revenue weekly and applies the kill rule.
5. The verdict lives in `board.json` (`continue`, `scale`, `park`, `kill`), in `office/digest.md` and the run's step summary (what needs Charlie after every run), in the Needs you issue in the private repo, and on the Foundry Radar page (live with a read-only token saved on the page, or through the optional sync task in `docs/FOUNDRY_SYNC_TASK.md`).

## Layout

- `map/tree.json`: the index of departments, functions and jobs (autonomy, stage, builds_on). Edit it, then `python -m foundry.scaffold`.
- `departments/<dept>/<function>/<job>/SKILL.md`: one skill per job. `status: stub` until a department session fills it (`SESSIONS.md`).
- `brain/company.md`: the company brain. `brain/INTERVIEW.md`: how it is built.
- `foundry/`: `audit`, `launch`, `scaffold`, `util`.
- `data/`: the private repo checked out (git-ignored). `data/ventures/<slug>/`: everything about one venture. `tests/fixtures/sample-idea.json` is the test fixture.
- `playbooks/deploy-order.md`: stages, outputs, gates, kill rule.
- `docs/radar.html`: the Foundry Radar, six command centres and the Needs you digest on one pinned Claude page, reading the private repo's `radar-data.json` directly or through the daily sync.
- `docs/map.html`: the visual skill tree, pinned too; rebuild with `python -m foundry.mapbuild` after skills change.
- `foundry/jobs.py`: the GitHub job runner. `foundry/dashboards.py`: radar data. `foundry/freellm.py` and `.github/actions/freellm`: the free model router, pinned in `config.json`.
- `cli/foundry.sh`: `status`, `sync` (into `~/.claude/skills`), `zip` (for the Claude app).
- `templates/venture/`: what a new venture repo starts from (Operations `project-scaffolding`).
- `INTAKE.md`: how a venture goes in. `foundry/intake.py`: the local command. `templates/idea.template.json`: the shape.
- `docs/FOUNDRY_SYNC_TASK.md`: the optional Claude task that feeds the Radar page's store (not needed with a token on the page). `docs/LODESTONE_LATER.md`: the parked Lodestone hook. `docs/HANDOVER.md`: where things stand and what Charlie must do.

## Secrets

Settings, Secrets and variables, Actions, on this repo. Required: `VENTURES_TOKEN` (a fine-grained personal access token, repository access limited to `foundry-ventures`, permission Contents: read and write). That is all: the models come from the FreeLLMAPI router (`foundry/freellm.py`, the same router Quickplay runs), started in Docker on the runner for each job over free, keyless tiers, so no Gemini, Groq or Claude key is needed. Optional, each a free plan with no card: `TAVILY_API_KEY`, `EXA_API_KEY`, `FIRECRAWL_API_KEY` or `LINKUP_API_KEY` (web search through the router), `CEREBRAS_API_KEY` (the steadiest free chat models; the keyless tiers allow about two calls a minute per model, so this is the key that makes jobs fast), `OLLAMA_API_KEY` and `LLM7_API_KEY` (more chat capacity), `APIFY_TOKEN`, `COMPANIES_HOUSE_API_KEY`. `TAVILY_API_KEY` is the one that gives every job real web search. If the router cannot start, the job falls back to `GEMINI_API_KEY` or `GROQ_API_KEY` when present, else the heuristic, and tries again next run.

## Run locally

```
pip install -r requirements.txt pytest
python -m pytest -q tests
python -m foundry.scaffold
mkdir -p data/ventures/sample && cp tests/fixtures/sample-idea.json data/ventures/sample/idea.json
python -m foundry.launch --slug sample --dry-run
python -m foundry.jobs --slug sample --dry-run
cli/foundry.sh status
```

## Deliberately not included

- No paid tools, no accounts created by agents, no card held by any agent.
- No Claude call at runtime inside a skill; Claude is a session Charlie starts, never a cron.
- No legal advice: Legal drafts, a solicitor or Charlie signs.
