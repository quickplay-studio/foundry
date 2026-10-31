---
name: entity-compliance
title: Entity Compliance
department: back-office
function: records
autonomy: human
stage: run
builds_on: [entity-and-structure]
breaks_into: [list-obligations, check-gov-uk-dates, build-checklist, remind-charlie]
replaces: "a company secretarial service, roughly 100 to 300 pounds a year"
runs_on: github
status: ready
---

# Entity Compliance

Filings and obligations per entity, tracked and scheduled; you file. The job produces a one-page dated brief and stops. Nothing is ever filed, registered or paid by an agent. Nothing here is legal or tax advice.

## Reads from the brain
- `brain/company.md`: the Entity line. As of Oct 2026 it says none; ventures run as personal projects until the first one makes money, then Legal `entity-and-structure` decides.
- `ventures/<slug>/brain.md`: money, for whether the venture has taken any revenue yet

## Inputs
- `office/records/entities.json`: written by Charlie after `entity-and-structure`: `[{"id", "type": "sole-trader|company|other", "name", "start_date", "year_end", "vat_registered", "has_staff", "ventures": []}]`.
- `ventures/*/finance/payments.json` and `office/finance/revenue/*.json`: to see when trading began and to total the last twelve months.
- `office/records/sources.json`: gov.uk and HMRC guidance page URLs Charlie has confirmed. The job reads no URL that is not in this file.
- `office/records/compliance.json`: the register of obligations and dates already found.

## Steps
1. If `entities.json` is empty and no venture has revenue, write the brief as "no entity, nothing due" with the one watch item: when a venture takes its first payment, tell Charlie to ask Legal `entity-and-structure` and to check whether he must register as self-employed with HMRC. Stop.
2. For each entity, list the obligation kinds that apply. Starting rules only, always confirmed on the page in step 3:
   - Sole trader: register for Self Assessment (by 5 October in the business's second tax year); online return and balancing payment by 31 January; payments on account 31 January and 31 July; the trading allowance limit.
   - Company: confirmation statement every 12 months; annual accounts 9 months after year end; Corporation Tax return 12 months and payment 9 months and 1 day after the accounting period ends.
   - Any entity: VAT registration when rolling 12-month taxable turnover passes the threshold (register within 30 days); PAYE if staff; the data protection fee check with Legal `data-protection`.
3. Read the matching pages from `sources.json` through Firecrawl (free tier; as of Oct 2026, check the limit) and compare each rule and each limit with `compliance.json`. Never use a threshold from memory or from this file. A mismatch is flagged `dates-changed`.
4. Compute each due date from `start_date` and `year_end`. For VAT, compute rolling 12-month turnover from the revenue files and flag when it passes 70 percent of the threshold read from the page.
5. Build the checklist: obligation, entity, due date, days left, where to do it (the page URL), what to have ready, and who can help (accountant, Companies House or HMRC helpline). Soonest first.
6. Open a GitHub issue for each item due within 30 days and again within 7 days, labelled `compliance`, using `GH_TOKEN`. Close issues Charlie marks `done`.
7. Stop. The brief is the output; the filing is Charlie's.

## Output
- `office/records/compliance-brief.md`: one page, dated, ranked by due date, plain language.
- `office/records/compliance.json`: `[{"id", "entity", "kind", "due", "source_url", "checked_on", "status": "upcoming|due|done|dates-changed"}]`.
- GitHub issues as reminders. Skips go to `office/skipped.json`.

## The ladder
- Human-led: Charlie keeps his own calendar and checks gov.uk himself.
- Human-assisted: the job builds the register, Charlie files from it.
- Fully autonomous: refused for filing and tax. The agent only tracks, checks pages and reminds; that is the ceiling.

## The human
What stays with Charlie: deciding the structure, registering, filing every return and statement, paying every bill, and asking an accountant when unsure.

## Tools
Firecrawl free tier for the gov.uk and HMRC pages; Python stdlib; Gemini 2.5 Flash then Groq free tiers only to summarise a changed page in two lines; GitHub Actions monthly schedule plus weekly once an entity exists.

## Build notes
- One module, `foundry/compliance.py`. Tests offline with a stored page fixture: a changed threshold, a year end that moves a due date, no entity.
- The starting rules above are prompts to check, not a source of truth.
- GitHub implementation: `run.py` beside this file (jobkit).
