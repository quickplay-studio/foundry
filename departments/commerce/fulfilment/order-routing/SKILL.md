---
name: order-routing
title: Order Routing
department: commerce
function: fulfilment
autonomy: assisted
stage: run
builds_on: [catalogue-sync]
breaks_into: [read-new-orders, match-supplier-or-stock, build-supplier-order-sheet, flag-failures]
replaces: "a virtual assistant keying orders to suppliers or a paid order-routing app"
runs_on: github
status: ready
---

# Order Routing

Each order goes to the right supplier or stock with the right details; failures flagged the same hour.

Produces an order sheet per supplier and a list of orders that need attention. Agents prepare orders; Charlie places and pays for every supplier order.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints (no agent pays a supplier; free tools only)
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof (delivery promise, lead times)

## Inputs
- `ventures/<slug>/idea.json`: `kind` and `channels`. Dropshipping routes every order to a supplier; shop and tiktok-shop route to stock first, then to the supplier.
- `ventures/<slug>/commerce/data/orders.csv`: the orders export Charlie drops in from each channel: `order_id,channel,placed,sku,qty,name,address_line1,address_line2,city,postcode,country,email,phone,paid,notes`. Append-only; the job tracks which order ids it has seen.
- `ventures/<slug>/commerce/catalogue.json`: sku, supplier id, lead time.
- `ventures/<slug>/commerce/suppliers.json` and `commerce/inventory.json`: where each sku is sourced and whether it is paused.
- `ventures/<slug>/commerce/routing.json` (own state): orders already routed.

## Steps
1. Read `idea.json`; stop with a `skipped` line if the kind is not a commerce kind. Read `orders.csv` and select ids not in `routing.json`.
2. Validate each order: paid is true, sku exists in the catalogue, qty is a positive whole number, the name and a complete UK address are present (postcode in UK format; flag Northern Ireland, Channel Islands, Isle of Man and non-UK addresses for a delivery and VAT check), phone or email present.
3. Pick the source for each line: own stock if `stock` covers it; otherwise the supplier in the catalogue; otherwise `blocked`. Skip any sku marked `paused` in `inventory.json` and mark the order `blocked: paused`.
4. Group the routable lines by supplier. Write one order sheet per supplier in the format that supplier takes (a CSV, or a plain list with the fields they ask for), with: supplier sku, quantity, ship-to name and address, a contact phone for the courier, the service level wanted, and the customer order id as the reference. For dropshipping, include a plain packing note: no invoice or price in the parcel, neutral or branded slip as agreed.
5. Flag failures with a reason and the order id, in `attention.md`, at the top, with the time: unpaid, unknown sku, paused, out of stock at both sources, address incomplete or outside the delivery area, the supplier's lead time longer than the promise on the listing, a duplicate order id, a possible fraud pattern (different billing and delivery country with an express service, repeat orders to many addresses).
6. For a failed line, draft a short message to the customer in the house voice (delay, partial shipment or refund offer), marked draft. Refund offers wait for Charlie.
7. Update `routing.json`. Data hygiene: customer details stay only in the private repo, appear in no log or issue text, and are removed from `orders.csv` copies 90 days after delivery (UK GDPR data minimisation).
8. Set the job to `review` in `board.json` when there is anything routable or flagged; leave it `done` for an empty run.

## Output
- `ventures/<slug>/commerce/orders/<date>-<supplier>.csv`: the sheet Charlie sends or uploads to the supplier.
- `ventures/<slug>/commerce/orders/attention.md`: failures newest first, with the reason and the next action. Charlie sees this the same hour the workflow runs.
- `ventures/<slug>/commerce/routing.json`: `{orders: {order_id: {status: "routed|blocked|shipped", source, supplier_id, sheet, flagged: [reasons], routed_at}}}`.

## The ladder
- Human-led: Charlie reads the orders and keys them into the supplier portal.
- Human-assisted: the default. The job sorts, formats and flags; Charlie places and pays.
- Fully autonomous: only the sorting, the sheets and the flags. Placing and paying stay with Charlie.

## The human
What stays with Charlie: placing and paying every supplier order, approving refund offers, and dropping the orders export.

## Tools
Free first. GitHub Actions hourly on a venture with live orders (about 24 runs a day; check the Actions minutes limit as of Oct 2026); Python stdlib for CSV; Gemini 2.5 Flash or Groq only to draft customer messages. No paid order apps and no seller logins held by agents.

## Build notes
- Idempotent: running twice produces no duplicate sheets.
- A missing `orders.csv` is a normal empty run, not an error.
- Tests offline: fixtures for a clean order, an unpaid order, a paused sku, a Northern Ireland address, a duplicate id and a two-supplier basket.
- GitHub implementation: `run.py` beside this file (jobkit).
