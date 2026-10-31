---
name: campaign-orchestration
title: Campaign Orchestration
department: sales
function: sequencing-and-send
autonomy: solo
stage: sell
builds_on: [cold-email-drafting, linkedin-messaging]
breaks_into: [choose-touch-order, assign-leads, set-stop-rules, write-campaigns-json]
replaces: "the cadence builder of Outreach, Salesloft or Lemlist"
runs_on: github
status: ready
---

# Campaign Orchestration

Order email, LinkedIn and phone touches into one multi-channel cadence.

## Reads from the brain
- `brain/company.md`: constraints, voice
- `ventures/<slug>/sell/icp.md`: segments and offer

## Inputs
- `sell/leads.csv` (tier, `subscriber_type`, `email_status`, `suppressed`).
- `sell/sequences/email-*.md`, `linkedin-*.md`, and `call-*.md` or `video-*.md` where they exist.
- `sell/deliverability.json` for the daily cap.

## Steps
1. Gate: `audit.json` must say `model: b2b`, else write a `skipped` line in `board.json` and stop.
2. One campaign per segment per tier. Tier A: email, LinkedIn, video, call. Tier B: email and one LinkedIn note. Tier C and X: no campaign.
3. Default cadence, in days from the lead's start: day 0 email 1; day 1 LinkedIn connect (A); day 3 email 2; day 5 LinkedIn DM (A); day 8 email 3, with the video link for A; day 10 call (A, after TPS and CTPS screening); day 15 email 4. Move weekend days to the Monday.
4. Email touches go only to leads with `subscriber_type=corporate`, `email_status` of `valid` or `likely`, `suppressed=no`, and a non-blank `email`. Anyone else gets non-email touches, or waits.
5. Stop rules, applied to every channel at once: a reply, an unsubscribe or "no", a hard bounce, a booked meeting, or `suppressed=yes`.
6. Cohorts: start leads in weekly batches sized so that daily sends stay under `deliverability.json` `daily_cap`. Assign a lead to one cohort once.
7. Write `campaigns.json` with `status: "draft"`. Never set a status beyond `draft`; campaign-launch does that.
8. If a touch's asset is missing (for example no video script), drop that touch from the cadence and name it in `missing_assets` so the gap is visible.

## Output
- `ventures/<slug>/sell/campaigns.json`:
```
{"slug":"<slug>","generated":"YYYY-MM-DD","campaigns":[{"id":"<segment>-A","segment":"","tier":"A",
"sequence":"sequences/email-<segment>.md","touches":[{"day":0,"channel":"email","step":1},
{"day":1,"channel":"linkedin","step":"connect","by":"charlie"}],"lead_ids":["L0001"],
"cohort_size":20,"stop_on":["reply","unsubscribe","bounce","meeting"],"daily_cap":20,
"window":"Tue-Thu 08:00-10:00 Europe/London","status":"draft"}],"missing_assets":[]}
```

## The ladder
- Human-led: Charlie plans the touches in a spreadsheet.
- Human-assisted: the job proposes the cadence, Charlie changes the day offsets.
- Fully autonomous: regenerates drafts when leads or sequences change. Nothing sends until campaign-launch is merged.

## The human
What stays with Charlie: nothing at this step beyond reading the draft; approval happens in campaign-launch.

## Tools
Python standard library. Gemini 2.5 Flash only to explain a cadence choice in the PR. No paid sequencer.

## Build notes
- Deterministic: the same inputs give the same file. Tests: a suppressed lead gets no touch, an individual gets no email, weekends shift.
- Lead ids in a campaign are frozen once it is `live`; new leads join a new cohort.
- GitHub implementation: `run.py` beside this file (jobkit).
