---
name: tech-stack-detection
title: Tech-Stack Detection
department: intelligence
function: companies
autonomy: solo
stage: sell
builds_on: []
breaks_into: [fetch-fingerprints, dns-and-subdomains, hiring-evidence, gap-analysis]
replaces: "a paid technographics lookup"
runs_on: github
status: ready
---

# Tech-Stack Detection

What a target runs and where the gaps are.

## Reads from the brain
- `brain/company.md`: constraints, what we will not do (no scraping against a site's terms)
- `ventures/<slug>/brain.md`: gap and mvp, to know which tools the venture replaces or complements

## Inputs
- One account: name and domain, from the target list or a dispatch input.
- Env: `GEMINI_API_KEY`, `GROQ_API_KEY`; optional `GH_TOKEN`, `FIRECRAWL_API_KEY`.
- A fingerprint table kept as data in `foundry/data/fingerprints.json` (created by the build): patterns for script domains, headers, cookies, meta tags and DNS records, each mapped to a tool and category.

## Steps
1. Check `https://<domain>/robots.txt`. Fetch the home page and, if allowed, the pricing and careers pages with `requests`, identifying the bot in the User-Agent. One request per page, no crawling.
2. Match headers: `Server`, `X-Powered-By`, `Set-Cookie` names, `X-Vercel-Id`, `CF-Ray`, `X-Shopify-Stage` and similar. Match HTML: `meta name=generator`, script and link hosts, inline snippets (analytics, chat widgets, payments, consent banners). Match with the fingerprint table; the model is not used here.
3. DNS through Google's DNS-over-HTTPS (`dns.google/resolve?name=<domain>&type=MX`, free, no key): MX records name the email provider, TXT records show SPF includes (email senders) and domain verification tokens (workspace, support and CRM tools). CNAMEs on `support.`, `help.`, `status.`, `app.` and `go.` name the vendors behind them.
4. Subdomains from certificate transparency (`crt.sh/?q=%25.<domain>&output=json`, free, no key, slow and sometimes unavailable; retry once, else skip).
5. Hiring evidence. Job descriptions from the public job board APIs (Greenhouse, Lever, Ashby, free, no key) or the careers page: tools named in requirements ("experience with Salesforce") are evidence of use. If the company has a public GitHub org, read repo languages via the GitHub API (`GH_TOKEN`; 5,000 requests an hour for a personal token, lower for the Actions token as of Oct 2026, check).
6. Build the table: category, tool, evidence (header, script, DNS, job ad), url, confidence (high for header, script or DNS; medium for a job ad; low for inference). Drop anything with no evidence.
7. Gaps. Gemini 2.5 Flash (free tier, about 10 requests a minute and 250 a day, check; Groq as fallback) receives only the table and the venture's `gap` and `mvp`, and lists up to 5 gaps (a missing category, an outdated tool, a manual process implied by job ads) and which ones the venture touches. Each gap cites a table row.

## Output
- `ventures/<slug>/sell/accounts/<account-slug>/tech-stack.json`: `domain`, `detected` (category, tool, evidence, url, confidence), `gaps` (text, rows, touches_venture), `checked` (date). `account-monitoring` diffs this file.
- `ventures/<slug>/sell/accounts/<account-slug>/tech-stack.md`: the table and gaps, under 300 words.
- Mark the account done in `ventures/<slug>/board.json`; a blocked site goes under `skipped`.

## The ladder
- Human-led: Charlie views source and checks DNS by hand.
- Human-assisted: the job produces the table; Charlie confirms the gap before using it in outreach.
- Fully autonomous: runs for every target on entry and weekly via `account-monitoring`.

## The human
What stays with Charlie: whether a gap is worth mentioning to the account, and never claiming to know their stack more precisely than the evidence shows.

## Tools
`requests`, Google DNS-over-HTTPS, crt.sh, public job board APIs, GitHub API, Gemini 2.5 Flash, Groq, GitHub Actions. No paid lookup service, no Claude.

## Build notes
- The fingerprint table is the product; start with about 60 common tools and grow it from misses.
- Detection is evidence, not proof. Do not state a tool as fact in outreach without a high-confidence row.
- Tests offline with saved headers, HTML and DNS responses for three sites.
