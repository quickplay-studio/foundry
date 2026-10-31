---
name: expense-categorisation
title: Expense Categorisation
department: back-office
function: records
autonomy: solo
stage: run
builds_on: []
breaks_into: [read-spend, apply-rules, categorise-the-rest, accountant-export]
replaces: "a bookkeeper's transaction coding, roughly 30 to 80 pounds a month"
runs_on: github
status: ready
---

# Expense Categorisation

Spend categorised for the accountant before they ask. Every row gets a category, a venture and a confidence; weak rows are queued for Charlie, not guessed.

## Reads from the brain
- `brain/company.md`: constraints (free tools only before first revenue, so most rows will be ads, domains and fees)
- `ventures/<slug>/brain.md`: money, so shared costs can be assigned to the right venture

## Inputs
- `ventures/<slug>/finance/spend.csv`: `date,amount,currency,merchant,description,kind`, from Charlie's card or bank export trimmed to those columns, plus `ads-*.csv` platform exports.
- `office/finance/spend-shared.csv`: same columns for costs that belong to no one venture.
- `office/finance/categories.json`: `{"categories": [...], "rules": [{"match", "category", "venture"}]}`. Seed categories: advertising, software and online services, domains and hosting, professional fees, payment and bank fees, travel, equipment, other. Each carries an `hmrc_heading` field naming the self-employment expense heading it maps to; verify the headings against the current gov.uk notes, read through Firecrawl, once a year.
- `office/finance/expenses-confirmed.json`: rows Charlie has confirmed, which become new rules.

## Steps
1. Read new rows only (a row key is `date|amount|merchant|description`). Reject rows with no date or amount into `needs_review` with a reason.
2. Clean text before anything else: remove any run of seven or more digits, so no card or account number ever reaches a file or a model.
3. Apply rules first: the longest matching `match` wins, case-insensitive on merchant then description. Confirmed rows from `expenses-confirmed.json` outrank seed rules.
4. Send the remaining rows to Gemini 2.5 Flash, then Groq, in batches of 50, with only date, amount, merchant, description and the category list. Ask for JSON `{index, category, venture, confidence}`. Accept only categories on the list; anything else becomes `other` with confidence 0.
5. Rows with confidence below 0.7, or from the heuristic fallback, are marked `needs_review: true`. The heuristic fallback is the keyword match only, so it never invents a category.
6. Set `kind` for `budget-tracking`: advertising becomes `ad`, software becomes `tool`, domains becomes `domain`, payment fees becomes `fee`, everything else `other`.
7. Write the outputs and a monthly accountant export. Never delete a row; a corrected row replaces the old one with a note.

## Output
- `ventures/<slug>/finance/expenses.json` and `office/finance/expenses.json`: `[{"key", "date", "amount", "currency", "merchant", "category", "kind", "venture", "confidence", "needs_review", "receipt"}]`. `budget-tracking` reads the first.
- `office/finance/accountant/2026-10.csv`: date, venture, merchant, description, category, hmrc_heading, amount, currency, receipt path, confirmed. This is what an accountant would be handed.
- `office/finance/review.md`: the `needs_review` rows, ten at most per run, with the model's best guess. Charlie's answers go into `expenses-confirmed.json`.

## The ladder
- Human-led: Charlie codes each transaction in a spreadsheet at year end.
- Human-assisted: the job proposes, Charlie confirms all rows.
- Fully autonomous (the setting here): confident rows are final for reporting; only the weak ones come back to Charlie, and his answers teach the rules.

## The human
What stays with Charlie: answering the review queue, deciding what is a business expense at all (the job categorises, it does not rule on what is allowable), and passing the export to an accountant.

## Tools
Python stdlib `csv`. Gemini 2.5 Flash then Groq free tiers for the uncertain rows; as of Oct 2026, check the limits. GitHub Actions weekly schedule, first in the Run order. Firecrawl free tier for the yearly HMRC heading check; check the limit.

## Build notes
- One module, `foundry/expenses.py`. Keep the rules file small and readable; it is the real asset.
- Tests offline: a rule hit, a model reply with an invalid category, a digit run stripped, a re-run that adds nothing.
- Receipts are filed by `document-filing-and-retrieval`; link by its index id, not by copying files.
- GitHub implementation: `run.py` beside this file (jobkit).
