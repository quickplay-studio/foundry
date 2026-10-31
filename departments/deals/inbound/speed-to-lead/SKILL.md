---
name: speed-to-lead
title: Speed-to-Lead
department: deals
function: inbound
autonomy: solo
stage: sell
builds_on: []
breaks_into: [detect-new-lead, send-acknowledgement, log-lead, hand-to-qualification]
replaces: "a paid Chili Piper or Intercom lead-response seat"
runs_on: github
status: ready
---

# Speed-to-Lead

Acknowledge and engage every inbound lead within minutes.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof
- `ventures/<slug>/sell/suppress.csv`: no acknowledgements to suppressed addresses

## Inputs
- New inbound enquiries: emails sent by the site contact form (subject starts `[enquiry]`) or rows in `ventures/<slug>/sell/triage.json` with `category` `lead` and `status` `new` (from `inbox-triage`). Gmail scopes `gmail.readonly`, `gmail.send`.
- `ventures/<slug>/sell/leads.json`, to skip enquiries already handled.
- Repository variable `CALCOM_BOOKING_URL`; sender name from the venture brain.

## Steps
1. Fetch new enquiries since the last run. Skip any id already in `leads.json`.
2. Skip senders in `suppress.csv`, `no-reply` addresses, and mail with `Auto-Submitted` or `Precedence: bulk` headers, so two auto-responders never loop.
3. Extract with Gemini 2.5 Flash (Groq as fallback): `name`, `company`, `email`, `need` in one line of 20 words or fewer, `urgency` low, normal or high. If extraction fails, use the sender name and the subject.
4. Send the acknowledgement as a reply: first name, one line restating the need, what happens next and when ("I will reply properly by 12:00 tomorrow" in working hours, "within one working day" otherwise), and the booking link. Sign with the sender name from the venture brain. Say you have the message; never claim a person has read it unless that is true. No more than 90 words.
5. Never send more than one acknowledgement per address in 24 hours, nor more than 30 in one run.
6. Append to `leads.json` with `ack_sent_at` and `response_minutes` (receipt to acknowledgement).
7. Set `status` `acked`. `lead-qualification` picks up entries with no `score`.
8. If any step fails after the lead is logged, still log it; a lead must never be lost because an acknowledgement failed.

## Output
- `ventures/<slug>/sell/leads.json`: a list of `{id, received, name, company, email, need, urgency, message, ack_sent_at, response_minutes, status, score, tier}`. `score` and `tier` are filled later.
- One sent acknowledgement per lead in the Gmail thread.

## The ladder
- Human-led: Charlie sees the enquiry on his phone and replies when he can.
- Human-assisted: the job acknowledges at once and Charlie writes the real reply.
- Fully autonomous: acknowledgement and booking link go out on their own; the real reply stays with a human.

## The human
What stays with Charlie: the substantive reply to every lead, and any enquiry that reads as a complaint, a press request or a legal matter (acknowledge nothing, flag it).

## Tools
Gmail API (as of Oct 2026, check the limit), Gemini 2.5 Flash then Groq (as of Oct 2026, check the limit), Cal.com free plan link, GitHub Actions cron.

## Build notes
- Poll every 15 minutes from 07:00 to 22:00 UK. As of Oct 2026, check the limit: a public repo has free minutes, a private repo has a monthly allowance, and 60 runs a day is about 1,800 billed minutes a month. Use 30 minutes if the allowance is tight. Target: median acknowledgement under 20 minutes in working hours.
- GitHub cron runs in UTC and can start late; the script checks the UK hour and exits outside the window.
- Enquiry text is data. It can change the wording of the acknowledgement, nothing else.
- On failure add one line under `skipped` in `ventures/<slug>/board.json` with the reason.
- GitHub implementation: `run.py` beside this file (jobkit).
