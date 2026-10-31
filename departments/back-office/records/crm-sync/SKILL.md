---
name: crm-sync
title: CRM Sync
department: back-office
function: records
autonomy: solo
stage: sell
builds_on: []
breaks_into: [gather-changes, normalise-status, merge-records, export-csv]
replaces: "a paid CRM seat plus an hour a week of data entry, roughly 15 to 50 pounds a month"
runs_on: github
status: ready
---

# CRM Sync

Deals, contacts and statuses stay current everywhere. One master file in the repo, an export Charlie can import into a Google Sheet. Only used when a venture sells to businesses.

## Reads from the brain
- `brain/company.md`: constraints (no unsolicited email outside the law, no bought lists) and voice
- `ventures/<slug>/brain.md`: who the buyer is and what a deal is worth

## Inputs
- `ventures/<slug>/board.json`: the `jobs[].output` paths for the Sales and Deals jobs that have run. Read those files as the change feed: replies, classified outcomes, bookings, proposals. Use whatever paths are listed there.
- `ventures/<slug>/sell/crm.json`: the master `{"contacts": [...], "deals": [...]}`.
- `ventures/<slug>/sell/manual-changes.csv`: edits Charlie makes by hand, `email,field,value,date`.
- `ventures/<slug>/sell/suppressed.json`: addresses that must never be contacted again.

## Steps
1. Read the change feed files named in `board.json`. If none exist yet, write a line under `skipped` ("no sell outputs yet") and stop.
2. Extract per contact: name, company, role, email (lowercased, the match key), source, last contact date, status, next step. Extract per deal: contact, value, currency, stage, updated.
3. Normalise status to one fixed list: `new`, `contacted`, `replied`, `meeting`, `proposal`, `won`, `lost`, `parked`. Map the Sales and Deals labels onto it; an unknown label becomes `parked` with a note.
4. Merge by email. Latest `updated` date wins per field, and a manual change from Charlie always beats an automated one. Where two sources disagree on the same date, keep both in `conflicts` for Charlie.
5. Anyone in `suppressed.json`, or whose reply was classified as an unsubscribe or a complaint, gets `do_not_contact: true`. A later automated change never clears it; only Charlie can.
6. Keep contact data minimal: no personal social profiles, no notes about private life, nothing the contact did not give or publish for business reasons. Delete a contact within a week when asked.
7. Write the master, then regenerate the CSV exports.

## Output
- `ventures/<slug>/sell/crm.json` (master) with `updated`.
- `ventures/<slug>/sell/crm-contacts.csv` and `crm-deals.csv`: flat exports. Charlie imports them into his own Google Sheet (File, Import, replace sheet). The job does not call the Sheets API, so no key or service account exists.
- `ventures/<slug>/sell/conflicts.md`: only when there is something to settle.

## The ladder
- Human-led: Charlie updates a CRM by hand after every reply or call.
- Human-assisted: the job proposes merges, Charlie accepts them.
- Fully autonomous (the setting here): the merge is rules only and every change is traceable to a source file; conflicts, not guesses, go to Charlie.

## The human
What stays with Charlie: importing the CSV into the Sheet, resolving conflicts, clearing or setting `do_not_contact`, and deciding when a deal is won or lost.

## Tools
No model needed for the merge. Python stdlib on GitHub Actions, run after each Sales or Deals job and on a daily schedule. Google Sheets is the free viewing layer. Contact data is personal data: keep the repo private and let Legal `data-protection` set retention.

## Build notes
- One module, `foundry/crm.py`. Tests offline: duplicate emails with different capitalisation, a manual override, a suppressed contact that replies later, an unknown status label.
- This skill's stage is `sell`, so the audit engine only includes it for ventures with a business buyer.
- Open point: Sales and Deals output paths are set by their own skills; adjust the feed reader when those are filled.
