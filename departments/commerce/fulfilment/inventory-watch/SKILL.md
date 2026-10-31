---
name: inventory-watch
title: Inventory Watch
department: commerce
function: fulfilment
autonomy: solo
stage: run
builds_on: [catalogue-sync]
breaks_into: [read-stock, check-supplier-availability, set-pause-flags, alert-low-stock]
replaces: "a VA checking stock daily or a paid stock sync app"
runs_on: github
status: ready
---

# Inventory Watch

Stock levels and supplier availability watched; listings paused before an order cannot be filled.

Produces an inventory state and a pause list. A paused sku flows into the next catalogue export with zero availability.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof (delivery promise, order sizes)

## Inputs
- `ventures/<slug>/idea.json`: `kind` and `channels`.
- `ventures/<slug>/commerce/catalogue.json`: skus, stock, supplier ids and lead times.
- `ventures/<slug>/commerce/data/stock.csv`: `sku,stock,updated` for stock Charlie holds.
- `ventures/<slug>/commerce/data/orders.csv`: sales rate by sku over the last 14 days.
- `ventures/<slug>/commerce/suppliers.json`: supplier product page URLs where availability is shown.
- Optional: `ventures/<slug>/commerce/data/supplier-stock.csv` from a supplier feed or Charlie.

## Steps
1. Read `idea.json`; stop with a `skipped` line if the kind is not a commerce kind. Dropshipping watches supplier availability; shop and tiktok-shop watch own stock first and the supplier for restocks.
2. For each sku compute stock on hand, orders awaiting fulfilment, and daily sales rate (14-day average). Days of cover = available stock over daily sales rate; if no sales, cover is not limited.
3. Check supplier availability for each supplier-sourced sku: read the product page (Firecrawl or Apify, respecting the site's terms) for in-stock, out-of-stock, price change and "ships in N days" text, or use `supplier-stock.csv`. If a page cannot be read, mark the sku `unverified` and keep its previous state; never assume it is in stock.
4. Set thresholds per sku: `low` when cover is under the supplier lead time plus 3 days or stock under 3 units; `pause` when stock is zero, the supplier says out of stock, the price rose enough to take margin per unit below the floor in `pricing.json`, or `stock.csv` is older than 7 days (stale data).
5. Write the pause list. A paused sku is set to `paused` in `inventory.json` and `catalogue-sync` exports it with zero availability; `order-routing` blocks orders for it. Un-pause only when stock and supplier availability are both positive on two checks in a row.
6. Compute a reorder suggestion for each low sku: units to cover lead time plus 14 days at the current rate, with the supplier price break and total cost from `suppliers.json`. State it as a suggestion; Charlie orders.
7. Write an alert at the top of `inventory.md` listing paused, low and unverified skus with the reason. If any marketplace listing has live orders at risk, say so first.
8. Update `inventory.json` and set the job to `done`. A run with no changes writes no commit.

## Output
- `ventures/<slug>/commerce/inventory.json`: `{checked, items: [{sku, stock, awaiting, daily_rate, cover_days, supplier_status, state: "ok|low|paused|unverified", reason, reorder: {qty, cost_gbp}}]}`.
- `ventures/<slug>/commerce/inventory.md`: the alert list and reorder suggestions. Read by `catalogue-sync`, `order-routing` and Charlie.

## The ladder
- Human-led: Charlie checks stock in his seller centres each day.
- Human-assisted: Charlie uploads the pause list and reorders on the suggestions.
- Fully autonomous: the default for watching and flagging. Pausing a live listing needs a seller login, so Charlie applies the export; reordering is always his.

## The human
What stays with Charlie: keeping `stock.csv` current, uploading the next catalogue export, and every reorder.

## Tools
Free first. GitHub Actions every four hours for a venture with live listings, daily otherwise (check the Actions minutes limit as of Oct 2026); Firecrawl free tier (500 credits as of Oct 2026, check the limit) or Apify free monthly credit for supplier pages; Python stdlib. No paid stock tools.

## Build notes
- Credit use: check each supplier page at most once per run, and fewer for slow-moving skus.
- Unknown is never treated as in stock.
- Tests offline: fixtures for stock zero, a supplier page showing out of stock, an unreadable page, a stale stock file, and a price rise that breaks the floor.
- GitHub implementation: `run.py` beside this file (jobkit).
