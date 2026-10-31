---
name: warm-path-finding
title: Warm-Path Finding
department: intelligence
function: people
autonomy: human
stage: sell
builds_on: [network-mapping]
breaks_into: [filter-real-paths, rank-and-brief]
replaces: "an account executive's hunt for a mutual connection"
runs_on: github
status: ready
---

# Warm-Path Finding

The shortest real intro path; asking for the intro is yours.

## Reads from the brain
- `brain/company.md`: voice (plain, short, no hype), constraints
- `ventures/<slug>/brain.md`: problem, mvp and proof, for what the intro can honestly say

## Inputs
- `ventures/<slug>/sell/accounts/<account-slug>/network.json` and `network.md` from `network-mapping`, after Charlie has marked which edges are real relationships (a `confirmed` flag on each edge, set in the pull request).
- `committee.json` and the target's `people/<person-slug>.json` for context.
- Env: `GEMINI_API_KEY`, `GROQ_API_KEY`. Nothing is fetched from the web.

## Steps
1. Keep only paths whose first hop is an edge Charlie has confirmed or that comes from his own contacts. A path through a connection nobody has confirmed is not warm; drop it.
2. Rank the rest in code: fewest hops, then the weakest edge on the path, then recency, then whether the middle person's role is relevant to the target's problem. Pick one recommended path and one backup.
3. Gemini 2.5 Flash (free tier, about 10 requests a minute and 250 a day as of Oct 2026, check; Groq as fallback) writes the one-page brief from the graph and notes only. Code checks that every name and link in the brief appears in `network.json`; any that do not are removed.
4. If no confirmed path exists within 2 hops, the brief says so on its first line and recommends cold outreach through the Sales jobs or dropping the account, with the reason. Do not stretch a weak path to fill the page.
5. Include a three-line intro request Charlie can edit, marked as a draft in his voice: who he is, why this person, one clear ask that is easy to forward. State that it is not sent.
6. Stop. The job sends nothing, messages no one and opens no pull request beyond the brief file.

## Output
- `ventures/<slug>/sell/accounts/<account-slug>/warm-path.md`: one page. First line: the recommended path in plain words, or "no warm path". Then why it is real (edges and links), the backup, what the intro-maker should be asked, the draft request, and risks (stale edge, weak tie, a conflict of interest).
- Mark the account `brief ready` in `ventures/<slug>/board.json`.

## The ladder
- Human-led: Charlie scans his contacts and asks around himself. This is the default for the ask.
- Human-assisted: the job ranks confirmed paths and writes the brief; Charlie edits and sends.
- Fully autonomous: not allowed. An intro is a favour between people.

## The human
What stays with Charlie: asking for the intro, the wording, the timing, and deciding whether the favour is worth spending.

## Tools
Gemini 2.5 Flash, Groq, GitHub Actions. No web fetches, no messaging, no Claude.

## Build notes
- Small script: filter, rank, brief, name check. Keep it under 80 lines.
- It must refuse to run if no edge carries `confirmed`, and log under `skipped` why.
- Tests offline: a graph with one confirmed and one unconfirmed path, and a graph with no confirmed path.
- GitHub implementation: `run.py` beside this file (jobkit).
