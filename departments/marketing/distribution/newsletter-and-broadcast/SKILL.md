---
name: newsletter-and-broadcast
title: Newsletter and Broadcast
department: marketing
function: distribution
autonomy: assisted
stage: support
builds_on: [caption-writing]
breaks_into: [pick-content, write-issue, render-email, check-and-queue]
replaces: "a freelance email copywriter and template designer"
runs_on: github
status: ready
---

# Newsletter and Broadcast

Drafts the regular email to subscribers: one issue, one call to action, in the brand system. The job prepares the issue; Charlie sends it from his email service. Fortnightly by default.

## Reads from the brain
- `brain/company.md`: voice, and the rules against unsolicited email outside the law and bought lists.
- `ventures/<slug>/brain.md`: the product, price and proof. The cadence is the `Decisions` line in this file, default fortnightly.

## Inputs
- Content: `launch/insights/performance.md` (best posts), `launch/captions.json` (copy that worked), `launch/insights/audience.json` (questions to answer), and product changes Charlie notes in `launch/inputs/updates.md`.
- `launch/brand.json`: `{colours:{bg, text, accent}, font, logo}`.
- `launch/lead-magnet/index.json` if a guide exists.
- Subscribers stay in Charlie's free email service. The job never holds the list.

## Steps
1. Pick one lead item: a question from `audience.json` answered with facts from the brain, or the best-performing post idea, or a product update. Add up to two short items below it.
2. Ask `foundry.util.ask_json` for `{subject, preheader, sections:[{heading, body}], cta_text, cta_link}`. Subject 50 characters or fewer, preheader 90 or fewer, body 250 words or fewer, one call to action.
3. Lint in code: no dashes, no exclamation marks, no hype or spam words (free, guaranteed, act now, winner), no claim missing from the brain, UK spelling.
4. Build links with `utm_source=newsletter&utm_medium=email&utm_campaign=<yyyy-mm-dd>`. Request each link with `requests`; a non-200 response fails the check.
5. Render an HTML email: single column, 600 pixels wide, inline CSS from `brand.json`, brand colours with text contrast of at least 4.5 to 1, alt text on every image, and a plain-text version. The footer says who we are, why the reader gets this, and uses the email service's unsubscribe merge tag.
6. Open a draft pull request with the issue files and set the board status to `review`. Charlie sends a test to himself, then schedules or sends from his email service.
7. After sending, Charlie adds `sent` and the date to `meta.json`; the job sets itself to `done` in `ventures/<slug>/board.json`.

## Output
- `ventures/<slug>/launch/newsletter/<yyyy-mm-dd>/issue.html`, `issue.txt` and `meta.json`: `{subject, preheader, send_after, segment, links:[], checks:{lint, links, contrast}}`.
- Charlie sees the pull request; subscribers see only what he sends.

## The ladder
- Human-led: Charlie writes and sends each issue.
- Human-assisted: the job drafts, checks and renders; Charlie reads, tests and sends. This is the default.
- Fully autonomous: not enabled. Sending to people always needs Charlie.

## The human
What stays with Charlie: choosing and running the email service account, the sign-up consent wording, sending, and removing anyone who asks to leave. Legal's `data-protection` and `privacy-policy` apply; this is not legal advice.

## Tools
Free first. A free email service Charlie picks, such as MailerLite or Buttondown free tiers (as of Oct 2026, check the limit). Gemini 2.5 Flash and Groq Llama 3.3 70B through `foundry.util.ask_json`. No Claude.

## Build notes
- Not built yet. Stdlib plus `requests`; the HTML is one template with slots, rendered with string replacement.
- Fallback with no model: lead item from the top question and its brain answer, plus the call to action.
- Run the first issue as a test only: no real send until Charlie has seen it in two mail clients.
- GitHub implementation: `run.py` beside this file (jobkit).
