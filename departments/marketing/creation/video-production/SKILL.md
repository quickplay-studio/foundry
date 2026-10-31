---
name: video-production
title: Video Production
department: marketing
function: creation
autonomy: solo
stage: launch
builds_on: [script-writing]
breaks_into: [resolve-media, voice-and-captions, compose-video, check-output]
replaces: "a freelance video editor, usually paid per video"
runs_on: claude-code
status: ready
---

# Video Production

Builds vertical videos from scripts: recordings or stock footage, captions, text overlays and a voice track, all with ffmpeg. Runs in a Claude Code session the first time for a venture, to build and look at the render template; after that the render step repeats on GitHub Actions.

## Reads from the brain
- `brain/company.md`: voice and constraints.
- `ventures/<slug>/brain.md`: the product, so recordings and overlays show the real thing.

## Inputs
- `ventures/<slug>/launch/scripts/<post-id>.json`: `{post_id, platform, duration_s, lines:[{start, end, voiceover, on_screen, visual}]}`.
- `launch/brand.json`: `{colours:{bg, text, accent}, font, logo}`.
- Media, in order of preference: Charlie's recordings in `launch/inputs/recordings/`; Pexels video (`PEXELS_API_KEY`); stills from `launch/images/` with a slow zoom. As of Oct 2026, check the limit.
- Voice: `launch/inputs/voice/<post-id>.wav` from Charlie; else Gemini text to speech if the free tier allows (check the limit); else a captions-only video.
- Optional music: royalty-free files Charlie places in `launch/inputs/music/`, licence noted in the file name.

## Steps
1. Read the script. Resolve a clip for each line from its `visual` note. Record the source and licence of every stock clip in `launch/video/credits.json`.
2. Get the voice. Normalise it with ffmpeg `loudnorm` to -14 LUFS.
3. Transcribe our own voice track with Groq Whisper (free tier, as of Oct 2026 check the limit) for word timings. Build an `.srt` with at most two lines of 32 characters.
4. Compose with ffmpeg (install with `apt-get` on the runner): scale and crop to 1080 by 1920 at 30 fps, draw `on_screen` text with `drawtext`, burn the captions in the central safe area (keep 250 pixels clear at the bottom and 150 at the top, where app buttons sit), add the logo, mix music at -22 LUFS under the voice.
5. Encode H.264 video, AAC audio, `-movflags +faststart`, under 60 seconds unless the script says long-form.
6. Check: `ffprobe` duration within 2 seconds of `duration_s`; extract frames at the start, middle and end and look at them for clipped text; confirm no caption or overlay sits in the unsafe area. Fix and re-render once.
7. Write the files. Videos go to a workflow artifact or release, not git; `index.json` records the location. Set this job to `done` in `ventures/<slug>/board.json`; a script that cannot render goes under `skipped` with the reason.

## Output
- `ventures/<slug>/launch/video/<post-id>.mp4` and `<post-id>.srt` (stored as artifacts), `credits.json`.
- `ventures/<slug>/launch/video/index.json`: `[{post_id, file, duration_s, platform, has_voice, checked}]`. Read by `clip-extraction`, `cross-platform-adaptation` and `publishing`.

## The ladder
- Human-led: Charlie edits in a free editor and exports each video.
- Human-assisted: the job renders a draft; Charlie records the voice or screen capture.
- Fully autonomous: the template renders on GitHub for every new script. Charlie approves in `publishing`.

## The human
What stays with Charlie: recordings of the real product, his voice if wanted, music choices, and approving each video before it posts.

## Tools
Free first. ffmpeg on GitHub Actions, Pexels free video, Groq Whisper, Gemini text to speech, vidIQ video and voiceover tools on Charlie's account if his plan has credits (as of Oct 2026, check the limit). Claude Code with Sonnet to build the template once; Opus only as advisor.

## Build notes
- Not built yet. Build `render.py` and a command template in a Claude Code session, test on one script, then run it from a `workflow_dispatch` job.
- The repo rule is stdlib plus `requests`; ffmpeg is called as a command, not a package.
- Keep files small. Do not commit mp4 files.
