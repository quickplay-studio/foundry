---
name: entity-and-structure
title: Entity and Structure
department: legal
function: formation
autonomy: human
stage: clear
builds_on: []
breaks_into: [read-venture-facts, compare-options, price-and-time-it, write-brief]
replaces: "an accountant's structure advice meeting, usually free or a modest fixed fee"
runs_on: github
status: ready
---

# Entity and Structure

Sole trader, limited company or hold off: options, costs and timing laid out; you choose.

Per the deploy order this runs for the first venture that has revenue. Until then ventures stay personal projects and the brief says `hold off`.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints (entity: none yet; free tools only until revenue)
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof (expected revenue, who pays, risk)
- `ventures/<slug>/clear/regulatory-screen.json`: a regulated flag changes the advice

## Inputs
- Expected first-year revenue and profit, from the brain and `budget.json`.
- Whether the venture takes consumer money, holds data, signs B2B contracts, sells an app, or may take investment or partners.
- Whether Charlie already has other income (affects tax bands) and whether he wants his name public. Ask him; do not assume.

## Steps
1. State the facts that decide structure: revenue, profit, liability risk, public name exposure, B2B contract needs, need for an app store account, outside investment.
2. Describe three options with source-checked costs and duties:
   - Hold off: trading income under the HMRC trading allowance (check the current figure on gov.uk, currently 1,000 pounds a year) needs no registration. Revisit once sales approach that amount.
   - Sole trader: register for Self Assessment with HMRC by 5 October after the tax year trading began; personal unlimited liability; income tax and Class 4 National Insurance on profits; the business name rules on gov.uk; the owner's name and address may be visible to customers and stores.
   - Private limited company: incorporate on Companies House (read the current incorporation fee, annual confirmation statement fee, and director identity verification rule); a separate legal person; Corporation Tax registration with HMRC within three months of starting; accounts to Companies House and HMRC; directors' and persons with significant control details are public (a registered office service can hide a home address); extra admin and costs.
3. Run a simple comparison: tax and National Insurance on profits of 5,000, 20,000 and 50,000 pounds under each option, using rates read from gov.uk "Rates and thresholds" for the current tax year (code, not model arithmetic). Show take-home and admin cost, and state the rates date.
4. Name the triggers to move up: profit above the point where a company is cheaper (computed above), a contract that needs a company, a liability the owner does not want to carry, VAT approaching the threshold (currently 90,000 pounds of taxable turnover, check on gov.uk), or a partner or investor.
5. Note the practical effects: payment providers and app stores ask for legal entity details (Apple's organisation account needs a legal entity; individual accounts show a personal name), trade mark and domain ownership should match the chosen owner, and a later move from sole trader to company needs a transfer of assets and contracts (cost, tax, and time).
6. Check Charlie's side: any outside-interests clause in his employment contract, and whether the idea sits near regulated ground (see `regulatory-screen`).
7. Write a one-page brief: recommendation with reasons, the alternative, the cost of each, the date to act, and the questions only Charlie can answer. Then stop.

## Output
- `ventures/<slug>/clear/entity-and-structure.md`: first line `DECISION NEEDED: hold off | sole trader | limited company` (the recommendation), then the three-option table, the tax comparison with rates date, triggers, open questions, and sources read with dates.
- Not legal advice. Drafts are checked by Charlie or a solicitor before use.

## The ladder
- Human-led: Charlie decides with an accountant.
- Human-assisted: the default. The job prepares the brief and the numbers; Charlie chooses and registers himself.
- Fully autonomous: not allowed. The job never registers, signs or pays.

## The human
What stays with Charlie: the choice, the registration with HMRC or Companies House (his own sign-in and identity checks), paying any fee, and an accountant for his full tax position.

## Tools
Free first. Firecrawl free tier (500 credits as of Oct 2026, check the limit) for gov.uk, HMRC and Companies House guidance pages; a small Python calculator for the comparison; Gemini 2.5 Flash or Groq to write the brief. No accounts are created by the job.

## Build notes
- Tax rates come from gov.uk each run, never from the model. Print the tax year used.
- Writes the chosen structure to `ventures/<slug>/board.json` only after Charlie records it; `tax-registration`, `terms-of-service` and `bank-and-payments-setup` read it.
- Tests offline with fixture rate tables.
- GitHub implementation: `run.py` beside this file (jobkit).
