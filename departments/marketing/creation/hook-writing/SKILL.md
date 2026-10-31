---
name: hook-writing
title: Hook Writing
department: marketing
function: creation
autonomy: solo
stage: launch
builds_on: [audience-analysis]
breaks_into: [load-patterns, draft-hooks, score-hooks, rank-per-platform]
replaces: "a freelance copywriter writing hooks and titles"
runs_on: github
status: ready
---

# Hook Writing

Writes and ranks the first line of every post and ad, per platform: spoken hooks, titles and cover text. Later jobs take the top hooks instead of inventing their own.

## Reads from the brain
- `brain/company.md`: voice (plain, direct, no hype, no exclamation marks, no dashes) and what we will not do.
- `ventures/<slug>/brain.md`: problem, who, MVP, money, proof. Hooks may only claim what is here.

## Inputs
- `ventures/<slug>/launch/insights/audience.json` (required): questions, objections, language bank.
- `launch/insights/hook-patterns.json` (`competitor-analysis`): proven patterns and templates. Optional.
- `launch/insights/performance.json` (`performance-mining`): winners and losers. Optional.
- Platforms: the `platforms` list in `launch/channels.json`; default `tiktok`, `instagram`, `youtube`.
- Optional: `launch/inputs/vidiq-titles.json`, title scores exported from Charlie's vidIQ account.

## Steps
1. Read the inputs. If `audience.json` is missing, add a line under `skipped` in `ventures/<slug>/board.json` and stop.
2. Build the pattern list: curiosity gap, number list, contradiction, pain call-out, how-to promise, before and after, direct offer, plus anything in `hook-patterns.json`. Patterns that won in `performance.json` go first.
3. For each platform, ask `foundry.util.ask_json` for 12 hooks of each kind: `spoken` (first three seconds, under 12 words), `title` (YouTube, up to 60 characters so it is not cut off), `cover` (on-image text, up to 7 words). Return `{hooks:[{kind, text, pattern, theme}]}`. Each hook must use one theme and one language-bank phrase.
4. Reject in code: dashes, exclamation marks, hype words (amazing, revolutionary, game-changing, insane, secret), an invented number, an income or health promise, an unsupported superlative. A number must come from `brain.md` or the counts in `audience.json`.
5. Score each hook 0 to 10 in code: 2 for being under the word limit, 2 for naming the reader or the problem plainly, 2 for a concrete noun or number, 2 for a pattern that won or appears in `hook-patterns.json`, 2 for a language-bank phrase. Break ties with the vidIQ score if present, otherwise the model's pick.
6. Keep the top five per platform and kind, at most 30 hooks. Number them `h-001`, `h-002`.
7. Write both outputs and set this job to `done` in `board.json` with `output` and `updated`.

## Output
- `ventures/<slug>/launch/hooks.json`: `{hooks:[{id, platform, kind, text, pattern, theme, score, status}]}`. `status` starts as `candidate`; Charlie may set `rejected`, and later jobs skip those.
- `ventures/<slug>/launch/hooks.md`: the same, grouped by platform and sorted by score, for reading. Read by `script-writing`, `caption-writing`, `carousel-production`, `ad-creative`.

## The ladder
- Human-led: Charlie writes hooks and tests them by posting.
- Human-assisted: the job ranks; Charlie rejects any that feel wrong for the brand.
- Fully autonomous: the top hook per theme flows to `script-writing` with no review. This is the default.

## The human
What stays with Charlie: the brand's taste. He rejects hooks that are off-voice or too close to a competitor's wording.

## Tools
Free first. Gemini 2.5 Flash, Flash-Lite and Groq Llama 3.3 70B through `foundry.util.ask_json` (as of Oct 2026, check the limit). vidIQ title scoring from Charlie's account, passed in as a file. No Claude.

## Build notes
- Not built yet. Stdlib plus `requests`. Steps 4 and 5 are plain functions with tests.
- Fallback with no model: fill the `template` fields from `hook-patterns.json` with language-bank phrases and score them the same way.
- The platform list comes from `channels.json`, so adding a platform needs no code change.
