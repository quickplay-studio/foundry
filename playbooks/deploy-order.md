# Deploy order

What runs when a Lodestone idea is deployed, what each stage must produce, and the gate that opens the next one. The audit engine (`foundry/audit.py`) picks the jobs for the specific idea; this is the order and the rules.

## 0. Deploy
Lodestone marks the idea `building` and writes `ventures/<slug>/idea.json` here. The `launch` workflow runs the audit and writes `brain.md`, `plan.md`, `board.json`, `budget.json`. Cost: nothing. Time: two minutes.

## 1. Validate (Intelligence, free models on GitHub)
Jobs: `regulatory-screen`, `vertical-analysis`, `competitor-teardown`, `pricing-research`, `tam-market-sizing`, `trend-monitoring`, `audience-analysis`, `research-reports`, `adversarial-verification`.
Output: `ventures/<slug>/validate/report.md` with a go, no-go or pivot line at the top.
Gate: Charlie reads the report and sets `gates.validate` to `passed` in `board.json`. A no-go sends the idea back to Lodestone as `dropped` with the reason.

## 2. Clear (Legal, assisted)
Jobs: `trademark-and-name-check`, `consumer-law-check`, `data-protection`, `terms-of-service`, `privacy-policy`, `entity-and-structure` (first revenue venture only).
Output: `ventures/<slug>/clear/` with the name check, the draft terms and privacy policy, and a one-page list of rules the product must follow.
Gate: name clear, nothing regulated, Charlie confirms. A solicitor reviews the terms before the product takes money.

## 3. Build (Operations, Claude Code with Sonnet and Opus advisor)
Jobs: `project-scaffolding` (new repo `quickplay-studio/<slug>` from the venture template), `licence-audit`, `qa-and-verification`, `agent-evaluation`, `monitoring-and-alerting`, `cost-and-usage-tracking`, `handoff-docs`.
Output: a working MVP on a free host, tests green, a status line in `board.json`.
Gate: QA passes on real data; Charlie uses it once end to end.

## 4. Launch (Marketing, free models for copy, Charlie's money for ads)
Jobs: `landing-page-copy`, `seo-and-geo`, `og-and-share-surface`, `hook-writing`, `script-writing`, `caption-writing`, `carousel-production`, `video-production`, `image-generation`, `thumbnail-and-cover-design`, `lead-magnet-builds`, `cross-platform-adaptation`, `publishing`, `platform-and-ad-compliance`, `ad-creative`.
Output: landing page live, ten organic posts scheduled, an ad brief with three creatives, two audiences, a daily cap and a kill rule (stop if cost per sign-up is above the number in the brief after the first fifty pounds).
Gate: Charlie approves the brief and the budget in `budget.json`, pays the platform himself, and records the campaign id. Agents never hold a card.

## 5. Sell (Sales and Deals, B2B ideas only)
Jobs in `builds_on` order from `icp-definition` through `campaign-launch`, then `reply-classification` to `meeting-booking`, `proposal-generation`, `crm-hygiene`, `pipeline-reporting`.
Output: a list, a sequence, replies handled, meetings on the calendar.
Gate: first reply handled end to end without Charlie touching it.

## 6. Support (Customer)
Jobs: `ticket-triage`, `faq-and-self-serve`, `macro-authoring`, `onboarding-journeys`, `health-scoring`, `churn-prediction`, `advocacy-and-referrals`, `engagement-and-replies`.
Output: a support inbox that answers itself for the repeat questions and flags the rest.
Gate: first real ticket answered.

## 7. Run (Back Office, weekly)
Jobs: `budget-tracking`, `revenue-reporting`, `goal-pacing`, `cash-flow-forecasting`, `expense-categorisation`, `payment-tracking`, `news-and-mention-tracking`, `context-maintenance`.
Output: `budget.json` current, one weekly line in `board.json`: spent, revenue, sign-ups, cost per sign-up, verdict.
Kill rule: if after the approved budget the venture has no revenue and no sign-up trend, the verdict is `park`, the idea goes back to Lodestone as `watching`, and the agents stop. The dashboards keep the record.

## Rules that hold in every stage
- Every job reads `brain/company.md` and the venture brain first.
- `solo` jobs write their output and move on. `assisted` jobs open a pull request or a draft. `human` jobs produce a one-page brief and stop.
- A job that cannot run writes a line under `skipped` in `board.json` with the reason and does not block the stage.
