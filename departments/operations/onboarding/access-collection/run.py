"""Access Collection: GitHub implementation of departments/operations/onboarding/access-collection/SKILL.md.

Reads kickoff/access.md, checks which secret names are present in this job's environment (names
and HTTP status only, never a value, length or prefix), makes one read-only call per known service
and writes kickoff/access-status.json. Charlie adds the secrets: the chase text, the check workflow
and the gh commands go to files, because nothing here opens issues or edits another repo.
"""
import datetime as dt
import re

import requests

from foundry import jobkit as k, util

KEY = re.compile(r"AIza[\w-]{20,}|gsk_\w{20,}|\bsk-[\w-]{20,}|ghp_\w{20,}")
CHECKS = {  # one read-only call each
    "GEMINI_API_KEY": lambda v: requests.get("https://generativelanguage.googleapis.com/v1beta/models", params={"key": v, "pageSize": 1}, timeout=20),
    "GROQ_API_KEY": lambda v: requests.get("https://api.groq.com/openai/v1/models", headers={"Authorization": "Bearer " + v}, timeout=20),
    "GH_TOKEN": lambda v: requests.get("https://api.github.com/rate_limit", headers={"Authorization": "Bearer " + v}, timeout=20),
}


def parse_rows(text):
    cols, rows = {"name": 0, "required": 2, "free tier": 3}, []
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        low = [c.lower() for c in cells]
        if "name" in low and "state" in low:
            cols = {c: low.index(c) for c in ("name", "required", "free tier") if c in low}
            continue
        name = cells[cols.get("name", 0)] if cells else ""
        if re.fullmatch(r"[A-Z][A-Z0-9_]{2,}", name):
            req = cells[cols["required"]].lower() if "required" in cols and len(cells) > cols["required"] else "yes"
            tier = cells[cols["free tier"]] if "free tier" in cols and len(cells) > cols["free tier"] else ""
            rows.append({"name": name, "required": req.startswith("y"), "service": re.sub(r"\s*\(.*", "", tier) or "its own free tier"})
    return rows


def age(since, today):
    try:
        return (dt.date.fromisoformat(today) - dt.date.fromisoformat(str(since))).days
    except ValueError:
        return 0


def check(name):
    """State for a present secret: ok, rejected, ok but rate limited, or present (no read-only call known)."""
    call = CHECKS.get(name)
    if not call:
        return "present"
    try:
        status = call(k.secret(name)).status_code
    except Exception:  # noqa: BLE001  (never keep the message: a URL may carry the key)
        return "present"
    return "ok" if 200 <= status < 300 else "rejected" if status in (401, 403) else "ok but rate limited" if status == 429 else "present"


def main(ctx):
    text = k.read(ctx, "kickoff/access.md", "") or ""
    rows = parse_rows(text)
    if not rows:
        return {"skipped": "kickoff/access.md is missing or has no secret rows"}
    slug, today = ctx["slug"], util.today()
    repo = f"quickplay-studio/{slug}" if k.read(ctx, "kickoff/scaffold.md") is not None else "quickplay-studio/foundry"
    old = {i.get("name"): i for i in (k.read(ctx, "kickoff/access-status.json", {}) or {}).get("items", []) if isinstance(i, dict)}
    items = []
    for r in rows:
        state = check(r["name"]) if k.secret(r["name"]) else "missing"
        item = {"name": r["name"], "required": r["required"], "state": state}
        if state not in ("ok", "ok but rate limited"):
            item["since"] = old.get(r["name"], {}).get("since") or today
        items.append(item)
    k.write(ctx, "kickoff/access-status.json", {"checked": util.now(), "items": items})
    todo = [i for i in items if i["required"] and i["state"] in ("missing", "rejected", "present")]
    stale = [i["name"] for i in todo if age(i["since"], today) >= 7]
    leaks = [rel for rel in ("brain.md", "board.json", "kickoff/note.md", "kickoff/access.md") if KEY.search(k.read(ctx, rel, "") if rel.endswith(".md") else str(k.read(ctx, rel, "")))]
    by_name = {r["name"]: r for r in rows}
    lines = [f"Add secret {i['name']} in {repo}: Settings, Secrets and variables, Actions. Free tier: {by_name[i['name']]['service']}. Paste the value nowhere else."
             for i in items if i["required"] and i["state"] in ("missing", "rejected")]
    body = [f"# access: {slug}", "", "States below come from this job's own environment. Run the check workflow in the venture repo for its secrets.", ""]
    body += [f"- [{'x' if i['state'] in ('ok', 'ok but rate limited') else ' '}] {i['name']} ({'required' if i['required'] else 'optional'}): {i['state']}" for i in items]
    body += ["", "## To do"] + (lines or ["Nothing: every required secret is ok or present."])
    if leaks:
        body += [f"A key pattern was found in {', '.join(leaks)}. Rotate that key now and remove it from the file."]
    body += ["", "## Commands for Charlie", "```", f"gh issue create -R {repo} --title \"access: {slug}\" --body-file kickoff/access-issue.md --label access",
             f"gh workflow run access-check.yml -R {repo}", "```", "Copy kickoff/access-check.yml to .github/workflows/access-check.yml in the venture repo first."]
    k.write(ctx, "kickoff/access-issue.md", "\n".join(body))
    steps = "\n".join(f'      - run: |\n          [ -n "${i["name"]}" ] && echo "{i["name"]}: present" || echo "{i["name"]}: missing"\n        env: {{{i["name"]}: ${{{{ secrets.{i["name"]} }}}}}}' for i in items)
    k.write(ctx, "kickoff/access-check.yml", "name: access-check\non: workflow_dispatch\njobs:\n  check:\n    runs-on: ubuntu-latest\n    steps:\n" + steps)
    done = not todo
    summary = f"{sum(i['state'].startswith('ok') for i in items)} of {len(items)} secrets ok" + ("" if done else f"; {len(todo)} required still to add (see kickoff/access-issue.md)")
    if stale:
        summary += f"; stale over 7 days: {', '.join(stale)}"
    if leaks:
        summary += f"; key pattern found in {', '.join(leaks)}, rotate it"
    return {"summary": summary, "flag": "ok" if done and not leaks else "caution"}


if __name__ == "__main__":
    k.run(main)
