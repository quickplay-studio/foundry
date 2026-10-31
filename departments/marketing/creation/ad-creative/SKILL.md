---
name: ad-creative
title: Ad Creative
department: marketing
function: creation
autonomy: assisted
stage: launch
builds_on: [hook-writing, landing-page-copy, platform-and-ad-compliance]
breaks_into: [read-budget, draft-creatives, set-audiences, write-brief]
replaces: "a paid-social freelancer or agency briefing a first campaign"
runs_on: github
status: ready
---

# Ad Creative

Writes the paid-ad brief Charlie approves before any money moves: three creatives, two audiences, a daily cap, a total budget, a target cost per sign-up and a kill rule. The agent never holds a card and never creates an ad account. Charlie approves the brief and pays the platform.

## Reads from the brain
- `brain/company.md`: voice (price and what it does in the first two lines); ad spend is the one paid exception and Charlie approves every budget line.
- `ventures/<slug>/brain.md`: problem, who, MVP, money (the price), proof. Every claim in an ad must appear here or in `launch/landing-page.md`.

## Inputs
- `ventures/<slug>/budget.json`: `ad_budget` in pounds, `spent`, `lines`.
- `launch/hooks.json` (`hook-writing`) and `launch/landing-page.md` (`landing-page-copy`): angles, price, proof, the sign-up page. `launch/channels.json` has `site`.
- Legal's `platform-and-ad-compliance` result: the file with `ad-compliance` in its name under `ventures/<slug>/launch/` or `ventures/<slug>/clear/`. Platform policies and banned claims.
- `launch/insights/audience.json`: who to target and the words they use.
- Optional on re-runs: `launch/inputs/ad-results.csv`, columns `creative,spend,signups`, typed in by Charlie from the platform.

## Steps
1. Read `budget.json`. If `ad_budget` is missing or 0, add a line under `skipped` in `ventures/<slug>/board.json` ("no ad budget") and stop.
2. Find the compliance file. If there is none, skip with that reason and stop: ad copy is not written before the rules.
3. Choose one platform. Google if people search the problem in words ("how do I", "best X for Y") and want an answer now. TikTok if the reader is mostly under 30 and the product demos well on video. Otherwise Meta. Check the platform's minimum daily budget (as of Oct 2026, check the limit); if the daily cap in step 8 is below it, change platform.
4. Write the objective in one sentence: sign-ups on the site at or below the target cost, within the total budget, tracked as the `sign_up` event. For a shop, tiktok-shop or dropshipping venture read `ventures/<slug>/commerce/landed-cost.json` and set the target to its `target_cpa`, never above `break_even_cpa`, with the objective a sale instead of a sign-up. Charlie installs the platform tag; UK consent rules apply (Legal `privacy-policy`; not legal advice).
5. Ask `foundry.util.ask_json` for nine candidates, three per angle (the problem, the outcome with price, the proof): `{angle, hook, body, visual_note}`. Hook 12 words or fewer; body 30 words or fewer and states the price and what it does. Google: headline 30 characters or fewer, description 90 or fewer.
6. Filter in code: dashes, exclamation marks, superlatives, guarantees, income or health claims, personal-attribute call-outs ("are you in debt"), anything the compliance file bans, any claim not in the brain. Keep the best of each angle by `hook-writing` score. If an angle has none left, regenerate once, then stop with a reason.
7. Write two audiences. Meta and TikTok: UK, an age range, one broad audience and one narrower from the who line. Google: two keyword themes, phrase or exact match, with negative keywords. No sensitive categories.
8. Set the money. Daily cap = total budget divided by 10, rounded to the nearest pound, at least £5. Target cost per sign-up = one third of first-year revenue per paying user, times the assumed share of sign-ups who pay (start at 10 per cent and say so in the field). Add expected sign-ups at target (total budget divided by target); under 20 means the test is too small to judge, and the field says so.
9. Write the kill rule exactly: "Stop when cost per sign-up is above £<target> after the first £50 spent." If the total budget is under £50, add "The total budget ends the test first."
10. Write the brief, run the field check (every field present, numbers parse, daily cap not above total), open a draft pull request for Charlie, and set the board status to `review`.

## Output
`ventures/<slug>/launch/ad-brief.md`, exactly these fields, in this order:
```
# Ad brief: <venture title>
**objective:** one sentence
**platform:** Meta, Google or TikTok (one)
**creative 1:** hook / body / visual note (three lines)
**creative 2:** hook / body / visual note
**creative 3:** hook / body / visual note
**audience 1:** definition Charlie can enter in the platform
**audience 2:** definition Charlie can enter in the platform
**daily cap:** £N
**total budget:** £N, copied from budget.json
**target cost per sign-up:** £N.NN, with the assumption stated
**kill rule:** Stop when cost per sign-up is above £N.NN after the first £50 spent.
**campaign id:** pending, Charlie fills this in after he pays
```
On a re-run with `ad-results.csv`, replace the creative with the highest cost per sign-up by a new one on the best angle. Never raise the cap or the total.

## The ladder
- Human-led: Charlie writes the ads and brief in the ad platform himself.
- Human-assisted: the job drafts the brief; Charlie edits, approves, pays and builds the campaign. This is the default and the ceiling.
- Fully autonomous: not allowed for money. Only drafting refreshed creatives from results can run unattended.

## The human
What stays with Charlie: approving the brief and the budget line, creating the ad account, paying with his own card, installing the tag, building the campaign, entering the campaign id, setting the platform's rule to pause at the kill rule (or checking at £50), and any budget increase.

## Tools
Free first. Gemini 2.5 Flash and Groq Llama 3.3 70B through `foundry.util.ask_json` (as of Oct 2026, check the limit). Meta Ads Manager, Google Ads and TikTok Ads are Charlie's account and money only. He may browse the Meta Ad Library by hand for angles; the job does not scrape it.

## Build notes
- Not built yet. Stdlib plus `requests`; the field check is a tested function that fails on a missing or extra field.
- A copy of the brief goes in the pull request body so Charlie can approve from his phone.
- Ad text limits change; keep them in one table in code.
- GitHub implementation: `run.py` beside this file (jobkit).
