# Foundry

Foundry is Charlie's AI workforce: 151 agent jobs across 8 departments, every one a skill file that reads one company brain, plus an audit engine that marks the tree for a given venture and a launch pipeline that takes a validated Lodestone idea through validate, clear, build, launch, sell, support and run. Modelled on SkillTree by Altari (137 jobs, 7 departments), with a Legal department added.

## How it works

1. Lodestone finds an idea and Charlie marks it `validated`, then presses Deploy. The idea arrives here as `ventures/<slug>/idea.json`.
2. `.github/workflows/launch.yml` runs `python -m foundry.launch`: the audit engine (Gemini, then Groq, then a heuristic, all free) picks the jobs that apply to this idea, orders them by stage and dependency, and writes `brain.md`, `plan.md`, `board.json` and `budget.json` in the venture folder.
3. Departments run their jobs in stage order (`playbooks/deploy-order.md`). Solo jobs run on GitHub Actions with free models. Assisted jobs open a pull request. Human jobs write a one-page brief and stop. Complicated jobs run in Claude Code with Sonnet, Opus as advisor.
4. Ads are the one thing that costs money: Marketing writes the brief, Charlie approves the budget and pays the platform. Back Office tracks spend and revenue weekly and applies the kill rule.
5. The verdict goes back to Lodestone: `live`, parked (`watching`) or `dropped`.

## Layout

- `map/tree.json`: the index of departments, functions and jobs (autonomy, stage, builds_on). Edit it, then `python -m foundry.scaffold`.
- `departments/<dept>/<function>/<job>/SKILL.md`: one skill per job. `status: stub` until a department session fills it (`SESSIONS.md`).
- `brain/company.md`: the company brain. `brain/INTERVIEW.md`: how it is built.
- `foundry/`: `audit`, `launch`, `scaffold`, `util`.
- `ventures/<slug>/`: everything about one venture. `sample` is a test fixture.
- `playbooks/deploy-order.md`: stages, outputs, gates, kill rule.
- `dashboards/`: the six command centres (session 9).
- `docs/map.html`: the visual skill tree.
- `cli/foundry.sh`: `status`, `sync` (into `~/.claude/skills`), `zip` (for the Claude app).
- `LODESTONE_HOOK.md`: the changes Lodestone needs (session 10).

## Secrets

Settings, Secrets and variables, Actions: `GEMINI_API_KEY` (Google AI Studio, free) and optionally `GROQ_API_KEY`. Without either, the audit uses the heuristic and keeps every staged job. `GH_TOKEN` is the workflow's own token.

## Run locally

```
pip install -r requirements.txt pytest
python -m pytest -q tests
python -m foundry.scaffold
python -m foundry.launch --slug sample --dry-run
cli/foundry.sh status
```

## Deliberately not included

- No paid tools, no accounts created by agents, no card held by any agent.
- No Claude call at runtime inside a skill; Claude is a session Charlie starts, never a cron.
- No legal advice: Legal drafts, a solicitor or Charlie signs.
