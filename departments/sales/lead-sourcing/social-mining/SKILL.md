---
name: social-mining
title: Social Mining
department: sales
function: lead-sourcing
autonomy: solo
stage: sell
builds_on: [icp-definition]
breaks_into: [find-threads, collect-engagers, filter-to-business-roles, purge-old-rows]
replaces: "a LinkedIn Sales Navigator seat and a paid social-listening tool"
runs_on: github
status: ready
---

# Social Mining

Harvest engaged people from comments, followers and groups around the topic.

## Reads from the brain
- `brain/company.md`: constraints, what we will not do
- `ventures/<slug>/brain.md`: problem, who, proof (the proof links are the first threads to read)
- `ventures/<slug>/sell/icp.md`: titles and keywords

## Inputs
- `sell/icp.md` and the `proof` links.
- `sell/inbox/linkedin-paste.csv`: names, profile URLs and comment text that Charlie pastes by hand from posts he can see on his own account.
- Optional `APIFY_TOKEN`.

## Steps
1. Gate: `audit.json` must say `model: b2b`, else write a `skipped` line in `board.json` and stop.
2. Find threads where the pain is discussed: the Hacker News Algolia search API (free, no key), and Apify actors for Reddit and YouTube comments (free credit; as of Oct 2026, check the limit). Use only public pages and respect each platform's terms.
3. LinkedIn: no scraping, no automation, no scheduling tools. The job reads only `inbox/linkedin-paste.csv`.
4. For each commenter ask Gemini yes or no: does the public text show a business role that fits an ICP title? Keep the yes rows only.
5. Store the minimum: handle or name, platform, profile URL, post URL, a quote of at most 200 characters, and `signal` (asked for a tool, complained, compared options). Never store emails taken from profiles, follower dumps, or anything from private groups or messages.
6. Set `subscriber_type=individual` on every row. These people are not emailed. The routes are a reply in the thread by Charlie, a LinkedIn note by Charlie, or tracing their employer to a limited company through database-mining.
7. Purge rows older than 90 days unless marked `contacted` (UK GDPR storage limitation).

## Output
- `ventures/<slug>/sell/raw/social.csv`: the raw row shape (`leads.csv` columns from `company` to `collected_on`, no `id`) plus `notes` holding `signal` and the quote.
- Merged by list-building with email routes switched off.

## The ladder
- Human-led: Charlie reads threads and logs the people himself.
- Human-assisted: the job collects, Charlie replies in threads by hand.
- Fully autonomous: weekly collection and purge; replies still go out by Charlie.

## The human
What stays with Charlie: every reply, comment and connection request on any platform, and the LinkedIn paste.

## Tools
Hacker News Algolia API, Apify free credit, Gemini 2.5 Flash or Groq for the role check. No paid listening tool.

## Build notes
- A thin file is the right result: a dozen real people beat a thousand scraped handles.
- Tests: a fixture with a hobbyist and a business owner; assert the hobbyist is dropped and no email field is filled.
