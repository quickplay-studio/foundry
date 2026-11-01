# Foundry handover, 1 November 2026

Written at the end of session 4 (session 3's handover updated in place). Read this first in the next session, then `CLAUDE.md`, then `SESSIONS.md`.

## One paragraph

Foundry is built and tested. 167 agent jobs across 9 departments, every skill filled, 149 GitHub implementations, the audit, launch and job runner, the free model router, the map and radar pages, two repos (public code, private venture data), three workflows. It has been rehearsed live on GitHub on the fixture venture through the validate and clear stages, writing real evidence from Hacker News, Reddit's feed, Bing, the App Store, ONS, Google Trends and competitor sites. Every run now ends with a digest of what needs Charlie, and the Radar can read the private repo directly. The only thing stopping the three real ventures from launching is one GitHub token that cannot see the private repo. Nothing else is blocked.

## What Charlie must do

1. Fix `VENTURES_TOKEN` (required). https://github.com/settings/personal-access-tokens, open the fine-grained token saved as `VENTURES_TOKEN`, Repository access: Only select repositories, tick `foundry-ventures`, Permissions: Contents, Read and write, save. Or make a new one and paste it at https://github.com/quickplay-studio/foundry/settings/secrets/actions. Every check today (the last at 12:10) returned HTTP 404 for `quickplay-studio/foundry-ventures` with token owner `quickplay-studio`.
2. Run the first launch: https://github.com/quickplay-studio/foundry/actions/workflows/launch.yml, Run workflow, slug `all`. It launches `sample`, `quickplay-daily` and `tiktok-shop-pilot` into the private repo (brain.md, plan.md, board.json, budget.json, audit.json, README.md each). The schedule does the same every four hours.
3. Run the first jobs: https://github.com/quickplay-studio/foundry/actions/workflows/jobs.yml, Run workflow. Daily at 05:23 UTC otherwise. Up to five jobs a run across ventures in plan order.
4. Optional free keys, same secrets page, no card, each one a real step up:
   - `CEREBRAS_API_KEY` from https://cloud.cerebras.ai: steady fast chat models (about a million tokens a day). The keyless tiers allow about two calls a minute per model, which is why jobs pace themselves.
   - `TAVILY_API_KEY` from https://app.tavily.com: real web search for every job (1,000 a month). Without it search falls back to Hacker News; DuckDuckGo challenges GitHub runners and Reddit is unreachable from them.
   - `FIRECRAWL_API_KEY` (https://www.firecrawl.dev/app/api-keys) for JavaScript-heavy pages, `APIFY_TOKEN` for Reddit, Play reviews and Trustpilot actors, `COMPANIES_HOUSE_API_KEY` for company lookups, `YOUTUBE_API_KEY` for comment and trend sources.
5. Give `tiktok-shop-pilot` a real product: edit `ventures/tiktok-shop-pilot/idea.json` in https://github.com/quickplay-studio/foundry-ventures (problem, who, gap, mvp, money, channels, budget_gbp). Until then it runs on the placeholder.
6. Optional: the Radar page live. Make a second fine-grained token with Repository access: Only `foundry-ventures`, Permissions: Contents, Read only; open the pinned Foundry Radar, Source, paste it, Read live. It stays in that browser only and the page then shows every run's `radar-data.json` and the Needs you digest with no Claude task. (`docs/FOUNDRY_SYNC_TASK.md`, the daily Claude task that fills the page's store, is the fallback and costs a Sonnet run a day.)
7. Read what needs you after each run: the Summary tab of the run at https://github.com/quickplay-studio/foundry/actions (the digest is printed there), or `office/digest.md` in the private repo, or the Radar's Needs you view.

## Decisions waiting on you (not blocking)

- Whether to add an `mvp-build` job. Today `project-scaffolding` (Claude Code) opens one issue per MVP bullet in the venture repo and nothing on GitHub builds the product; a Claude Code session does. Adding a GitHub job would mean the free models write product code unattended, which session 1's agents advised against.
- Thresholds the department agents chose: auto-reply confidence 0.85 (customer), 80 percent usage warning and 90 percent agent-evaluation pass (operations), returns allowance 8 percent, margin floor 25 percent, target CPA 60 percent of break-even (commerce). Each is a constant at the top of its `run.py`.
- `marketplace-compliance` runs on GitHub and resolves doubt to the stricter flag; set `runs_on: claude-code` in its SKILL.md if a wrong clear worries you.

## How it runs day to day

- A venture is one `idea.json` in `ventures/<slug>/` of the private repo (`INTAKE.md` has the shape). `launch.yml` audits it with the free model (which jobs apply, b2b or b2c, what to drop), orders them by stage and dependency and writes the plan and board.
- `jobs.yml` runs ready GitHub jobs in plan order, gated by stage. A job writes its files into the venture folder and commits them. Solo jobs end `done`; assisted and human jobs end `review` for Charlie.
- Gates: when a stage is done Charlie sets `gates.<stage>: passed` in `board.json` and the next stage starts. A job that returns a stop flag sets `verdict: blocked`; Charlie overrides in writing or kills.
- Run-stage jobs repeat every 7 days, support jobs every 3. A job that skips on three different days is marked `skipped` so dependants can move on; set it back to `todo` to retry.
- `smoke.yml` (manual) runs the whole pipeline on the fixture venture with no private repo: dispatch it with a `job` input to try one job live before a venture reaches it, or `through` (a stage name) to rehearse every stage up to that one with gates passed automatically, or `probe_only` true to see which keyless sources answer the runner; read the Board summary step and the per-script diagnostics in the log.
- Jobs outside a stage (email triage, HR, talent) run on demand: `jobs.yml` with the job input, or `python -m foundry.jobs --slug <slug> --job <id>`.
- 18 jobs run in Claude Code, not on GitHub: icp-definition, cold-email-drafting, demo-prototyping, project-scaffolding, integration-builds, data-migration, portal-provisioning, qa-and-verification, buying-committee-mapping, onboarding-journeys, calendar-management, onboarding-and-training, video-production, terms-of-service, privacy-policy, contract-drafting, nda-and-agreements, ip-assignment. Each needs a session when a venture reaches it (`SESSIONS.md` has the brief).

## Where things are

- Code: https://github.com/quickplay-studio/foundry (public). Venture data: https://github.com/quickplay-studio/foundry-ventures (private). Local clone in this sandbox at `/home/claude/foundry` with a git-ignored `data/` copy of the ventures.
- Pages: Foundry Map https://claude.ai/artifact/67kXWzT6Pzd5pS1G5H9KNz (from `docs/map.html`), Foundry Radar https://claude.ai/artifact/C7f5MnT2vPMYSHWQ6QZXGv (pinned, database-backed).
- Index `map/tree.json`; contracts between jobs `map/contracts.json` (zero gaps); the model order `config.json` (`freellm.prefer`, `never`); the deploy order `playbooks/deploy-order.md`; the brain `brain/company.md`.
- Tests: `python -m pytest -q tests` (159, offline, the network is blocked in the run tests). Lint rule: no em or en dashes anywhere.

## What today's live runs taught (already fixed)

- The audit's keep list overran the model's output limit: it now returns a drop list and the structural rules (no stage, sell only for b2b, commerce only for shops) stay in code.
- The router's auto routing landed on a safety classifier ("Safety: Safe") and on 2B models: calls now go to a named order from `config.json`, steadiest first, guard and tiny models never.
- The keyless upstreams (OVHcloud, Kilo) answer 502 and 429 when hit back to back: calls rotate across models with a 32 second rest per model, a rate-limited model rests a minute, three faults and the process stops asking that model. A clean run of eight jobs takes ten minutes.
- Weak models echo template placeholders ("<two sentences>") into fields: a scrub blanks them; prompts that matter were rewritten with concrete examples; matching by name now also matches by position or loosely (regulatory areas, competitor extraction, comment labels).
- No web search without a key: competitor discovery is seeded from what the model already knows, then verified by fetching the sites; search falls back to Hacker News.
- Google Trends RSS added as a keyless trend source; off-topic trends rank below fitting ones. Audience themes are folded into groups so counts mean something.
- The router status file crashed on a missing folder on a fresh runner; fixed. Per-script diagnostics now print into the workflow log.

## What session 4 added

- `foundry/digest.py`: after every run, `office/digest.md` in the private repo and the workflow step summary list drafts waiting for review (with links), stages whose jobs are all finished (set the gate), blocked verdicts, jobs that gave up, last runs.
- `jobkit.render_pdf`: proposals, brand-deal approval packs and lead-magnet guides render to PDF with the runner's Chrome.
- `tests/test_seams.py`: writer and reader scripts run in order on one venture (validate chain for a service, an app and a shop; market map into account monitoring; QA result into handoff and status; transcript into follow-ups). Status updates carry the QA line.
- `foundry/probe.py` and the findings in `SESSIONS.md`: from runners Reddit's `search.rss` and Bing's HTML page answer; both are now fallbacks (`intelkit.reddit`, `util.keyless_search`), with off-topic Bing rows dropped. Everything else keyless is closed; a `TAVILY_API_KEY` is still the real search fix.
- `foundry/smoke.py` and the `through` input: stage rehearsals.
- Radar: reads the private repo with a browser-held read-only token; Needs you view renders the digest.

## Known gaps

- Reddit's JSON API is unreachable from GitHub runners (403); the search feed answers but is throttled per address, so some runs get nothing. An Apify token restores full access.
- Pricing and teardown signals vary run to run with the model and the competitor set; a sample idea with few public complaints will read `fail` or `warn`, which is the honest answer, not a bug.
- Nothing posts, sends, pays or opens issues from GitHub. Where a skill wanted that, the script writes the commands or draft to a file.
- PDFs read only when pypdf is installed (guarded). Deck renders (Marp) are still a pending workflow step.
- Live APIs not yet exercised by a real venture: YouTube, Meta, Gmail, Cal.com, HubSpot, Fireflies, Pexels, Companies House. Every call is wrapped and logs a skip; the first real run may need small fixes, which is what `smoke.yml` with a `job` input is for.
- Lodestone integration is parked (`docs/LODESTONE_LATER.md`). Lodestone's own daily sweep has failed since 29 October because GitHub Actions on the account's private repos is blocked on billing; that is a Lodestone matter, not Foundry's.

## First real run: what to watch

1. `launch.yml` after the token fix: the "Check the data repo token" step must say HTTP 200, the Launch step must print `launched <slug>: N jobs, model freellm/...` for all three, and the Commit step must push to `foundry-ventures`.
2. `jobs.yml`: the first five jobs are validate-stage intelligence jobs. Read `ventures/<slug>/validate/*.md` in the private repo. `quickplay-daily` is a channel (build is the content pipeline, launch is distribution); `tiktok-shop-pilot` adds the commerce department.
3. If a job skips three days running, the reason is in `board.json` under `skipped` with an attempt count, and in the workflow log under `[job] ...`.

## Session log

- Session 0 (31 Oct): index, scaffold, brain, audit, launch, deploy order, map.
- Session 1 (31 Oct): every department filled by eight parallel agents, job runner, Radar, repo split.
- Session 2 (31 Oct): a `run.py` for all 149 GitHub jobs, jobkit, offline harness, contracts, router, local full lifecycle with the fake model.
- Session 3 (1 Nov): `smoke.yml`, eight live rehearsals, the fixes above, Cerebras as an optional router key.
- Session 4 (1 Nov): digest, PDF render, seam tests, source probes with the Reddit feed and Bing fallbacks, stage rehearsals through clear, Radar live from GitHub, this handover.
