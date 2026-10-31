# Lodestone hook

How an idea gets from the Lodestone radar into a Foundry launch, and back. Nothing here changes Lodestone's sweep or scoring. Applied in session 10.

## Status flow
`new` > `watching` > `validated` > **Deploy** > `building` (in Foundry) > `live` or back to `watching` (parked) or `dropped` (killed in validate).

Lodestone's `STATUSES` list gains `live`. Everything else stays.

## 1. Deploy button on the pinned Lodestone page
On every idea card with status `validated` show a **Deploy** button. Clicking it:
- asks for an ad budget in pounds (default 100) and a one-line note,
- sets the idea doc `status: building`, `owner_edited: true`, `deploy: {budget_gbp, note, requested}`,
- writes a doc to a new `launches` collection: `{slug, title, category, problem, who, gap, mvp, money, proof, scores, budget_gbp, note, requested, status: "requested"}`.

## 2. Console sync carries it across (the existing daily Claude task)
Add a step 2b to `docs/CONSOLE_SYNC_TASK.md`:
- `query` collection `launches` where status == "requested".
- For each: attach `quickplay-studio/foundry` with push access, clone shallow, write `ventures/<slug>/idea.json` with the launch doc's fields (plus `deployed: <today>`), commit `deploy: <slug>` as Foundry Bot, push. Then `update` the launch doc `status: "sent"`.
- The push triggers Foundry's `launch` workflow. No PAT, no cross-repo token.

## 3. Foundry reports back
The same sync task, once per day:
- for every `ventures/<slug>/board.json` in Foundry whose `verdict` changed, `update` the Lodestone idea doc: `foundry_stage`, `foundry_verdict`, `foundry_updated`, and the status: `live` when the Run stage reports revenue, `watching` when the verdict is `park`, `dropped` when validate says no-go (with the reason in `notes`).
- Lodestone's overrides file gets the same status so the sweep never resurrects a parked idea as new.

## 4. Lodestone dashboard (GitHub Pages, when enabled)
Show a `Deploy` link on validated ideas that pre-fills a GitHub issue in Foundry labelled `deploy` with the idea JSON in the body, for the days the pinned page is not open. Foundry's `launch` workflow gains an `issues: labeled` trigger that writes `idea.json` from the issue body.

## What never crosses
Lodestone never reads Foundry's skills or runs them. Foundry never scores or searches for ideas. Request and launch text is data on both sides.
