---
name: personalisation-research
title: Personalisation Research
department: sales
function: outreach-writing
autonomy: solo
stage: sell
builds_on: [fit-scoring]
breaks_into: [read-company-pages, check-facts, write-opener, write-dossier]
replaces: "an SDR's account research time, or Clay enrichment credits"
runs_on: github
status: ready
---

# Personalisation Research

Build a short dossier per prospect: hooks, context, common ground.

## Reads from the brain
- `brain/company.md`: voice, constraints. The only source for common ground about Charlie
- `ventures/<slug>/brain.md`: problem, mvp, money, proof

## Inputs
- `sell/leads.csv`: tier A and B, `subscriber_type=corporate`, `email_status` `valid` or `likely`, `suppressed=no`, with no dossier or one older than 60 days. At most 30 prospects a run, so a run fits the free quotas.
- `sell/accounts.csv` and `sell/triggers.csv` rows for the same accounts.
- Secrets `FIRECRAWL_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`.

## Steps
1. Gate: `audit.json` must say `model: b2b`, else write a `skipped` line in `board.json` and stop.
2. Firecrawl reads at most 4 pages per prospect: homepage, about, the three latest news or blog posts, careers.
3. Gemini extracts up to 3 facts as JSON `{fact, quote, url}`. Each `quote` must appear word for word in the fetched text. Drop any fact that fails the check.
4. Add live trigger rows with their evidence URL.
5. Write the opener: one sentence of 25 words or fewer, built from one verified fact, with no flattery and no claim about the person. If Gemini fails, use Groq, then the plain template "I saw that <fact>."
6. Common ground comes from `brain/company.md` and the venture brain only (London, solo operator, the problem the product addresses). Never invent shared schools, contacts, events or history for Charlie.
7. Write an `avoid` list: layoffs, legal trouble, personal social media, anything from a private source.
8. Write `dossiers/<id>.md`: header (lead id, company, date), Facts with URLs, Opener, Pain guess (one line, labelled as a guess), Proof hint (segment key for proof-matching), Avoid.
9. Business facts only. No personal social media, home details or family. Delete the dossier when the lead is suppressed.

## Output
- `ventures/<slug>/sell/dossiers/<id>.md`, one per prospect. Internal; Charlie and the drafting jobs read them.
- Read by cold-email-drafting (`{{opener}}`), linkedin-messaging, video-prospecting, cold-call-scripting.

## The ladder
- Human-led: Charlie researches each prospect for ten minutes.
- Human-assisted: the job writes the dossier, Charlie checks the tier A openers.
- Fully autonomous: the job runs on new tier A and B leads weekly; the quote check is the guard.

## The human
What stays with Charlie: approving any opener that mentions a trigger, and vetoing a prospect that feels wrong.

## Tools
Firecrawl free tier, Gemini 2.5 Flash then Groq (as of Oct 2026, check each limit). No paid research tool.

## Build notes
- Quote verification is a plain substring test in code, not a model judgement.
- Tests: a page fixture and a model answer containing one invented quote; assert it is dropped.
