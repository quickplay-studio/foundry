# Sessions

One Claude Code session per department, Sonnet doing the work, Opus consulted at hard decisions. Each session fills the stubs in one folder of `departments/` and nothing else. Start every session by pasting the brief below and `/advisor opus` for the decisions marked advisor.

## Done
- Session 0 (31 Oct 2026): index, scaffold, brain template, audit engine, launch pipeline, deploy order, map page, Lodestone hook spec.
- Session 1 (31 Oct 2026, eight Sonnet agents in parallel): every department filled; job runner (`foundry/jobs.py`, `jobs.yml`); Radar page and `foundry/dashboards.py`; venture template; Lodestone Deploy button and sync steps; split into public code repo and private `foundry-ventures` data repo because private-repo Actions were blocked on the account.

- Session 2 (31 Oct 2026, nine Sonnet agents): a `run.py` for every one of the 149 GitHub jobs, the `jobkit` helpers, the offline harness (`tests/test_runs.py`), cross-department contracts (`foundry/contracts.py`, `map/contracts.json`) with the seams fixed, the runner gated on dependencies with recurring run and support jobs and three-attempt skips, the FreeLLMAPI router, and a local full-lifecycle drive with the fake model (`FOUNDRY_FAKE_MODEL=1`) that ran every stage of three ventures without a script crashing.

## Session 3 (1 Nov 2026): first live runs on GitHub
`smoke.yml` ran the fixture venture live four times. What held: the router comes up on the runner (24 chat models on Kilo and OVHcloud), Hacker News, the App Store search and review feeds, ONS Nomis, Google Trends RSS and plain page fetches all work from GitHub, and the validate stage writes real evidence. What was fixed from the logs: the audit now returns a drop list (the keep list overran the token limit); router calls retry across a named model order from `config.json` (`freellm.prefer`, `never`) because auto routing landed on a safety classifier and on 2B models; echoed template placeholders are scrubbed; competitor discovery is seeded from what the model already knows; web search falls back to Hacker News when the router has no search key (DuckDuckGo returns its bot challenge to runners); Reddit is unreachable from runners. The one key that changes the most is `TAVILY_API_KEY` (free, 1,000 searches a month, no card): it gives the router real web search for every job.

## Session 4 (1 Nov 2026): what Charlie sees, and the keyless routes
Added `foundry/digest.py` (one page of what needs Charlie: drafts to review with links, gates ready to pass, blocked verdicts, jobs that gave up; written to `office/digest.md` and the workflow step summary after every run), a shared headless Chrome PDF render (`jobkit.render_pdf`, used by proposals, approval packs and lead magnets), the seam tests (`tests/test_seams.py`: writer and reader scripts run in order on one venture), the QA line in status updates, `foundry/probe.py` (one line per keyless source from the runner) and `foundry/smoke.py` (rehearse stage by stage; `smoke.yml` input `through`). The Radar page now reads `radar-data.json` and the digest straight from the private repo with a read-only token saved in the browser, so the daily sync task is optional. What the probes showed from GitHub runners: Reddit's JSON API, pullpush, the Jina reader, DuckDuckGo, Brave, Mojeek, Qwant, Startpage and Yahoo are closed or challenged; Reddit's `search.rss` answers (throttled, one wait honoured) and Bing's HTML page answers correctly for the first requests of a run and then serves results for some other query, so rows that share no word with the query are dropped and the search falls through to Hacker News. The App Store, Google Trends RSS, ONS Nomis, YouTube RSS and the Companies House search page all answer. Decided against making `audit.py` read `breaks_into`: the audit prompt already overran the free models' output limit, and the drops it decides do not depend on sub-steps.

## Known gaps after session 2
- Live APIs were never called from this sandbox (its proxy blocks them): Hacker News, Reddit, App Store, YouTube, Meta, Gmail, Cal.com, HubSpot, Fireflies, Pexels, Companies House, ONS. The first real runs may need small query fixes; every call is wrapped and logs a skip. `.github/workflows/smoke.yml` runs the fixture venture live on GitHub with no private repo (dispatch it with a `job` input to try one job); read its Board summary step and download the `foundry-smoke-data` artifact.
- Nothing posts, sends, pays or opens issues from GitHub. Where a skill wanted that, the script writes the commands or draft to a file. A later session can add a `sell-send` workflow (Gmail) and issue-opening with a scoped token.
- Claude Code jobs (18 of 167) wait for a session: icp-definition, cold-email-drafting, demo-prototyping, project-scaffolding, integration-builds, data-migration, portal-provisioning, qa-and-verification, buying-committee-mapping, onboarding-journeys, calendar-management, onboarding-and-training, video-production, terms-of-service, privacy-policy, contract-drafting, nda-and-agreements, ip-assignment.
- PDFs are read only when pypdf is installed (guarded); renders need ffmpeg or ImageMagick on the runner (both present on ubuntu-latest) and headless Chrome for PDF pages (pending).
- Jobs outside a launch stage (email-triage, talent, HR) run only on demand: `python -m foundry.jobs --slug <slug> --job <id>`, or the jobs workflow with the job input.
- bank-and-payments-setup and research-reports can return a stop; the runner then sets `verdict: blocked` and waits for Charlie to override in writing or kill.

## Open points from the department agents
- Operations: no job builds the MVP itself; `project-scaffolding` opens one issue per MVP bullet for a Claude Code session in the venture repo. Decide whether an `mvp-build` job is wanted.
- Intelligence: `adversarial-verification` wants a `prefer` argument on `util.ask_json` to force Groq against Gemini; `tech-stack-detection` needs `foundry/data/fingerprints.json`; `vertical-analysis` installs pytrends in its own step.
- Legal: UK IPO and EUIPO search pages may not read through Firecrawl; the skill then says unverified and flags caution. Apple, Google Play, domain and trade mark fees are flagged for Charlie, never paid by an agent.
- Customer and Operations chose thresholds (auto-reply confidence 0.85, 80 percent usage warning, 90 percent pass on agent evaluation) that Charlie may want to tune.
- Commerce: `marketplace-compliance` runs on GitHub and resolves doubt to the stricter flag; flip it to `claude-code` if a wrong clear worries you. Its defaults (returns allowance 8 percent, margin floor 25 percent, target CPA at 60 percent of break-even, commission tiers) are assumptions marked in the skills.
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
9. Hardening session (done in sessions 2 to 4, except the open points marked for Charlie above): tool calls in every `run.py`, seams tested, keyless routes probed. `breaks_into` stays documentation.
10. First real ventures: `quickplay-daily` (channel) and a real product in `tiktok-shop-pilot`; watch the validate stage run, fix what breaks. Lodestone hook later (`docs/LODESTONE_LATER.md`).

## Weekly drop
Every Sunday the Ideas Inbox batch may add one job to `map/tree.json`; `python -m foundry.scaffold` creates its stub; the next department session fills it.
