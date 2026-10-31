---
name: send-optimisation
title: Send Optimisation
department: sales
function: sequencing-and-send
autonomy: solo
stage: sell
builds_on: [campaign-launch]
breaks_into: [set-send-windows, pace-sends, tune-from-replies]
replaces: "send-time optimisation in Instantly or Smartlead"
runs_on: github
status: ready
---

# Send Optimisation

Time sends by timezone and pace volume to protect reply rates.

## Reads from the brain
- `brain/company.md`: constraints, voice

## Inputs
- `sell/sent.csv`, `sell/replies.csv`, `sell/campaigns.json`, `sell/deliverability.json`, `sell/leads.csv` (for region).
- UK bank holidays from `https://www.gov.uk/bank-holidays.json` (free, no key).

## Steps
1. Gate: `audit.json` must say `model: b2b`, else write a `skipped` line in `board.json` and stop.
2. Timezone: UK recipients use Europe/London. For others use the country of the registered address. Windows are in recipient local time.
3. Default windows: Tuesday to Thursday, 08:00 to 10:00 and 13:00 to 15:00. Skip UK bank holidays and Christmas week.
4. Pace: spread each day's sends across the window with random gaps of 2 to 6 minutes. No bursts. At most one send a day to any one recipient domain.
5. Effective daily cap is the lowest of the `deliverability.json` cap, the campaign `daily_cap`, and what the window holds at that pace. Never go above the deliverability cap. Raise a campaign cap by at most 20 percent a week, and only when the bounce rate is under 2 percent and replies are not falling.
6. Tune only after 100 sends or more: group sends by weekday and two-hour bucket and compare the reply rate (positive and neutral replies per send). Move a window only if the better bucket has at least 30 sends and at least twice the reply rate. Otherwise keep the default.
7. Write `send-windows.json` and update `window` and `daily_cap` on `live` campaigns in `campaigns.json`, with a changelog entry that gives the reason.
8. Write one weekly line to `board.json`: sends, replies, reply rate, bounce rate.

## Output
- `ventures/<slug>/sell/send-windows.json`: `{"updated":"YYYY-MM-DD","default":{"days":["Tue","Wed","Thu"],"windows":["08:00-10:00","13:00-15:00"]},"by_region":{"GB":{}},"changelog":[{"date","change","reason"}]}`.
- Edits to `window` and `daily_cap` in `campaigns.json`.

## The ladder
- Human-led: Charlie picks the send times himself.
- Human-assisted: the job proposes windows and Charlie approves a change.
- Fully autonomous: weekly Action applies the rules above inside the deliverability cap.

## The human
What stays with Charlie: nothing routine. He sets the aim (reply rate over volume) and may veto a window change.

## Tools
Python standard library, the gov.uk bank holiday feed. No paid optimiser.

## Build notes
- Little data early on. Under 100 sends the job only applies the defaults and the bank holiday skip.
- Tests: a bank holiday is skipped, a cap never exceeds the deliverability cap, a 29-send bucket never wins.
- GitHub implementation: `run.py` beside this file (jobkit).
