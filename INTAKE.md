# Intake: putting a venture into Foundry

Foundry is a standalone workforce. Any venture goes in the same way: one `idea.json` in the private data repo `quickplay-studio/foundry-ventures` under `ventures/<slug>/`. The launch workflow (every four hours, public repo) audits it, writes the brain, plan and board, and the daily jobs run from there.

## The shape
`templates/idea.template.json`. The fields that matter most: `kind` (app, channel, shop, tiktok-shop, dropshipping, service), `problem`, `who`, `gap`, `mvp`, `money`, `channels`, `budget_gbp`, `note`. The audit drops departments the kind does not need: commerce only for shop, tiktok-shop and dropshipping; sell only when there is a business buyer.

## Three ways to add one
1. On GitHub, no tools: open https://github.com/quickplay-studio/foundry-ventures/new/main?filename=ventures/my-slug/idea.json, paste the template, fill it in, commit. Replace `my-slug` in the filename.
2. Locally: `python -m foundry.intake --slug my-slug --kind shop --title "My Shop" --problem "..." --who "..." --gap "..." --money "..." --mvp "first thing" --budget 100`, then commit and push inside `data/`.
3. In a Claude chat: describe the venture and ask for the idea.json to be written to foundry-ventures.

## Examples in the data repo
- `ventures/sample/`: an app, used to test the pipeline.
- `ventures/quickplay-daily/`: the Quickplay channel as a `channel` venture. Foundry runs alongside it (validate the niche, check platform rules, marketing insights, money tracking) and never edits the channel's own repo.
- `ventures/tiktok-shop-pilot/`: a placeholder `tiktok-shop` venture to exercise the commerce department. Edit problem, who and gap before trusting its audit.

## Moving a venture on
- Read `ventures/<slug>/plan.md` and the stage folders as outputs land.
- Jobs marked `review` in `board.json` are drafts waiting for you; change them to `done` once used.
- To open the next stage, set that stage's gate in `board.json` to `passed` (the first gate, validate, is what the Intelligence report earns).
- To stop a venture, set `verdict` to `park` or `kill`; jobs stop.

## Lodestone
Later, not now. `docs/LODESTONE_LATER.md` keeps the design for a Deploy button on the Lodestone page that writes the idea.json for you.
