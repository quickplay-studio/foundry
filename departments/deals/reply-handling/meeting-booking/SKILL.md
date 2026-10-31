---
name: meeting-booking
title: Meeting Booking
department: deals
function: reply-handling
autonomy: solo
stage: sell
builds_on: [hot-lead-routing]
breaks_into: [offer-slots, confirm-booking, send-reminder, chase-no-shows]
replaces: "a paid Calendly or Chili Piper plan plus a rep chasing no-shows"
runs_on: github
status: ready
---

# Meeting Booking

Offer slots, book the call, chase no-shows.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof
- `ventures/<slug>/sell/suppress.csv`: no messages to suppressed addresses

## Inputs
- `ventures/<slug>/sell/replies.json` rows with `status` `routed`, and the matching `pipeline.csv` rows.
- Cal.com API key in secret `CALCOM_API_KEY`; repository variable `CALCOM_BOOKING_URL`.
- Gmail scopes `gmail.send` and `gmail.readonly`; secrets as in `reply-classification`.
- `ventures/<slug>/sell/meetings.json`: a list of `{deal_id, start, end, attendee_email, join_url, status, consent, transcript}`. `status` is `offered`, `booked`, `held`, `no_show` or `cancelled`; `consent` is `yes`, `no` or `unknown`.

## Steps
1. For each routed row with no meetings entry, read three free slots in the next five working days from the Cal.com API (check its current slots endpoint).
2. Send one reply in the thread: two lines, the three slots written in UK time, the booking link, and this sentence: "I would like to record the call for notes; tell me if you would rather I did not." Add a `meetings.json` entry with `status` `offered`, `consent` `unknown`.
3. On every run list Cal.com bookings. Match each to a deal by attendee email. Set the entry to `booked` with `start`, `end`, `join_url`, and set the pipeline `stage` to `meeting_booked`.
4. If the prospect's reply or booking note agrees to recording, set `consent` `yes`; if it refuses, `no`. Otherwise leave `unknown`.
5. Send one reminder 24 hours before `start`, with the join link, only to `booked` entries.
6. Thirty minutes after `start`, if `status` is still `booked`, do not guess: open or update one GitHub issue asking Charlie to set `held` or `no_show`.
7. When `status` becomes `no_show`: send one message at once offering two new slots, and a last one after three working days. After that set the pipeline `stage` to `dormant`, `next_step_date` 30 days on, and stop.
8. A `cancelled` booking gets one offer of new slots; no second offer.

## Output
- `ventures/<slug>/sell/meetings.json` as above.
- Sent messages in the Gmail thread; pipeline `stage`, `next_step`, `next_step_date` updated.
- A GitHub issue for any meeting whose attendance is unknown.

## The ladder
- Human-led: Charlie proposes times by email and logs the booking himself.
- Human-assisted: the job offers slots and tracks bookings, Charlie marks attendance.
- Fully autonomous: attendance comes from Cal.com or the recording; Charlie only takes calls.

## The human
What stays with Charlie: marking `held` or `no_show`, and saying yes or no to recording on the call itself.

## Tools
Cal.com free plan and API (as of Oct 2026, check the limit), Gmail API (as of Oct 2026, check the limit), GitHub Actions every 30 minutes, GitHub issues. No model needed.

## Build notes
- Cal.com webhooks need a server, so the job polls. Do not add one.
- Booking times are stored in UTC and written to people in UK time.
- Never record without consent; `call-capture` reads the `consent` field.
- On failure add one line under `skipped` in `ventures/<slug>/board.json` with the reason.
