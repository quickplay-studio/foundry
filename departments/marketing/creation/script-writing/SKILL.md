---
name: script-writing
title: Script Writing
department: marketing
function: creation
autonomy: solo
stage: launch
builds_on: [hook-writing]
breaks_into: [pick-hooks, outline-beats, write-script, voice-check]
replaces: "a freelance scriptwriter, usually paid per script"
runs_on: github
status: ready
---

# Script Writing

Turns the best hooks into full video scripts in the house voice: ten short-form scripts for launch, and one long-form script if Charlie asks. Free.

## Reads from the brain
- `brain/company.md`: voice. Say the price and what the product does in the first two lines; proof over adjectives.
- `ventures/<slug>/brain.md`: problem, MVP, money, proof. Every claim in a script comes from here.

## Inputs
- `ventures/<slug>/launch/hooks.json`: hooks with scores and status.
- `launch/insights/audience.json` and, if present, `launch/insights/trends.md` and `launch/insights/performance.json`.
- Optional: `launch/inputs/script-request.json`, `{count, platform, length_s, theme}`, to override the default of ten posts of 30 seconds.

## Steps
1. Pick hooks. Take the highest-scoring `spoken` hook per theme that is not `rejected`, rotating platforms, until the count is reached. Short-form is 20 to 45 seconds.
2. Outline five beats for each: hook (0 to 3 s), problem (3 to 10 s), what it does and the price (10 to 20 s), proof (a number or a screen recording from the product), one call to action. Long-form is 3 to 6 minutes, 450 to 900 words, with a chapter per question from `audience.json`.
3. For each outline ask `foundry.util.ask_json` for `{lines:[{voiceover, on_screen, visual}]}`. Voiceover is spoken English at about 2.5 words a second; on-screen text is 7 words or fewer.
4. Time it in code: seconds = words / 2.5. Cut lines until the total is within the length. Assign `start` and `end` to each line.
5. Voice check in code: no dashes, no exclamation marks, no hype words, UK spelling list (color, optimize, program and similar), no emoji. A claim with no matching line in `brain.md` is rewritten once, then marked `[needs proof]` for Charlie.
6. The call to action is one sentence and names one action: sign up at the link in bio, or watch the next video. Never two.
7. Write the files and set this job to `done` in `ventures/<slug>/board.json`.

## Output
- `ventures/<slug>/launch/scripts/<post-id>.json`: `{post_id, platform, hook_id, duration_s, lines:[{start, end, voiceover, on_screen, visual}]}`. `post_id` is `p-001`, `p-002`. Read by `video-production` and `caption-writing`.
- `ventures/<slug>/launch/scripts/<post-id>.md`: the same as a readable two-column script.
- `ventures/<slug>/launch/scripts/index.json`: one row per script with duration and any `[needs proof]` count.

## The ladder
- Human-led: Charlie writes and records each script himself.
- Human-assisted: the job drafts; Charlie fixes `[needs proof]` lines before filming.
- Fully autonomous: scripts go straight to `video-production`. This is the default for scripts with no `[needs proof]`.

## The human
What stays with Charlie: filming himself or approving a voice, supplying real screen recordings, and fixing any claim marked `[needs proof]`.

## Tools
Free first. Gemini 2.5 Flash and Groq Llama 3.3 70B through `foundry.util.ask_json` (as of Oct 2026, check the limit). Complicated long-form scripts can be written in a Claude Code session with Sonnet, Opus only as advisor.

## Build notes
- Not built yet. Stdlib plus `requests`; steps 4 and 5 are tested functions.
- Fallback with no model: fill beat templates from `brain.md` and the hook text; mark the file `draft: template`.
- Sponsored scripts are `deal-scripting`, not this job.
