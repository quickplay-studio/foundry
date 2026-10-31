---
name: campaign-launch
title: Campaign Launch
department: sales
function: sequencing-and-send
autonomy: assisted
stage: sell
builds_on: [campaign-orchestration, email-verification]
breaks_into: [run-pecr-preflight, render-send-queue, send-seed-test, open-approval-pr]
replaces: "an Instantly or Smartlead subscription"
runs_on: github
status: ready
---

# Campaign Launch

Load finished campaigns into the sending platform with the right settings.

## Reads from the brain
- `brain/company.md`: voice, constraints, what we will not do (no unsolicited email outside the law)
- `ventures/<slug>/brain.md`: the venture name and reply address

## Inputs
- `sell/campaigns.json` (status `draft`), `sell/leads.csv`, `sell/suppression.csv`, `sell/sequences/email-*.md`, `sell/deliverability.json`.
- Secrets `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`, created and stored by Charlie.

## Steps
1. Gate: `audit.json` must say `model: b2b`, else write a `skipped` line in `board.json` and stop.
2. PECR preflight. All must pass or the job opens the pull request with the failures listed and sets nothing live. Cold email goes only to business addresses at corporate subscribers (limited companies, LLPs, PLCs, public bodies). It never goes to sole traders, partnerships, or free-mail addresses. Check: every recipient is `corporate`, `email_status` is `valid` or `likely`, `suppressed=no`; every rendered email names the sender and ends with the unsubscribe line; plain text, no tracking pixel.
3. Deliverability preflight: `deliverability.json` has `pause: false`, SPF, DKIM and DMARC pass for any custom sending domain, and the day's volume is within the warm-up `daily_cap`.
4. Render each lead's emails from the sequence and merge fields. Steps 2 to 4 reply in the same Gmail thread (`In-Reply-To`, `References`). Add `List-Unsubscribe: <mailto:<reply address>?subject=unsubscribe>`. Write `send-queue.csv`.
5. Send one rendered copy of each step to Charlie's own address as a seed test.
6. Open a pull request titled `launch: <slug> campaign <id>`: counts, the preflight table, three rendered samples, daily cap, send window and the kill rule (pause at a 3 percent bounce rate on the last 50 sends, or on any spam complaint). Merging it sets `status: "approved"`. Charlie's merge is the approval.
7. The scheduled sender (`sell-send` workflow, every 30 minutes inside the window) takes due rows up to the remaining daily cap. It re-checks `suppression.csv` and replies just before each send, calls the Gmail API `users.messages.send`, and appends to `sent.csv`. It reads the inbox for replies and bounces and appends to `replies.csv` and `bounces.csv`. The first send moves the campaign to `live`.

## Output
- `ventures/<slug>/sell/send-queue.csv`: `lead_id,campaign_id,step,send_after,to,subject,body,status`.
- `ventures/<slug>/sell/sent.csv`: `lead_id,campaign_id,step,channel,sent_at,message_id,thread_id`. Also `replies.csv`, `bounces.csv`.
- Updated `campaigns.json`. Deals `reply-classification` reads `replies.csv`.

## The ladder
- Human-led: Charlie sends from Gmail by hand.
- Human-assisted: the job preflights, renders and queues, Charlie merges. This is the working mode.
- Fully autonomous: not used. A campaign goes live only by Charlie's merge.

## The human
What stays with Charlie: creating the Google Cloud OAuth client (free), adding the three secrets, and merging each launch. Use scopes `gmail.send` and `gmail.readonly`. Set the consent screen to production for own use, or the refresh token lapses after 7 days in testing (check Google's current rules).

## Tools
Gmail API free quota. Consumer accounts have lower daily limits than Workspace (as of Oct 2026, check the limit); stay at the warm-up cap. A free-tier sending tool Charlie already holds is an alternative; name it in the PR. HubSpot free CRM optional by hand. No paid sequencer, no card.

## Build notes
- Build `.github/workflows/sell-send.yml` and `foundry/sales/send.py` (stdlib plus `requests`). Tests mock the Gmail API.
- Never log message bodies or tokens in Actions output.
- GitHub implementation: `run.py` beside this file (jobkit).
