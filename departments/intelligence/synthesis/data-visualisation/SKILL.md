---
name: data-visualisation
title: Data Visualisation
department: intelligence
function: synthesis
autonomy: solo
stage: validate
builds_on: [research-reports]
breaks_into: [pick-charts, render-svg, check-and-embed]
replaces: "a designer or analyst building charts by hand"
runs_on: github
status: ready
---

# Data Visualisation

A pile of research into charts that explain themselves.

## Reads from the brain
- `brain/company.md`: voice (plain, no hype), so chart titles state a finding in plain words
- `ventures/<slug>/brain.md`: problem and who, to keep the charts on the question

## Inputs
- `ventures/<slug>/validate/report.md` and the sidecars it cites: `vertical-analysis.json` (`trend`), `competitor-teardown.json` (`gaps`), `pricing-research.json` (`plans`, `anchors`, `band`), `tam-market-sizing.json` (`tam`, `sam`, `som`), `verdict.json` (`signals`).
- Env: `GEMINI_API_KEY`, `GROQ_API_KEY`. Nothing is fetched from the web.
- Ad hoc: any CSV or JSON Charlie drops in `ventures/<slug>/research/data/`.

## Steps
1. List what can be charted from the sidecars by data shape: values compared across items is a horizontal bar; values over time is a line; parts of a whole is a stacked bar; a funnel is a bar per stage; pass, warn and fail across jobs is a scorecard. Skip any series with fewer than 3 points.
2. Ask Gemini 2.5 Flash (free tier, about 10 requests a minute and 250 a day as of Oct 2026, check; Groq as fallback) for a chart spec per candidate as JSON: type, which sidecar keys feed it, title, axis labels, units. Keep at most five. The model writes no numbers; it only points at keys.
3. Render each chart as an SVG in plain Python, no plotting library. Use the Okabe-Ito colour-blind safe palette (`#0072B2`, `#E69F00`, `#009E73`, `#D55E00`, `#56B4E9`, `#CC79A7`), a white background and dark text so it reads on a light or dark GitHub theme. Never encode meaning in colour alone: add direct labels, and a different marker or pattern per series. Include `<title>` and `<desc>` for screen readers.
4. Title each chart as the finding in under 12 words, for example "Median rival charges 4.99 pounds a month". Code checks that every number in a title exists in the chart's data; if not, use a plain title of the form "<measure> by <item>, <unit>".
5. Write the data behind each chart to `charts/<name>.json` (labels, values, sidecar key, source urls). Add a source line under each chart and a small markdown table of the values beneath it so the figures can be read and checked.
6. Replace the empty block between `<!-- charts:start -->` and `<!-- charts:end -->` in `report.md` with image links and tables. Touch nothing else in the report, and never edit line 1.

## Output
- `ventures/<slug>/validate/charts/<name>.svg` and `<name>.json`, at most five pairs, names such as `scorecard`, `competitor-prices`, `demand-trend`, `tam-funnel`, `complaint-themes`.
- `ventures/<slug>/validate/report.md` with the charts block filled.
- Update `ventures/<slug>/board.json`; a skipped chart goes under `skipped` with the reason (too few points).

## The ladder
- Human-led: Charlie builds the charts in a spreadsheet and pastes them in.
- Human-assisted: the job proposes and draws; Charlie removes any chart that does not help.
- Fully autonomous: charts are drawn from the sidecars at launch and embedded with no review.

## The human
What stays with Charlie: deciding which chart earns its place, and anything shown to an outside audience.

## Tools
Python standard library SVG strings, Mermaid for diagrams (rendered by GitHub), Gemini 2.5 Flash, Groq, GitHub Actions. No Claude, no paid chart service.

## Build notes
- A small renderer (`bar`, `line`, `funnel`, `scorecard`) of about 150 lines; stay inside stdlib plus `requests`.
- Run after `research-reports` and before `adversarial-verification`, so the challenge pass can check chart data against the sidecars. The index does not enforce this order; the workflow does.
- Tests offline: render each type from a fixture and assert the SVG contains the labels and the title check works.
