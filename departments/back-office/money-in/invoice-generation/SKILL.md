---
name: invoice-generation
title: Invoice Generation
department: back-office
function: money-in
autonomy: solo
stage: run
builds_on: []
breaks_into: [validate-request, number-and-calculate, render-invoice, log-invoice]
replaces: "a paid invoicing app, roughly 10 to 25 pounds a month"
runs_on: github
status: ready
---

# Invoice Generation

Branded invoices per entity, currency and tax treatment. Only needed when a venture bills a business directly; consumer sales through Stripe get Stripe's own receipts.

## Reads from the brain
- `brain/company.md`: voice (plain, price first, no hype) and the Entity line. Entity is "none yet": see step 1.
- `ventures/<slug>/brain.md`: money, for what is sold and at what price

## Inputs
- `ventures/<slug>/finance/invoice-requests.json`: list of `{customer, customer_address, items: [{description, quantity, unit_price}], currency, due_days, reference}`, written by Charlie or taken from an accepted proposal.
- `office/finance/issuer.json`: the issuing name, address, contact email, VAT number if registered, and the payment line. Written by Charlie after Legal `entity-and-structure` decides who issues.
- `ventures/<slug>/finance/tax.json`: `{vat_registered, vat_rate, note}`, set by Charlie. This job never decides whether VAT applies.
- `ventures/<slug>/finance/invoices.json`: the register and the last number used.
- Optional logo at `ventures/<slug>/brand/logo.svg`.

## Steps
1. If `issuer.json` or `tax.json` is missing, stop for that venture: write a line under `skipped` in `board.json` ("no issuer set") and do nothing else. Never invent an issuer or a VAT status.
2. Validate each request: customer, address, at least one item, positive quantities and prices, a currency code. Reject the request with a reason, do not repair it.
3. Number it `INV-<year>-<4 digits>`, gapless and in date order, from the register. A request already in the register (same `reference`) is not issued twice.
4. Calculate in integer minor units. Net per line, VAT per line if `vat_registered`, total, all rounded half up. Due date is the invoice date plus `due_days`.
5. Render `INV-....html` with print styles and `INV-....md`. Include what an invoice needs: number, date, issuer and customer names and addresses, description, quantity, unit price, net, VAT rate and amount and VAT number if registered, total, due date, payment line. Once a quarter read the HMRC invoice guidance page through Firecrawl to confirm that list; note any change in `invoices.json`.
6. Payment line is a payment link or "reply for bank details". Account and sort code numbers never go in the repo; Charlie adds them to the sent copy by hand if wanted.
7. Add a register row with status `draft`.

## Output
- `ventures/<slug>/finance/invoices/INV-2026-0001.html` and `.md`.
- `ventures/<slug>/finance/invoices.json` rows: `{"number", "date", "due", "customer", "currency", "net_minor", "vat_minor", "total_minor", "status": "draft"}`. `payment-tracking` reads it.
- Charlie sends the invoice and changes status to `sent`. Nothing is emailed by the job.

## The ladder
- Human-led: Charlie fills an invoicing app by hand each time.
- Human-assisted: the job drafts and numbers, Charlie checks the figures before sending.
- Fully autonomous (the setting here): drafts appear whenever a valid request lands; sending and chasing stay human.

## The human
What stays with Charlie: choosing the issuer and VAT status (with an accountant when the first venture earns), checking the total, sending it, and marking it `sent`.

## Tools
No model. Python stdlib on GitHub Actions, triggered when `invoice-requests.json` changes. Firecrawl free tier for the quarterly HMRC page read; as of Oct 2026, check the limit.

## Build notes
- One module, `foundry/invoices.py`, plus one HTML template with a CSS variable for the accent colour taken from the venture's brand file if present.
- Tests offline: rounding, mixed VAT, gapless numbering after a rejected request, idempotent re-run.
- Multi-currency invoices are issued in the customer's currency; conversion to GBP happens in `revenue-reporting`, never here.
