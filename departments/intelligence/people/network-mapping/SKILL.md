---
name: network-mapping
title: Network Mapping
department: intelligence
function: people
autonomy: assisted
stage: sell
builds_on: [person-research]
breaks_into: [collect-edges, build-graph, rank-paths]
replaces: "a sales researcher tracing connections by hand"
runs_on: github
status: ready
---

# Network Mapping

Who knows whom: paths into a target account.

## Reads from the brain
- `brain/company.md`: constraints, what we will not do, voice
- `ventures/<slug>/brain.md`: who and problem, to decide which target people matter

## Inputs
- `ventures/<slug>/sell/accounts/<account-slug>/people/*.json` from `person-research`, and `committee.json` if present, for the target people.
- Optional `ventures/<slug>/sell/network/my-contacts.csv`: Charlie's own export of his contacts (first name, last name, company, position). He supplies it; the job never fetches it. Use only in a private repo; otherwise Charlie runs the job locally and the file stays out of git.
- Env: `GEMINI_API_KEY`, `GROQ_API_KEY`; optional `GH_TOKEN`, `FIRECRAWL_API_KEY`, `COMPANIES_HOUSE_API_KEY`.

## Steps
1. List target people and the target company. Add Charlie as a node, with his contacts as first-degree edges (source: `contacts`).
2. Collect public edges, each with type, evidence URL, date and strength 1 to 3. Shared directorships and appointments: Companies House officer appointments (`/officers/{id}/appointments`, free key, 600 requests per 5 minutes as of Oct 2026, check). Co-contribution and org membership: GitHub API (public data, `GH_TOKEN`). Shared investors or advisers: `funding.json`. Co-appearance at talks, podcasts and articles: up to three Firecrawl searches per target (500 free credits one-off, check; cap 15 per account). Replies between two people on Hacker News via the Algolia API (free, no key).
3. Score strength in code: 3 for a current shared role or direct reply thread, 2 for a shared past role or event in the last 3 years, 1 for the same group or conference. Edges older than 5 years drop one point; a dissolved shared company counts as 1.
4. Build the graph with the stdlib: nodes (person, company, event, repo), edges as above. Breadth-first search from Charlie to each target, at most 3 hops. Rank paths by fewest hops, then the weakest edge on the path, then recency.
5. Gemini 2.5 Flash (free tier, about 10 requests a minute and 250 a day, check; Groq as fallback) writes a one-line reason per top path from the edge evidence only. Code checks every name in the text exists in the graph.
6. Write the files and open a draft pull request. Mark each edge `public` or `from Charlie's contacts`, and say plainly that a connection is not a relationship.

## Output
- `ventures/<slug>/sell/accounts/<account-slug>/network.json`: `nodes`, `edges` (from, to, type, strength, date, evidence_url, origin), `paths` (nodes, hops, weakest_edge, reason).
- `ventures/<slug>/sell/accounts/<account-slug>/network.md`: the top 5 paths with reasons and links, plus a note when there is no path within 3 hops. One page.
- A draft pull request; mark the account `awaiting Charlie` in `ventures/<slug>/board.json`.

## The ladder
- Human-led: Charlie scans his own contacts and the target's profile.
- Human-assisted: the job builds the graph and ranks paths; Charlie marks which edges are real relationships.
- Fully autonomous: graphs are rebuilt for each new target, but nothing is acted on.

## The human
What stays with Charlie: knowing which connections are real, which people would welcome an intro, and every approach to them.

## Tools
Companies House API, GitHub API, Hacker News Algolia API, Firecrawl, Gemini 2.5 Flash, Groq, GitHub Actions. No LinkedIn scraping, no paid graph service, no Claude.

## Build notes
- Graph code is plain Python (`collections.deque`); keep it under 120 lines and unit test with a six-node fixture.
- Keep contact data out of logs and out of any public repo or workflow output.
- Tests offline with saved officer appointments and a small contacts CSV.
