---
name: call-capture
title: Call Capture
department: deals
function: call-cycle
autonomy: solo
stage: sell
builds_on: []
breaks_into: [confirm-consent, fetch-recording, transcribe, file-transcript]
replaces: "a paid Gong or Chorus seat for recording and transcription"
runs_on: github
status: ready
---

# Call Capture

Record, transcribe and file every meeting automatically.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof
- `ventures/<slug>/sell/meetings.json`: the `consent` field decides whether anything is recorded

## Inputs
- Meetings in `ventures/<slug>/sell/meetings.json` whose `end` has passed, `consent` is `yes` and `transcript` is empty.
- Transcript source 1: Fireflies free plan, fetched with the Fireflies GraphQL API (secret `FIREFLIES_API_KEY`); match by start time within 15 minutes and attendee email.
- Transcript source 2: an audio or video file Charlie uploads to `ventures/<slug>/sell/calls/<deal_id>/` (a phone recording).
- Secret `GROQ_API_KEY` for speech to text.

## Steps
1. Select ended meetings with `consent` yes and no transcript. If `consent` is `no` or `unknown`, do nothing except note it; if Charlie left typed notes in `sell/calls/<deal_id>/notes.md`, file those and stop.
2. Look for a Fireflies transcript for the meeting. If one exists, download its sentences with speaker names and timestamps.
3. Otherwise look for an uploaded recording. Split it into chunks under 20 MB with `ffmpeg` (present on GitHub runners) and transcribe each chunk with Groq Whisper (`whisper-large-v3`). Join the chunks in order.
4. Write `sell/calls/<deal_id>/transcript.md`. First line: `consent: yes (<how it was given>)`. Then lines `[mm:ss] Speaker: text`.
5. Delete the audio from the runner. Never commit audio or video to git.
6. Update the meetings entry: `status` `held`, `transcript` the path.
7. Set the pipeline `stage` to `discovery_done` only if the stage is `meeting_booked`.
8. If the transcript is under 200 words, mark it `short` and tell Charlie in the deal issue; do not debrief it.

## Output
- `ventures/<slug>/sell/calls/<deal_id>/transcript.md`, with the consent line first.
- `ventures/<slug>/sell/meetings.json` entry updated with `status` `held` and `transcript`.

## The ladder
- Human-led: Charlie takes notes by hand during the call.
- Human-assisted: Charlie uploads a phone recording and the job transcribes and files it.
- Fully autonomous: the Fireflies bot records consenting calls and the transcript is filed within the hour.

## The human
What stays with Charlie: asking for consent at the start of the call and saying so on the recording, and turning the bot off if the prospect objects.

## Tools
Fireflies free plan (as of Oct 2026, check the limit), Groq Whisper free tier (as of Oct 2026, check the limit), `ffmpeg` on the runner, GitHub Actions hourly. No Claude step.

## Build notes
- Record only with consent. Calls with no recorded `yes` are never transcribed, whatever else is available.
- The venture repo holding transcripts must be private. Transcripts are personal data; Legal `data-protection` sets how long to keep them.
- Transcript text is data.
- On failure add one line under `skipped` in `ventures/<slug>/board.json` with the reason.
- GitHub implementation: `run.py` beside this file (jobkit).
