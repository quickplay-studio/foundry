---
name: tax-registration
title: Tax Registration
department: legal
function: formation
autonomy: assisted
stage: clear
builds_on: [entity-and-structure]
breaks_into: [list-registrations, check-vat, build-deadline-calendar, write-checklist]
replaces: "an accountant's set-up and deadline checklist, usually a small fixed fee"
runs_on: github
status: ready
---

# Tax Registration

HMRC registrations, VAT thresholds and deadlines for the chosen structure.

Charlie logs in and registers. The job tells him what, when and what to have ready.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof (who pays, from which countries)
- `ventures/<slug>/clear/entity-and-structure.md` and the choice recorded in `board.json`

## Inputs
- The chosen structure: hold off, sole trader or limited company.
- Date of first sale or first trading income, expected 12-month turnover, customer countries, sales route (own checkout, payment provider, app store), whether anyone is to be employed or paid as a contractor.

## Steps
1. If structure is `hold off`: confirm income stays under the HMRC trading allowance (read current figure on gov.uk) and write when to revisit and end the job here.
2. Sole trader: Self Assessment registration (UTR) by 5 October after the tax year trading began; keep records; online return by 31 January after the tax year ends; payments on account on 31 January and 31 July; Class 4 National Insurance. Read the gov.uk "Set up as a sole trader" page and rates for the current year.
3. Limited company: Corporation Tax registration with HMRC within three months of starting trading (the company UTR letter); Companies House confirmation statement every 12 months; annual accounts to Companies House and a Company Tax Return to HMRC (read the current deadlines on gov.uk); PAYE if directors or staff are paid; director identity verification at Companies House.
4. VAT: read the current registration and deregistration thresholds and the rolling 12-month test and the 30-day look-ahead test. Digital sales to consumers are VAT-able in the UK at the standard rate. Voluntary registration, the Flat Rate Scheme and Making Tax Digital for VAT apply once registered. Note sales to EU and other overseas customers need separate VAT checks. If an app store or payment provider acts as merchant of record, record who accounts for VAT and mark the question open for an accountant.
5. Making Tax Digital for Income Tax: read the phased income thresholds and start dates for sole traders (the first phase starts April 2026) and whether this venture's income puts Charlie in scope; list HMRC-recognised software, including free options, and choose the lowest-cost match.
6. Other registrations to check: ICO data protection fee (see `data-protection`), and an employer's registration if staff are hired.
7. Build a dated calendar for the structure: what, deadline, where, who. Produce JSON for the back-office budget jobs.
8. Write a checklist of what Charlie needs for each registration (National Insurance number, Government Gateway sign-in, company details). The job never logs in or creates an account.
9. Flag: stop if an overdue registration is likely (income already above a threshold); caution if VAT is within 20 percent of the threshold or a merchant-of-record question is open; else clear.

## Output
- `ventures/<slug>/clear/tax-registration.md`: first line `FLAG: clear`, `FLAG: caution` or `FLAG: stop`, then registrations needed with deadlines, VAT position, Making Tax Digital position, the checklist, open questions for an accountant, and sources read with dates.
- `ventures/<slug>/clear/tax-deadlines.json`: `[{what, due, where, repeats}]`, read by `cash-flow-forecasting`.
- Not legal advice. Drafts are checked by Charlie or a solicitor before use.

## The ladder
- Human-led: Charlie follows HMRC guidance and registers himself.
- Human-assisted: the default. The job prepares the checklist and calendar as a draft pull request; Charlie registers.
- Fully autonomous: the calendar and VAT threshold monitor only, run weekly from `revenue-reporting` figures, raising caution near a threshold.

## The human
What stays with Charlie: every registration and filing (his own identity), paying tax, choosing software, and an accountant for VAT with overseas sales, employees, or anything unusual.

## Tools
Free first. Firecrawl free tier (500 credits as of Oct 2026, check the limit) for gov.uk and HMRC pages; Companies House free service for company deadlines; Gemini 2.5 Flash or Groq to draft; dates in code. No paid tools.

## Build notes
- Thresholds and deadlines are read from gov.uk each run and written with a "read on" date; nothing is hard-coded from memory.
- Re-run when the structure changes or revenue passes 70 percent of the VAT threshold.
- Tests offline with fixture pages for each structure.
