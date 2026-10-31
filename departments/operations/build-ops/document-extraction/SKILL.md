---
name: document-extraction
title: Document Extraction
department: operations
function: build-ops
autonomy: solo
stage: build
builds_on: []
breaks_into: [list-and-hash, convert-to-text, extract-fields, validate-and-review]
replaces: "a data entry clerk or a paid OCR and extraction service"
runs_on: github
status: ready
---

# Document Extraction

Structured extraction from piles of documents at volume.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof

## Inputs
- Documents in `ventures/<slug>/extract/inbox/` (PDF, HTML, text, images), or a list of URLs in `extract/urls.txt`.
- `ventures/<slug>/extract/schema.json`: `{"fields": [{"name", "type": "string|number|date|money|enum", "required": true, "values": []}]}`. If absent, derive a draft from the `mvp` bullets in `brain.md`, save it with `"source": "derived"`, and carry on.
- Personal or client documents: do not send them to a free-tier model unless Legal `data-protection` has cleared it. Free-tier prompts may be used by the provider; check the terms. Without clearance use the regex route in step 4 only.

## Steps
1. List the inbox, take the sha256 of each file, and skip any hash already in `extract/index.json`. The job is safe to re-run.
2. Convert to text. PDFs with a text layer: `pdftotext -layout` (install `poppler-utils` in the workflow). Web pages: Firecrawl scrape (free tier, as of Oct 2026, check the limit), else `requests` plus the stdlib HTML parser. Scans and images: Gemini 2.5 Flash vision (free tier, check the limit). Never scrape against a site's terms.
3. Build one prompt per document: the schema, the text, and "Return JSON only. Use null for anything not in the text. Never guess." Send through the model chain in `foundry/util.py` (`ask_json`: Gemini, then Groq, then the heuristic).
4. Heuristic route for fields with a pattern (dates, money, reference numbers, postcodes): regex in `extract/patterns.py`. Use it when no model answers, and to cross-check the model on those fields.
5. Validate each record: types, required fields, enum values, dates as ISO, money as integer pence. Any failure moves the record to `needs-review.jsonl` with the reason. Nothing is silently corrected.
6. Process at most 200 documents per run (keeps the job inside the free Actions minutes and model limits); the rest wait for the next run.
7. Pick 5 percent of records (minimum 5) and write `spot-check.md`: source snippet beside the extracted values.
8. Set this job in `board.json` to `done` with the counts in `output`. If the model chain is empty and no pattern applies, add a `skipped` line with the reason.

## Output
- `ventures/<slug>/extract/records.jsonl`: one line per document: `{"source", "sha256", "fields": {}, "confidence": 0-1, "model", "status": "ok|needs_review"}`.
- `extract/index.json` (hashes done), `extract/needs-review.jsonl`, `extract/spot-check.md`.
- Counts line in `board.json`: processed, ok, needs_review, failed.

## The ladder
- Human-led: Charlie reads each document and types the fields.
- Human-assisted: the job extracts, Charlie works through `needs-review.jsonl`.
- Fully autonomous: the job extracts and validates; Charlie reads the spot check only. This is the default.

## The human
What stays with Charlie: defining what a correct record is (the schema), reading the spot check, clearing anything with personal data, and deciding whether a source may be used at all.

## Tools
Free first. Gemini 2.5 Flash and Groq free tiers, Firecrawl free tier, `pdftotext`, Apify free credit for sources a plain request cannot reach (as of Oct 2026, check the limit). Python stdlib plus `requests`. No Claude.

## Build notes
- Money is stored as integer pence, never floats.
- A `confidence` below 0.7 goes to review whatever the model said. Confidence is the share of required fields found verbatim in the source text.
- Keep the raw text out of git unless the repo is private and the documents are Charlie's own.
- QA (`qa-and-verification`) re-runs ten real documents through this job and compares by hand-checked answers.
