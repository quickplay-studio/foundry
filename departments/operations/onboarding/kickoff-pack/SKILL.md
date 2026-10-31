---
name: kickoff-pack
title: Kickoff Pack
department: operations
function: onboarding
autonomy: solo
stage: build
builds_on: []
breaks_into: [read-venture-brain, pick-free-stack, write-kickoff-note, write-access-checklist]
replaces: "a freelance project manager's first-day onboarding pack"
runs_on: github
status: ready
---

# Kickoff Pack

Welcome note, access checklist and project scaffold the day work starts.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof

## Inputs
- `ventures/<slug>/idea.json`, `brain.md`, `plan.md`, `board.json`, `budget.json` (all written by the launch workflow).
- `validate` and `clear` gates in `board.json` must read `passed`. If not, stop and write a `skipped` line (see Output).

## Steps
1. Read `brain/company.md`, then the venture's `brain.md` and `plan.md`. If `brain.md` is missing, add a `skipped` line and stop.
2. From the `mvp` bullets, list what the product needs: hosting, database, auth, analytics, model calls, payments, email.
3. Map each need to a free service. Defaults, each "as of Oct 2026, check the limit": Cloudflare Pages or Netlify (hosting), Supabase (database, auth), PostHog (analytics), UptimeRobot (monitoring), Gemini 2.5 Flash then Groq (model calls), GitHub Actions (jobs). A need with no free option is marked `needs Charlie` with the reason. Payments are marked `later: after first sign-ups`.
4. Write `kickoff/note.md` (under 40 lines): product name, the problem in one line, who it is for, the price from `money`, the MVP bullets, the stack from step 3, and the Build gate: QA passes on real data and Charlie uses it once end to end. Voice from `brain/company.md`: plain, short, UK English, price and what it does in the first two lines.
5. Write `kickoff/access.md`: a table with one row per secret: name, purpose, required (yes or no), where the free tier lives (service name only), state `missing`. Names only, never values. Use the standard names `GEMINI_API_KEY`, `GROQ_API_KEY`, `GH_TOKEN`, plus one per extra service, for example `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `POSTHOG_KEY`.
6. Set this job in `board.json` to `done` with `output` set to `ventures/<slug>/kickoff/` and `updated` set to today (ISO date).
7. Commit as `Foundry Bot <foundry@users.noreply.github.com>` with message `kickoff: <slug>`.

## Output
- `ventures/<slug>/kickoff/note.md`: the welcome note, read by Charlie and later by `project-scaffolding`.
- `ventures/<slug>/kickoff/access.md`: the checklist `access-collection` works from.
- On failure, a line in `board.json` under `skipped`: `{"job": "kickoff-pack", "reason": "<short>", "date": "<ISO>"}`.

## The ladder
- Human-led: Charlie writes the note and checklist by hand from the brain.
- Human-assisted: the job drafts, Charlie edits the stack choices.
- Fully autonomous: the job commits both files after launch and Charlie reads them on the board. This is the default.

## The human
What stays with Charlie: confirming the stack, signing up to each free service himself (agents never create accounts), and deciding anything marked `needs Charlie`.

## Tools
Free first. The checklist and stack mapping are a lookup table, no model needed. Gemini 2.5 Flash (then Groq) via `foundry.util.ask_json` words the note only. No Claude.

## Build notes
- Runs in the same workflow job as `launch`, or as its own job on a push that changes `board.json`.
- Numbers in the note come from `idea.json` and `budget.json`, never from the model. Check the note against them before commit.
- Never put a key, token or password in either file. A grep for `AIza`, `gsk_` and `sk-` must return nothing.
