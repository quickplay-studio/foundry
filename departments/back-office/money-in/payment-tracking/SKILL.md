---
name: payment-tracking
title: Payment Tracking
department: back-office
function: money-in
autonomy: solo
stage: run
builds_on: [invoice-generation]
breaks_into: [read-exports, match-to-invoices, flag-late, write-ledger]
replaces: "a bookkeeper's monthly bank reconciliation, roughly 50 to 100 pounds a month"
runs_on: github
status: ready
---

# Payment Tracking

What is paid, due and late, without opening a bank app. Payment data comes only from CSV exports Charlie drops in a folder, never from a live bank or card connection.

## Reads from the brain
- `brain/company.md`: voice, constraints (no live bank connection, no card or account numbers stored)
- `ventures/<slug>/brain.md`: money, for the price and billing model (one-off, subscription, invoiced)

## Inputs
- `ventures/<slug>/finance/stripe-*.csv`: Stripe payment exports, once the venture takes money. Before that there are none, and that means no revenue, not an error.
- `ventures/<slug>/finance/bank-*.csv`: optional bank export for invoices paid by transfer.
- `ventures/<slug>/finance/invoices.json`: from `invoice-generation` (number, date, due, currency, total, status).
- `ventures/<slug>/finance/processed.json`: file names and SHA-256 hashes already read.

## Steps
1. For each venture folder with a `finance/` directory, list CSVs whose hash is not in `processed.json`.
2. Map columns by header name, case-insensitively: id, date, amount, currency, status, amount refunded, description. If date, amount, currency or status is missing, skip the file with a reason. Never ask a model to guess money columns. Check the header and one known row before trusting the units; convert to integer minor units (pence).
3. Keep only id, date, amount, currency, status, refunded amount, the description cut to 80 characters and any invoice reference matching `INV-\d{4}-\d{4}`. Drop customer names, emails, card details and any digit run longer than six characters in free text.
4. Normalise status to `paid`, `pending`, `failed` or `refunded`; a refund becomes a negative row linked to the original.
5. Match payments to invoices by reference. Failing that, match on exact amount and currency within 30 days of the invoice date, but only when exactly one open invoice fits. Anything else goes to `unmatched` for Charlie.
6. Set each invoice to `paid`, `part-paid`, `due` (before the due date) or `late` (after it, with `days_late`).
7. Merge rows into `payments.json`, de-duplicated by id. Add the file hash to `processed.json`.
8. With no exports at all, write the file with empty rows and the note `no payment exports yet, so no revenue`.

## Output
- `ventures/<slug>/finance/payments.json`:
  `{"currency": "GBP", "updated": "<iso>", "rows": [{"id", "date", "amount_minor", "currency", "status", "refunded_minor", "invoice", "source"}], "invoices": [{"number", "state", "days_late"}], "unmatched": []}`
- `ventures/<slug>/finance/payments.md`: paid this month, due in the next seven days, late list. `budget-tracking`, `revenue-reporting` and `collections` read these files.
- Skips go under `skipped` in `ventures/<slug>/board.json`.

## The ladder
- Human-led: Charlie opens Stripe and the bank each week and ticks invoices off.
- Human-assisted: the job matches and lists, Charlie resolves `unmatched`.
- Fully autonomous (the setting here): the job runs weekly after the exports land; Charlie only handles `unmatched` and failed payments.

## The human
What stays with Charlie: downloading the exports, confirming a bank transfer that cannot be matched, deciding what to do about a failed or disputed payment, and keeping account numbers out of the repo.

## Tools
No model. Python stdlib `csv` and `hashlib` in a GitHub Actions weekly job. Stripe's own CSV export is the free data source; check the export screen for the columns it offers.

## Build notes
- One module, `foundry/payments.py`. Minor-unit integers inside this file; `budget.json` keeps pounds to two decimals, so convert once at the boundary.
- Tests offline: a Stripe-shaped fixture, a refund, a duplicate file drop, a header that is missing, an unmatched payment.
- Runs before `budget-tracking` and `revenue-reporting` in the weekly order.
