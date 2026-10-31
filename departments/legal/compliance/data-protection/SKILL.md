---
name: data-protection
title: Data Protection
department: legal
function: compliance
autonomy: assisted
stage: clear
builds_on: []
breaks_into: [map-the-data, set-lawful-basis, check-ico-fee-and-dpia, set-retention]
replaces: "a data protection consultant's data map and registration advice"
runs_on: github
status: ready
---

# Data Protection

UK GDPR basics: lawful basis, data map, ICO registration need, retention.

Produces the facts the privacy policy is written from. If the data map is wrong the policy is wrong.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof
- `ventures/<slug>/clear/regulatory-screen.json`: special category data, children, user-generated content flags

## Inputs
- The MVP scope, sign-up flow, payment route, analytics and email tools planned, hosting and database provider, and whether users under 18 are likely.
- After the build, the repo schema and third-party calls (re-run to compare plan against reality).

## Steps
1. List every piece of personal data the product will hold or send: identifiers, contact details, payment references, device and usage data, content users enter, cookies and similar tech. For each: purpose, source, who sees it, where stored, which processor handles it.
2. Mark special category data (health, biometrics, ethnicity, beliefs, sex life, trade union) and criminal records data. UK GDPR Article 9 needs a further condition; if found, set flag caution or stop and tell the regulatory screen.
3. Set a lawful basis per purpose from the ICO's lawful basis guidance: contract for delivering the service, legitimate interests for security and basic analytics (with a short balancing note), consent for marketing and non-essential cookies, legal obligation for tax records. Never default everything to consent.
4. Check cookies and marketing: PECR rules on cookies and electronic marketing (ICO guidance), including soft opt-in limits for email.
5. ICO fee: run the ICO's "Do I need to pay a data protection fee?" self-assessment logic against the venture. Record the answer, the tier and the current fee read from ico.org.uk. If a fee applies, the venture owner (Charlie or a company) pays it.
6. DPIA screen: use the ICO list of processing that needs a data protection impact assessment (large-scale profiling, special category data, children, tracking). If any apply, write a short DPIA draft or flag stop.
7. Processors: list each (hosting, database, email, analytics, payments, AI model providers). Check each provider's data processing terms exist and where data goes. International transfers need the UK IDTA, the UK Addendum to the EU SCCs, or an adequacy route (such as the UK-US data bridge for certified firms); read the current ICO guidance.
8. Children: if likely accessed by under-18s, apply the ICO Children's code standards and the age rule for consent (13 in the UK, Data Protection Act 2018 section 9).
9. Set retention per data type with a delete trigger, and the plan for access, deletion and export requests (one month to answer) and breach reporting (72 hours to the ICO if risk to people). Check the Data (Use and Access) Act 2025 changes to UK GDPR for anything that applies.
10. Never send real personal data to a free model tier; free tiers may use inputs for training. Use placeholders.

## Output
- `ventures/<slug>/clear/data-protection.md`: first line `FLAG: clear`, `FLAG: caution` or `FLAG: stop`, then data map table, lawful basis per purpose, ICO fee answer, DPIA screen, processors and transfers, retention schedule, rights and breach plan, sources read with dates.
- `ventures/<slug>/clear/data-map.json`: structured rows that `privacy-policy` reads.
- Not legal advice. Drafts are checked by Charlie or a solicitor before use.

## The ladder
- Human-led: Charlie fills the ICO checklist and writes the data map by hand.
- Human-assisted: the default. The job drafts the map and bases as a draft pull request; Charlie confirms what the product really collects.
- Fully autonomous: only the re-run diff against the repo schema, which raises a caution if new data appears.

## The human
What stays with Charlie: confirming the data map matches the product, paying the ICO fee if due, signing processor terms, deciding on a DPIA, and a solicitor or data protection adviser for special category or children's data.

## Tools
Free first. Firecrawl free tier (500 credits as of Oct 2026, check the limit) to read ICO pages; the ICO self-assessment tools by hand where no API exists; Gemini 2.5 Flash or Groq for drafting the table from the brain. No paid tools.

## Build notes
- The data map is the shared contract with `privacy-policy`; keep field names stable.
- On a failed model, write the map skeleton from the brain's keywords and set caution.
- Re-run after build and on every new third-party service. Tests offline with fixture brains.
