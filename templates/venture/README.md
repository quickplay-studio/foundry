# {{name}}

{{problem}}

For: {{who}}.
Price: {{money}}

## Why it is worth building
{{gap}}

## MVP
{{mvp}}

## Status
Built by Foundry as venture `{{slug}}`. Plan, board and brain live in the Foundry repo under `ventures/{{slug}}/`. Build progress is tracked in `docs/mvp.md` and the issues labelled `mvp`.

## Run and test
- Open `app/index.html` in a browser.
- `python -m pytest -q tests`

## Deploy
Free host only: connect this repo to Cloudflare Pages or Netlify and publish the `app` directory (as of Oct 2026, check the limit). Keys go in the host's or GitHub's secrets, never in files.
