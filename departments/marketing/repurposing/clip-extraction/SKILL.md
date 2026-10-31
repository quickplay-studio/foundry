---
name: clip-extraction
title: Clip Extraction
department: marketing
function: repurposing
autonomy: solo
stage: launch
builds_on: [video-production]
breaks_into: [transcribe, pick-moments, cut-clips, caption-clips]
replaces: "a clipping freelancer or a paid clip-cutting tool"
runs_on: github
status: ready
---

# Clip Extraction

Cuts a long recording Charlie owns (webinar, screen walkthrough, podcast) into short vertical clips with captions, each one standing alone. Free.

## Reads from the brain
- `brain/company.md`: voice, and the rule that sponsored or third-party content is never cut without permission.
- `ventures/<slug>/brain.md`: the product, so clips that show it are preferred.

## Inputs
- `ventures/<slug>/launch/inputs/recordings/<name>.mp4` (or `.mov`, `.wav`): only recordings Charlie made or has the rights to.
- `launch/brand.json`: `{colours:{bg, text, accent}, font, logo}`.
- Optional: `launch/inputs/clip-request.json`, `{count, min_s, max_s}`; defaults 8 clips of 20 to 60 seconds.
- `GROQ_API_KEY` for Whisper transcription (free tier; as of Oct 2026, check the limit and its file-size cap).

## Steps
1. Extract mono 16 kHz audio with ffmpeg at 32 kbps so an hour stays under the free tier's file cap. Split into chunks if longer.
2. Transcribe with Groq Whisper (`whisper-large-v3-turbo`) with word timestamps. Save the transcript to `launch/clips/<name>.transcript.json`.
3. Build candidate windows on sentence boundaries, 20 to 60 seconds each, overlapping by half.
4. Ask `foundry.util.ask_json` to score windows in batches: standalone sense (begins on a clear claim, ends on a finished thought, no "as I said earlier"), a number or a specific example, mention of the product. Return `{scores:[{window, score, hook_text, reason}]}`. Take the top N that do not overlap.
5. Cut with ffmpeg, re-encoding for frame-accurate starts. Reframe to 1080 by 1920: centre crop for a face or a screen region, or the source fitted over a blurred copy. Burn word-timed captions of two lines at most, in the safe area (250 pixels clear at the bottom, 150 at the top). Normalise loudness to -14 LUFS.
6. Check with `ffprobe`: duration within the request, audio present, no clip starting or ending mid-word (cut at word boundaries plus 0.2 s padding).
7. Write the clips (artifact storage, not git), the index and `launch/clips/<name>.md`. Set this job to `done` in `ventures/<slug>/board.json`.

## Output
- `ventures/<slug>/launch/clips/<name>/clip-01.mp4`, `clip-01.srt` and onward (stored as workflow artifacts).
- `ventures/<slug>/launch/clips/<name>/index.json`: `[{clip_id, source, start, end, hook_text, score, reason}]`. The `hook_text` feeds `hook-writing` and `caption-writing`; clips go to `cross-platform-adaptation` and `publishing`.

## The ladder
- Human-led: Charlie scrubs the recording and exports clips by hand.
- Human-assisted: the job proposes and cuts; Charlie deletes weak ones.
- Fully autonomous: the top clips go to `cross-platform-adaptation`. This is the default.

## The human
What stays with Charlie: supplying recordings, confirming he has the rights to anyone who appears, and removing a clip that is out of context.

## Tools
Free first. ffmpeg on GitHub Actions, Groq Whisper, Gemini 2.5 Flash and Groq Llama 3.3 70B through `foundry.util.ask_json`. vidIQ clip generation on Charlie's account is an alternative if his plan has credits (as of Oct 2026, check the limit).

## Build notes
- Not built yet. Stdlib plus `requests`; ffmpeg is called as a command.
- Fallback with no model: pick windows by speech rate and the presence of numbers; mark the index `heuristic`.
- Never fetch other people's videos. This job only cuts files that are in `inputs/recordings/`.
