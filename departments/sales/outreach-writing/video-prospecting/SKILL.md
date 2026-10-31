---
name: video-prospecting
title: Video Prospecting
department: sales
function: outreach-writing
autonomy: assisted
stage: sell
builds_on: [personalisation-research]
breaks_into: [pick-video-targets, write-script, write-send-line, queue-for-recording]
replaces: "a Loom or Vidyard paid plan and an SDR's recording time"
runs_on: github
status: ready
---

# Video Prospecting

Scripts for personalised prospecting videos under ninety seconds.

## Reads from the brain
- `brain/company.md`: voice (plain, no hype), constraints
- `ventures/<slug>/brain.md`: problem, mvp, money

## Inputs
- Tier A dossiers in `sell/dossiers/` (most recent 10 a week).
- `sell/proof.json`, `sell/icp.md`.

## Steps
1. Gate: `audit.json` must say `model: b2b`, else write a `skipped` line in `board.json` and stop.
2. Pick at most 10 tier A prospects a week, highest `fit_score` first, with a live trigger or a verified dossier fact.
3. Write each script at 110 to 150 words, about 60 seconds. Hard ceiling 190 words, 90 seconds.
4. Structure with seconds: name and company (5), one verified fact from the dossier with their page on screen (10), the problem in their words (10), what the product does and the price with the demo on screen (20), one ask (10), sign-off with name.
5. Put screen cues in square brackets: which of their pages to show, which of ours.
6. Charlie speaks and appears. No AI voice, no face clone, no fake "recorded just for you" if it is a template. If the video is a template, say so.
7. Write the send line, one sentence with the link, for email 3 or LinkedIn DM 2. An email carrying a video link is marketing: it keeps the sender identity and the unsubscribe footer, and goes only to `corporate` leads with a `valid` or `likely` address.
8. Hosting: a free video-tool plan Charlie already has, or an unlisted YouTube video (as of Oct 2026, check the limit). No tracking pixels.
9. Save and open a pull request. Charlie records, picks what to send, and the send is logged in `sent.csv` with channel `video`.

## Output
- `ventures/<slug>/sell/sequences/video-<segment>.md`: the segment skeleton, then one filled script per prospect under `## <lead id>`.
- Used by campaign-orchestration as the tier A touch on day 8.

## The ladder
- Human-led: Charlie scripts and records each video.
- Human-assisted: the job writes the scripts and the send line, Charlie records. This is the working mode.
- Fully autonomous: not used. A person must record and approve.

## The human
What stays with Charlie: recording, deciding which prospects get a video, and the final send.

## Tools
Gemini 2.5 Flash then Groq for scripts (as of Oct 2026, check the limit). Charlie's phone camera or a free screen recorder. No paid video platform.

## Build notes
- Word-count check is code: over 190 words fails.
- Tests: a script without a dossier fact fails; a send line without the unsubscribe footer in its email wrapper fails.
