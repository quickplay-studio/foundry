---
name: regulatory-screen
title: Regulatory Screen
department: legal
function: compliance
autonomy: human
stage: validate
builds_on: []
breaks_into: [read-the-idea, check-regulated-areas, set-the-flag]
replaces: "a regulatory scoping call with a solicitor, roughly one to two hours of fees"
runs_on: github
status: ready
---

# Regulatory Screen

Flag ideas that touch regulated ground (money, health, children, gambling) before any work starts; you decide.

This is the first job on every venture. Nothing else in Legal, and no build work, starts until Charlie has read the flag.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints (nothing regulated without a human and a solicitor)
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof
- `ventures/<slug>/idea.json`: the raw idea, if the brain is thin

## Inputs
- Venture slug. The MVP scope, who the user is, how the product earns, what data it holds, whether users talk to each other.
- Any earlier flag in `board.json` (a re-run after the scope changes replaces it).

## Steps
1. Read the brain and idea. Write five plain facts: what it does, who uses it, what it charges, what personal data it holds, whether users can post or message.
2. For each area below, ask the question, name the source, and give area-flag clear, caution or stop with a one-line reason:
   - Financial services: does it advise on, arrange, lend, broker, hold or move money, or promote investments or crypto? FCA Handbook PERG perimeter guidance, FSMA 2000 financial promotions rule, Payment Services Regulations 2017, Money Laundering Regulations 2017. Check the FCA Register if a named firm is involved.
   - Health: does it diagnose, triage, advise on treatment or dosing, or process health data? MHRA guidance on software as a medical device, NHS Digital Technology Assessment Criteria, CQC scope, ASA health claims rules.
   - Children: aimed at, or likely to be used by, under-18s? ICO Children's code, Online Safety Act 2023 child safety duties, Apple Kids and Google Play Families policies.
   - Gambling and prizes: betting, gaming, lotteries, loot boxes, paid prize draws? Gambling Act 2005 and Gambling Commission licensing.
   - User-generated content or messaging: Online Safety Act 2023, Ofcom duties for user-to-user services.
   - Special category or large-scale personal data, profiling, automated decisions: UK GDPR Article 9 and 22, ICO guidance.
   - Legal, tax or accounting advice: Legal Services Act 2007 reserved activities, HMRC anti-money-laundering supervision.
   - Energy, telecoms, lettings, recruitment, age-restricted goods: Ofgem, Ofcom, Estate Agents Act 1979 and Tenant Fees Act 2019, Employment Agencies Regulations 2003, CAP Code age-restricted rules.
   - Data sourcing: does the product depend on data or scraping that a site's terms forbid? Hand to `licence-audit`.
3. Read the current official page for any area marked caution or stop using Firecrawl (gov.uk, fca.org.uk, ico.org.uk, gamblingcommission.gov.uk, mhra pages on gov.uk). Cite the page and the date read. Do not rely on memory for thresholds.
4. Set the overall flag to the worst area flag. Stop: the product itself is a regulated activity or aimed at children or gambling. Caution: adjacent to regulated ground or needs a design limit (for example information only, never a recommendation). Clear: no area triggers.
5. If a model fails or an official page cannot be read, set caution with reason "screen incomplete". Never return clear on a failed check.
6. Write the output and set the `board.json` job entry to `waiting-on-human` with the flag.

## Output
- `ventures/<slug>/clear/regulatory-screen.md`: first line `FLAG: clear`, `FLAG: caution` or `FLAG: stop`, then the reason in two sentences, then a table (area, question, source, finding, area-flag), then the design limits that would keep a caution inside the line, then sources read with dates.
- `ventures/<slug>/clear/regulatory-screen.json`: `{flag, reason, areas: [{area, source, finding, flag}], checked_on}`. Read by the audit and the dashboards.
- Not legal advice. Drafts are checked by Charlie or a solicitor before use.

## The ladder
- Human-led: Charlie reads the one-page brief and sets the gate. A stop ends the venture unless he overrides in writing with a solicitor's note.
- Human-assisted: the job runs on every new `idea.json`, then holds. A caution passes forward only with the design limits copied into `brain.md`.
- Fully autonomous: not allowed. The free model only drafts the table; the flag always waits for Charlie.

## The human
What stays with Charlie: reading the flag, accepting any design limit, overriding a stop, and paying a solicitor for a regulated idea. He also checks any outside-interests clause in his own employment contract.

## Tools
Free first. Firecrawl free tier (500 credits as of Oct 2026, check the limit) to read official pages. Gemini 2.5 Flash, then Groq, for the table. FCA Register and Companies House free search for named firms. No paid tools.

## Build notes
- Runs in the `launch` workflow right after the audit, before any other Legal job. Model chain in `foundry.util`; the fallback is a keyword list (loan, invest, crypto, diagnose, symptom, kids, bet, prize, casino) that can only raise a flag to caution or stop.
- Tests offline: fixtures for a clear idea, a caution idea and a stop idea, plus a model failure that must return caution.
- Re-run whenever `brain.md` scope changes. Dated reads make stale rules visible; re-read any source older than 90 days.
