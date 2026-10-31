---
name: email-verification
title: Email Verification
department: sales
function: enrichment
autonomy: solo
stage: sell
builds_on: [contact-enrichment]
breaks_into: [check-syntax-and-mx, filter-disposable-and-freemail, hunter-verify, apply-bounces]
replaces: "NeverBounce or ZeroBounce credits"
runs_on: github
status: ready
---

# Email Verification

Check every address before a single send goes out.

## Reads from the brain
- `brain/company.md`: constraints (nothing leaves unverified, free tools only)

## Inputs
- `sell/leads.csv`: rows with an `email` and a blank `email_status`, or `verified_on` older than 30 days.
- `sell/bounces.csv`: written by the campaign-launch sender (`lead_id,email,type,date`).
- Optional secret `HUNTER_API_KEY`.
- `sell/suppression.csv`.

## Steps
1. Gate: `audit.json` must say `model: b2b`, else write a `skipped` line in `board.json` and stop.
2. Syntax: lower-case, strip spaces and trailing punctuation, require one `@` and a valid domain. Fail means `invalid`.
3. Domain: ask Google DNS over HTTPS (`https://dns.google/resolve?name=<domain>&type=MX`). No MX and no A record means `invalid`.
4. Filter: domains on the in-repo `disposable-domains.txt`, and free-mail domains (gmail.com, outlook.com, hotmail, yahoo, icloud), are `invalid` for B2B. They are personal addresses and fail the PECR rule.
5. Hunter verifier on tier A, then B, while free credits last (as of Oct 2026, check the limit). Map `valid` to `valid`, `accept_all` to `risky`, `invalid` and `disposable` to `invalid`, `webmail` to `invalid`, `unknown` to `likely`. Without Hunter, an address that passes steps 2 to 4 is `likely`.
6. Do not probe with SMTP. It needs port 25, damages sender reputation and is blocked on most runners.
7. Bounces: for each hard bounce in `bounces.csv` set `email_status=bounced` and append the address to `suppression.csv` with reason `bounce`. A soft bounce twice in a row counts as hard.
8. Write `email_status` (`valid`, `likely`, `risky`, `invalid`, `bounced`) and `verified_on`. Campaign-launch sends only to `valid` and `likely`.
9. Write `verification.json`.

## Output
- Updated `ventures/<slug>/sell/leads.csv` and `ventures/<slug>/sell/suppression.csv`.
- `ventures/<slug>/sell/verification.json`: `{"checked":N,"valid":N,"likely":N,"risky":N,"invalid":N,"bounced":N,"hunter_credits_used":N,"date":"YYYY-MM-DD"}`.

## The ladder
- Human-led: Charlie runs each address through a free checker.
- Human-assisted: the job checks, Charlie reviews the `risky` rows.
- Fully autonomous: runs before each launch and daily on live campaigns for bounces.

## The human
What stays with Charlie: deciding whether to send to `risky` rows. Default is no.

## Tools
Google DNS over HTTPS, Hunter free plan, an in-repo disposable-domain list. No paid verifier.

## Build notes
- A `likely` address is not proven. The first 10 sends of a campaign act as the real test; the deliverability job reads the bounce rate.
- Tests: offline, DNS responses monkeypatched; cover a bounce adding to suppression.
- GitHub implementation: `run.py` beside this file (jobkit).
