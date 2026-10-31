---
name: portal-provisioning
title: Portal Provisioning
department: operations
function: build-ops
autonomy: assisted
stage: build
builds_on: [project-scaffolding]
breaks_into: [define-scope, build-static-portal, add-access-control, wire-status-feed]
replaces: "a bespoke client portal or a paid project-management seat per client"
runs_on: claude-code
status: ready
---

# Portal Provisioning

Spin up a scoped portal with live status per venture or client.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof

## Inputs
- `ventures/<slug>/board.json` (stage, gates, jobs) and `kickoff/note.md`.
- The venture repo `quickplay-studio/<slug>`.
- Audience: a public status page (consumer venture) or named clients behind a login (B2B venture). Read it from `idea.json` and the business model in `board.json`. If unclear, build the public version.

## Steps
1. Write `portal/scope.json` in the venture repo: an allow-list of what a viewer may see: `stage`, `gates`, `jobs_done`, `jobs_total`, `next`, `latest_update`, `deliverables`, `recaps`. Add a `never` list: costs, budget, keys, incidents, other ventures, internal notes, personal data.
2. Build a static page in `portal/`: `index.html` and `portal.js` reading `status.json`. No framework. Readable on a phone, light and dark.
3. Write `portal/build_status.py`: reads the venture's `board.json`, keeps only allow-listed fields, writes `portal/status.json`. `portal-sync` runs it afterwards.
4. Hosting: Cloudflare Pages or Netlify free tier, publish directory `portal` (as of Oct 2026, check the limit). Charlie connects the repo.
5. Private client view: use Supabase auth on the free tier (as of Oct 2026, check the limit). One row per client in a `portal_status` table with row level security on `client_id`; the page signs in and reads only that client's row. If Supabase is not set up, publish nothing private and add a `skipped` line in `board.json`.
6. Tests, offline: the page renders from a sample `status.json`; `build_status.py` output contains no key outside `scope.json`; with two test users, user B cannot read user A's row (run against a local SQL fixture of the policy).
7. Open a pull request `portal: <slug>`. Set this job in `board.json` to `review` with the PR URL in `output`. After Charlie connects the host, record the live URL in `output`.

## Output
- `portal/` in the venture repo: `index.html`, `portal.js`, `scope.json`, `build_status.py`, sample `status.json`, and `tests/test_portal.py`.
- A pull request; later the live URL in `board.json`.

## The ladder
- Human-led: Charlie builds the page and policies; the session reviews them.
- Human-assisted: the session builds, Charlie approves the scope and merges. This is the default.
- Fully autonomous: only for the public status page with a fixed scope; Charlie still connects the host.

## The human
What stays with Charlie: approving `scope.json`, creating the hosting and Supabase accounts, inviting clients, and merging.

## Tools
Free first. Cloudflare Pages or Netlify free tier, Supabase free tier, GitHub Actions. Claude Code with Sonnet, Opus as advisor on the access policy. No paid portal product.

## Build notes
- The page is public by default. Treat everything in `status.json` as visible to the world unless step 5 is done.
- Row level security must be on for every table the page reads. A table without it is a fail.
- Keys in the page are the anon key only, set through the host's environment, never committed.
- No analytics scripts on a client portal.
