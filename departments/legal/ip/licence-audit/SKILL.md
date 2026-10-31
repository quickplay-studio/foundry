---
name: licence-audit
title: Licence Audit
department: legal
function: ip
autonomy: solo
stage: build
builds_on: [project-scaffolding]
breaks_into: [list-dependencies, resolve-licences, check-assets-and-data, flag-conflicts]
replaces: "a software licence compliance scan, or a solicitor reviewing open source obligations"
runs_on: github
status: ready
---

# Licence Audit

Every dependency, font, image and dataset checked for a licence that allows commercial use.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof (is the product closed source, hosted, or distributed as an app?)

## Inputs
- The venture repo `quickplay-studio/<slug>` created by `project-scaffolding`: `requirements.txt`, `package.json` and lockfiles, `docs/` and asset folders, any `data/` files.
- A list of fonts, images, icons, audio and datasets the product uses, with where each came from (read from the repo and from `brain.md`).

## Steps
1. List dependencies from the lockfiles, including transitive ones. For GitHub repos use the dependency graph SBOM endpoint of the GitHub API (`GH_TOKEN`); otherwise parse the lockfiles.
2. Resolve each licence as an SPDX identifier: PyPI JSON API for Python, the npm registry for JavaScript, deps.dev (Google Open Source Insights, free) as a cross-check. Unknown or missing licence is a finding, not a pass.
3. Classify: permissive (MIT, BSD, Apache-2.0, ISC) is fine with notice; weak copyleft (LGPL, MPL-2.0) is fine if used as a library and unmodified; strong copyleft (GPL, AGPL) is a conflict for closed or hosted code; non-commercial, no-derivatives or "source available" terms (CC BY-NC, BUSL, SSPL) are a stop.
4. Check assets by source. Fonts: Google Fonts are mostly OFL, confirm per family. Images and icons: the licence page of the source (CC0, CC BY needs credit, stock site terms). AI-generated media: read the generator's current terms on commercial use and output ownership; UK copyright in AI output is unsettled, so note it.
5. Check datasets: Open Government Licence v3.0 for UK government data (needs attribution), ODbL (share-alike), CC BY, and any API terms of service that bar storage, resale or training. A site that forbids scraping cannot be a data source (company rule).
6. List the attribution notices required and draft a `NOTICES.md` text for the repo.
7. Flag: stop if any non-commercial, no-derivatives or AGPL/GPL item sits in shipped code; caution if any licence is unknown, any copyleft item needs a decision, or an asset source is unverified; else clear.

## Output
- `ventures/<slug>/clear/licence-audit.md`: first line `FLAG: clear`, `FLAG: caution` or `FLAG: stop`, then a table (item, type, version, licence, source checked, verdict, action), then the draft `NOTICES.md` text.
- `ventures/<slug>/clear/licence-audit.json`: the same rows, for the QA job and dashboards.
- Not legal advice. Drafts are checked by Charlie or a solicitor before use.

## The ladder
- Human-led: Charlie reads every licence by hand.
- Human-assisted: the job lists and classifies; Charlie decides each copyleft or unknown item.
- Fully autonomous: the default. The job writes the file, sets the flag and opens an issue on the venture repo for each stop. Re-run on every dependency change.

## The human
What stays with Charlie: replacing or removing a conflicting item, accepting a copyleft obligation, paying for any commercial licence (not before revenue), and a solicitor's view if the product will be distributed as an app or sold to a business buyer who asks for a licence warranty.

## Tools
Free first. GitHub dependency graph API, PyPI and npm registry APIs, deps.dev, the SPDX licence list, Firecrawl free tier (500 credits as of Oct 2026, check the limit) for asset and dataset licence pages, Gemini 2.5 Flash or Groq to read unusual licence text. `pip-licenses` and `license-checker` can run inside Actions if the APIs fail.

## Build notes
- Runs in the venture repo as a workflow on pull requests that change lockfiles, as well as once at build stage. The stage here is build; the output still goes under `clear/` so the gates read one folder.
- The model never decides a licence is permissive; it only summarises text. The SPDX id from the registry is the source of truth.
- Tests offline: fixture lockfiles with one GPL, one unknown and one MIT item.
- GitHub implementation: `run.py` beside this file (jobkit).
