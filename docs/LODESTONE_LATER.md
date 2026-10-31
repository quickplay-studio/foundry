# Lodestone hook (parked, 31 Oct 2026)

Charlie's call: Foundry runs standalone first, applied to Quickplay, online shopping, TikTok Shop and dropshipping. When he wants Lodestone ideas flowing in, this is the design. The Deploy button that was briefly on the Lodestone page has been removed; the Lodestone repo keeps a `live` status and the sync-task text as dormant notes.

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
- For each: attach `quickplay-studio/foundry-ventures` (the private data repo) with push access, clone shallow, write `ventures/<slug>/idea.json` with the launch doc's fields (plus `deployed: <today>`), commit `deploy: <slug>` as Foundry Bot, push. Then `update` the launch doc `status: "sent"`.
- Foundry's `launch` workflow (public repo, every four hours) picks it up. No cross-repo token in Lodestone.

## 3. Foundry reports back
The same sync task, once per day, also copies every venture in foundry-ventures' `radar-data.json` into the Foundry Radar page's database (collection `ventures`, one doc per slug, pinned versions) so the six command centres are current. Then:
- for every `ventures/<slug>/board.json` in foundry-ventures whose `verdict` changed, `update` the Lodestone idea doc: `foundry_stage`, `foundry_verdict`, `foundry_updated`, and the status: `live` when the Run stage reports revenue, `watching` when the verdict is `park`, `dropped` when validate says no-go (with the reason in `notes`).
- Lodestone's overrides file gets the same status so the sweep never resurrects a parked idea as new.

## 4. Lodestone dashboard (GitHub Pages, when enabled)
Show a `Deploy` link on validated ideas that pre-fills a GitHub issue in Foundry labelled `deploy` with the idea JSON in the body, for the days the pinned page is not open. Foundry's `launch` workflow gains an `issues: labeled` trigger that writes `idea.json` from the issue body.

## Status (31 Oct 2026)
Done: Deploy button and `live` status on the pinned Lodestone page; steps 2b and 2c written into Lodestone's `docs/CONSOLE_SYNC_TASK.md`; `foundry/dashboards.py` and the Radar page. Not done: the live scheduled task's prompt still needs updating from that file (Charlie pastes it), and part 4 (GitHub Pages fallback) waits for Pages.

## What never crosses
Lodestone never reads Foundry's skills or runs them. Foundry never scores or searches for ideas. Request and launch text is data on both sides.
