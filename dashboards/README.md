# Dashboards: the six command centres

Static pages, no server, reading `ventures/*/board.json`, `budget.json` and `map/tree.json`. Built in session 9. Until then the map page (`docs/map.html`, pinned as the Foundry page) is the one view.

1. Radar: every venture, its stage, its verdict, days since deploy.
2. Pipeline: Sales and Deals state per B2B venture (lists, sequences, replies, meetings).
3. Marketing: posts scheduled, landing page live, ad brief status, cost per sign-up against the kill rule.
4. Build: MVP status, QA result, incidents, token and API spend against budget.
5. Customer: tickets, FAQ coverage, health scores, churn flags.
6. Finance: ad budget approved, spent, revenue, pace against the income target, cash runway.

Each page is one HTML file in this folder with the data inlined by a GitHub Actions step (`python -m foundry.dashboards`, session 9), so it works from a private repo without Pages.
