---
name: returns-and-refunds
title: Returns and Refunds
department: commerce
function: fulfilment
autonomy: assisted
stage: support
builds_on: [consumer-law-check]
breaks_into: [classify-request, check-rights-and-window, decide-and-draft, log-reason]
replaces: "a customer service VA or a paid returns management platform"
runs_on: github
status: ready
---

# Returns and Refunds

Returns handled to UK consumer law and the platform's policy: approve, refund, replace or escalate, with the reason logged.

Produces a decision and a draft reply for each return request, and a log. Agents never issue a refund; Charlie does.

## Reads from the brain
- `brain/company.md`: voice (plain, direct, no hype), offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof (return promise, margin)

## Inputs
- `ventures/<slug>/idea.json`: `kind` and `channels`.
- `ventures/<slug>/clear/consumer-law-check.md`: the rules list already agreed for the venture.
- `ventures/<slug>/commerce/data/returns.csv`: `request_id,order_id,channel,received,sku,reason,detail,photos,delivered,opened`. Exported or typed by Charlie.
- `ventures/<slug>/commerce/routing.json` and `shipping/`: order, delivery date and supplier.
- `ventures/<slug>/commerce/landed-cost.json`: the cost of a return, for the log.
- The channel's returns policy from its seller help centre.

## Steps
1. Read `idea.json`; stop with a `skipped` line if the kind is not a commerce kind. Read the new rows in `returns.csv`.
2. Classify each request: change of mind, faulty or not as described, wrong item, damaged in transit, not delivered, or other. Take the delivery date from `shipping/`.
3. Apply the Consumer Contracts Regulations 2013 to a change of mind on a distance sale: the consumer may cancel within 14 days of receiving the goods, then has a further 14 days to send them back. The refund is due within 14 days of the goods arriving back or proof of posting, and includes standard delivery. The consumer pays return postage only if told before buying. Exceptions to confirm on legislation.gov.uk: sealed goods for health or hygiene once unsealed, personalised goods, goods that spoil quickly.
4. Apply the Consumer Rights Act 2015 to faulty or misdescribed goods: a 30-day right to reject for a full refund; then one repair or replacement; then a price reduction or the final right to reject. In the first six months the fault is presumed to have been there at delivery, so the seller must show otherwise. These rights cannot be excluded or reduced by the seller's terms. Wrong or damaged items are the seller's responsibility; the seller pays the return.
5. Check the channel policy for the same case. Where it is more generous than the law, the more generous rule applies. Where the channel handles the refund itself (TikTok Shop, Amazon), the reply must not promise what the platform controls.
6. Decide per request: `approve-return` (give the return instructions), `refund` (goods not needed back, for example low value under the venture's threshold), `replace`, `deny` (with the legal basis, for example outside the window or an excluded good) or `escalate` (fraud pattern, high value, injury or safety concern, legal threat, repeated returns by one customer). A safety concern is always `escalate` and feeds `marketplace-compliance`.
7. Draft the reply in the house voice: the decision, the reason, the next step, the date by which money returns. If denied, state the right they still have, never leave it silent.
8. Log: request id, order id, category, rule applied, decision, reason, cost to the venture, and the date the refund is due. Count reasons per sku and write the recurring themes for `review-management` and `product-selection`.
9. Set the job to `review`; Charlie approves refunds and replacements and sends the reply.

## Output
- `ventures/<slug>/commerce/returns/decisions.json`: `[{request_id, order_id, category, rule, decision, reason, refund_due, cost_gbp, draft_reply, status: "draft"}]`.
- `ventures/<slug>/commerce/returns/log.csv`: append-only decision log.
- `ventures/<slug>/commerce/returns/themes.md`: reasons by sku, weekly. Not legal advice; Charlie or a solicitor checks the policy before launch.

## The ladder
- Human-led: Charlie reads every request and decides.
- Human-assisted: the default. The job classifies, applies the rules and drafts; Charlie approves.
- Fully autonomous: only the log and the themes. Money out and customer replies stay with Charlie.

## The human
What stays with Charlie: issuing every refund or replacement, sending replies, and every escalation.

## Tools
Free first. Gemini 2.5 Flash or Groq to classify and draft; code for the date arithmetic; Firecrawl free tier (500 credits as of Oct 2026, check the limit) to read legislation.gov.uk and the channels' returns policies. No paid returns platforms.

## Build notes
- Statute text is read from legislation.gov.uk with the date recorded, not taken from memory.
- Dates are counted in code, never by the model.
- Tests offline: fixtures for a change of mind on day 10, one on day 20, a fault at day 25, a fault at month 4, a sealed hygiene item and a safety complaint.
- GitHub implementation: `run.py` beside this file (jobkit).
