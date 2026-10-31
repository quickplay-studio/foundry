# Dashboards: the six command centres

One pinned Claude page, `docs/radar.html` (Foundry Radar), with six tabs. Its database holds one document per venture, written by the daily Lodestone console sync from `docs/radar-data.json`, which `python -m foundry.dashboards` rebuilds after every launch and every jobs run.

1. Radar: every venture, its stage, its verdict, days since deploy.
2. Pipeline: Sales and Deals state per B2B venture (lists, sequences, replies, meetings).
3. Marketing: posts scheduled, landing page live, ad brief status, cost per sign-up against the kill rule.
4. Build: MVP status, QA result, incidents, token and API spend against budget.
5. Customer: tickets, FAQ coverage, health scores, churn flags.
6. Finance: ad budget approved, spent, revenue, pace against the income target, cash runway.

The repo stays private and GitHub Pages is not needed: the page lives on claude.ai and only summaries cross.
