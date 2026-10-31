---
name: deliverability
title: Deliverability
department: sales
function: sequencing-and-send
autonomy: solo
stage: sell
builds_on: []
breaks_into: [check-dns-auth, ramp-volume, watch-bounce-rate, pause-on-risk]
replaces: "Mailreach or Warmup Inbox, or the warm-up feature of Instantly"
runs_on: github
status: ready
---

# Deliverability

Keep sending domains healthy: warm-up, spam tests, inbox rotation.

## Reads from the brain
- `brain/company.md`: constraints (free tools, nothing outside the law)

## Inputs
- `sell/mailboxes.json`, owned and listed by Charlie: `[{"address","domain","first_send","spam_score","daily_limit"}]`. The job never creates a mailbox or account.
- `sell/sent.csv`, `replies.csv`, `bounces.csv` once sending starts.

## Steps
1. Gate: `audit.json` must say `model: b2b`, else write a `skipped` line in `board.json` and stop. No `mailboxes.json`: write `skipped: no sending mailbox` and stop.
2. Start this job on day one of the sell stage so the warm-up clock runs while the list is built.
3. DNS: query Google DNS over HTTPS for TXT records. SPF (`v=spf1` including the mail provider), DKIM (selector `google` for Workspace; skip for @gmail.com, Google signs it), DMARC at `_dmarc.<domain>` (start at `p=none`, move to `quarantine` after a clean fortnight). A missing record is `fail`, with the exact record for Charlie to add at his registrar.
4. Keep cold email off the venture's main address. The free route is a separate Gmail address Charlie owns. A sending domain is a spend that Charlie approves.
5. Warm-up is a volume ramp, never a pod or a fake-reply network. Daily cap per mailbox by days since `first_send`: days 1 to 7: 5; 8 to 14: 10; 15 to 21: 20; 22 to 28: 30; after that 40. Never above the provider's limit (as of Oct 2026, check the limit). Early sends go to the best tier A leads. Charlie also sends a few real emails from the mailbox each week to people he knows.
6. Spam test: before launch and after any copy change Charlie sends email 1 to a free spam-test inbox (mail-tester.com has a free daily allowance; as of Oct 2026, check it) and records the score in `mailboxes.json`. Below 8 out of 10 blocks launch.
7. Monitor daily: bounce rate and negative-reply rate over the last 50 sends, and reply rate. Raise the cap one step only while bounces stay under 2 percent.
8. Pause: a bounce rate of 3 percent or more on the last 50 sends, any "this is spam" reply, or a Gmail warning sets `pause: true`, writes an alert line to `board.json`, and campaign-launch's sender stops.
9. Rotation: with two or more owned mailboxes, split each day's volume evenly under each cap. One mailbox owns a lead for the whole sequence, so threads stay intact.

## Output
- `ventures/<slug>/sell/deliverability.json`: `{"checked_on":"YYYY-MM-DD","mailboxes":[{"address","spf","dkim","dmarc","warm_day","daily_cap","bounce_rate","spam_score","status"}],"daily_cap":N,"pause":false}`.

## The ladder
- Human-led: Charlie checks DNS and sends warm-up mail himself.
- Human-assisted: the job checks and sets caps, Charlie fixes DNS and runs the spam test.
- Fully autonomous: daily Action sets caps and pauses; DNS edits and the spam test stay with Charlie.

## The human
What stays with Charlie: DNS edits, the spam test, resuming after a pause, and the Google Postmaster Tools check (free, custom domain only).

## Tools
Google DNS over HTTPS, mail-tester.com free allowance, Google Postmaster Tools, Gmail API quota. No paid warm-up tool.

## Build notes
- Build `foundry/sales/deliverability.py`. Tests: DNS fixtures for pass and fail, and a bounce series that crosses 3 percent.
- Read-only on `sent.csv`; it only writes `deliverability.json` and the alert line.
