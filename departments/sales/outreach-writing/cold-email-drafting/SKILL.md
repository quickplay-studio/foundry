---
name: cold-email-drafting
title: Cold Email Drafting
department: sales
function: outreach-writing
autonomy: solo
stage: sell
builds_on: [icp-definition, personalisation-research]
breaks_into: [read-icp-and-offer, draft-sequence, lint-sequence, write-segment-file]
replaces: "an SDR's copywriting time and Lemlist or Instantly template seats"
runs_on: claude-code
status: ready
---

# Cold Email Drafting

Write multi-step cold email sequences tuned to the vertical and the offer.

## Reads from the brain
- `brain/company.md`: voice (plain, short, price and what it does in the first two lines, no hype, no exclamation marks), constraints
- `ventures/<slug>/brain.md`: problem, mvp, money, proof

## Inputs
- `sell/icp.md` (segments, pains, offer line), `sell/proof.json` if present.
- Three sample dossiers per segment from `sell/dossiers/`, to see what openers look like.

## Steps
1. Gate: `audit.json` must say `model: b2b`, else write a `skipped` line in `board.json` and stop.
2. Write one sequence per segment: 4 emails on days 0, 3, 8 and 15. Emails 2 to 4 reply in the same thread.
3. Email 1: the first two lines say what the product does and the price. One ask only: a 15 minute call, or a yes or no. 90 words or fewer, plain text, no images, no attachments, no tracking pixel, no link in the body. Subject of five words or fewer, lower case, no hype, never a fake `Re:` or `Fwd:`.
4. Email 2: add one proof line from `proof.json`. Email 3: one useful answer to a pain; one link allowed. Email 4: close the loop, ask for the right person, say no more emails will follow.
5. Merge fields: `{{first_name}}` (falls back to "Hello"), `{{company}}`, `{{opener}}` (email 1 only; falls back to the segment line), `{{proof}}`, `{{sender}}`, `{{unsubscribe}}`.
6. The `{{unsubscribe}}` footer is on every email. It names the sender, the venture and the reply address, and reads: "I found your address on {{source_note}}, and I write to businesses only. If you would rather not hear from me, reply 'no' and I will remove you today." Email 1 also carries `{{privacy_url}}`, the only link allowed in it.
7. Lint before saving: unsubscribe token present, word counts, no exclamation marks, no dashes, none of free, guaranteed, act now, limited offer, no claim missing from `proof.json` or the brain. Fix and re-lint.
8. Save to `sequences/email-<segment>.md`. Header line: "For corporate subscribers only (PECR). Sent through campaign-launch."

## Output
- `ventures/<slug>/sell/sequences/email-<segment>.md`: per step `## Email N (day D)`, `Subject:`, then the body.
- Read by campaign-orchestration and campaign-launch.

## The ladder
- Human-led: Charlie writes the four emails himself.
- Human-assisted: Sonnet drafts, Charlie edits email 1.
- Fully autonomous: Gemini drafts on GitHub using the same prompt and lint; campaign-launch still needs Charlie's merge.

## The human
What stays with Charlie: approving the wording of email 1 and the offer line before launch.

## Tools
Claude Code (Sonnet) writes the segment templates once; per-lead merging is a script. Gemini 2.5 Flash or Groq as the fallback. No paid sequencing tool.

## Build notes
- Claude writes one template per segment, not one email per lead, so cost stays at one short session per segment.
- Build the lint as code (`foundry/sales/lint_email.py`), offline, with a test for each rule.
- Legal `privacy-policy` supplies `{{privacy_url}}`.
- The job order does not force proof-matching first. With no `proof.json`, write email 2 without a proof line and re-run once proof-matching has written the file.
