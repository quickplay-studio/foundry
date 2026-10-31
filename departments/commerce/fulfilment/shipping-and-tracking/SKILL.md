---
name: shipping-and-tracking
title: Shipping and Tracking
department: commerce
function: fulfilment
autonomy: solo
stage: run
builds_on: [order-routing]
breaks_into: [collect-tracking, build-channel-upload, draft-customer-updates, chase-late-parcels]
replaces: "a VA chasing parcels or a paid tracking and notification app"
runs_on: github
status: ready
---

# Shipping and Tracking

Tracking numbers collected and sent to the customer; late parcels chased before the customer asks.

Produces tracking uploads for each channel, customer update messages and a chase list for late parcels.

## Reads from the brain
- `brain/company.md`: voice (plain, direct, no hype, no exclamation marks), offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof (delivery promise)

## Inputs
- `ventures/<slug>/idea.json`: `kind` and `channels`.
- `ventures/<slug>/commerce/routing.json`: routed orders and the supplier for each.
- `ventures/<slug>/commerce/data/tracking.csv`: `order_id,carrier,tracking,shipped,status,last_scan,delivered` from supplier confirmations, carrier exports or Charlie. Append or update by order id.
- `ventures/<slug>/commerce/suppliers.json` and `catalogue.json`: lead time and the delivery promise per sku.
- The channels' shipping rules: dispatch time and tracking requirements from the seller help centres.

## Steps
1. Read `idea.json`; stop with a `skipped` line if the kind is not a commerce kind. Read `routing.json` and `tracking.csv`.
2. Match tracking to orders. An order routed more than the supplier's stated dispatch time ago with no tracking is `awaiting-tracking`; list it with the supplier to chase.
3. For orders with tracking, normalise the carrier name and build the public tracking link from the carrier's standard URL pattern. Do not scrape carrier pages; use the status columns in `tracking.csv`, or the link inside the message.
4. Build the channel upload: a file in the format each channel's seller centre takes for tracking and shipment confirmation (order id, carrier, tracking number, ship date). Marketplace orders are updated in the seller centre, and customer messages for them go through that channel's messaging, never off-platform, so Charlie uploads the file.
5. Draft customer messages in the house voice, one per event: shipped (carrier, tracking link, expected date), delayed (new date, option to cancel for a full refund), delivered check-in after two days. Messages are short, state the order id and nothing sensitive. Shop orders can use the store's own shipping email; the drafts are the wording for it.
6. Find late parcels: no scan for 3 working days, or past the promised date, or delivered status with a customer complaint. Calculate days late. Write the chase message to the supplier or carrier with the order id, tracking, dates and the ask (locate, reship or confirm a refund).
7. Apply the law: goods are at the seller's risk until the consumer has them (Consumer Rights Act 2015, section 29); delivery is due within 30 days unless agreed otherwise (section 28). A parcel at 20 days with no movement is escalated to Charlie for a reship or refund decision. Marketplace late-dispatch and late-delivery rate limits come from the help centre, read each run.
8. Write the outputs. Update `routing.json` order status to `shipped` or `delivered`.

## Output
- `ventures/<slug>/commerce/shipping/uploads/<channel>-<date>.csv`: tracking upload per channel.
- `ventures/<slug>/commerce/shipping/messages.json`: `[{order_id, channel, type: "shipped|delayed|delivered", subject, body, send_via, status: "draft"}]`.
- `ventures/<slug>/commerce/shipping/late.md`: parcels late or at risk, days late, the chase text and the decision needed. Read next by `returns-and-refunds` and the support jobs.

## The ladder
- Human-led: Charlie pastes tracking into each seller centre and writes to customers.
- Human-assisted: Charlie uploads the files and sends the drafts.
- Fully autonomous: the default for the files and drafts. No mail or seller key exists in this repo's secrets list, so sending and uploading are Charlie's clicks.

## The human
What stays with Charlie: uploading tracking, sending messages, and any reship or refund decision on a lost parcel.

## Tools
Free first. GitHub Actions on a schedule (daily is enough until order volume needs more); Python stdlib; Gemini 2.5 Flash or Groq to draft messages. No paid tracking apps.

## Build notes
- Customer personal data stays in the private repo only; messages carry the order id, not full addresses.
- Tests offline: fixtures for a shipped order, a missing tracking number after dispatch time, a parcel with no scan for 4 days, and a delivered order.
- GitHub implementation: `run.py` beside this file (jobkit).
