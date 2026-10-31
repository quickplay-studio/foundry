"""Handoff Docs: GitHub implementation of departments/operations/knowledge/handoff-docs/SKILL.md.

Stops unless qa/result.json is PASS and its sha is the venture repo's current main commit (read
with GH_TOKEN). Facts come from the repo tree and code by script; the free model only words one
paragraph, and its text is thrown away if it adds a number. Writes handoff.md for Charlie, and the
repo docs (runbook, architecture, known issues, README) staged under handoff/repo/ with the exact
git and gh commands in handoff/publish-commands.md: no pull request or push is made from here.
"""
import json
import re

import requests

from foundry import jobkit as k, util

API = "https://api.github.com"
KEY = re.compile(r"AIza[\w-]{20,}|gsk_\w{20,}|\bsk-[\w-]{20,}|ghp_\w{20,}")
BAD = re.compile("[" + chr(0x2013) + chr(0x2014) + "]")
ENV = re.compile(r"os\.environ(?:\.get)?\(?\[?\s*[\"']([A-Z][A-Z0-9_]+)|os\.getenv\(\s*[\"']([A-Z][A-Z0-9_]+)|process\.env\.([A-Z][A-Z0-9_]+)|secrets\.([A-Z][A-Z0-9_]+)")
TEXT = (".py", ".js", ".ts", ".html", ".yml", ".yaml", ".md", ".json", ".toml", ".txt", ".sh")


def gh(path, token, params=None, raw=False):
    try:
        r = requests.get(API + path, params=params, timeout=30, headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github.raw" if raw else "application/vnd.github+json"})
        return (r.text if raw else r.json()) if r.ok else None
    except Exception:  # noqa: BLE001
        return None


def tidy(text):
    return BAD.sub(", ", text).replace("!", ".")


def first_line(path, text):
    ext = path.rsplit(".", 1)[-1]
    pats = {"py": r'^\s*(?:"""\s*(.+?)\s*(?:"""|$)|#(?!!)\s*(.+))', "js": r"^\s*(?://\s*(.+)|/\*+\s*(.+?)\s*(?:\*/|$))", "ts": r"^\s*(?://\s*(.+)|/\*+\s*(.+?)\s*(?:\*/|$))",
            "yml": r"^\s*#\s*(.+)", "yaml": r"^\s*#\s*(.+)", "sh": r"^\s*#(?!!)\s*(.+)", "toml": r"^\s*#\s*(.+)", "html": r"<!--\s*(.+?)\s*-->|<title>(.+?)</title>", "md": r"^#\s+(.+)"}
    m = re.search(pats.get(ext, r"\A\Z"), text, re.M)
    return next((g for g in m.groups() if g), "")[:90] if m else ""


def read_table(ctx, rel):
    rows = k.read(ctx, rel, [])
    rows = rows.get("items") or rows.get("services") or [] if isinstance(rows, dict) else rows
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def main(ctx):
    slug, token, today = ctx["slug"], k.secret("GH_TOKEN"), util.today()
    qa = k.read(ctx, "qa/result.json")
    if not isinstance(qa, dict) or str(qa.get("verdict", "")).upper() != "PASS":
        return {"skipped": "QA not passed"}
    repo = f"quickplay-studio/{slug}"
    main_commit = gh(f"/repos/{repo}/commits/main", token) if token else None
    head = str(main_commit.get("sha", "")) if isinstance(main_commit, dict) else ""
    qa_sha = str(qa.get("sha", ""))
    if not head or not qa_sha:
        return {"skipped": "docs would describe an unverified build: cannot compare the QA sha with the repo's main commit" + ("" if token else " (no GH_TOKEN)")}
    if not (head.startswith(qa_sha) or qa_sha.startswith(head)):
        return {"skipped": "docs would describe an unverified build: main has moved since QA, re-run qa-and-verification"}
    tree = gh(f"/repos/{repo}/git/trees/main", token, {"recursive": "1"})
    paths = sorted(t["path"] for t in (tree or {}).get("tree", []) if isinstance(t, dict) and t.get("type") == "blob" and not t["path"].startswith((".git/", "node_modules/")))[:300] if isinstance(tree, dict) else []
    if not paths:
        return {"skipped": "the venture repo file tree could not be read"}
    order = sorted([p for p in paths if p.endswith(TEXT)], key=lambda p: (not p.startswith(("app/", ".github/", "docs/integrations", "README")), p))[:40]
    texts = {p: gh(f"/repos/{repo}/contents/{p}", token, raw=True) or "" for p in order}
    env = sorted({n for t in texts.values() for m in ENV.findall(t) for n in m if n})
    flows = []
    for p, t in texts.items():
        if p.startswith(".github/workflows/"):
            flows.append(f"{p.split('/')[-1]}: " + (", ".join(re.findall(r"cron:\s*['\"]([^'\"]+)['\"]", t)) or "no schedule"))
    limits = texts.get("docs/integrations/limits.md", "")[:1500]
    board = ctx["board"] if isinstance(ctx["board"], dict) else {}
    url = next((str(board.get(key)) for key in ("live_url", "url") if str(board.get(key) or "").startswith("http")), "")
    run_cmds = (["pip install -r requirements.txt"] if "requirements.txt" in paths else ["npm install"] if "package.json" in paths else []) + (["open app/index.html in a browser"] if "app/index.html" in paths else [])
    test_cmd = "python -m pytest -q tests" if any(p.startswith("tests/") and p.endswith(".py") for p in paths) else "npm test" if "package.json" in paths else "no automated tests found"
    idea = ctx["idea"]
    title, price = tidy(str(idea.get("title") or slug)), tidy(str(idea.get("money") or "price not set in idea.json"))
    files = [f"- `{p}`" + (f": {first_line(p, texts[p])}" if texts.get(p) and first_line(p, texts[p]) else "") for p in paths[:60]]
    blob = json.dumps([title, price, paths, env, flows, limits, url])
    answer = k.ask("Write one plain paragraph of at most 70 words saying how this small software venture fits together, using only the facts given: no new feature, price or limit, no numbers that are not in the facts. "
                   'Return JSON only: {"architecture": "<paragraph>"}\n\nFACTS\n' + blob[:5000])
    para = tidy(str(answer.get("architecture", ""))).strip() if isinstance(answer, dict) else ""
    if not (20 <= len(para) <= 600) or any(n not in blob for n in re.findall(r"\d+(?:[.,]\d+)*", para)):
        para = f"{title} is a small venture kept in one repository. The app files are in app/, the checks are in tests/ where present, and the schedules are listed below."
    status = k.read(ctx, "kickoff/access-status.json", {})
    access = [i for i in status.get("items", []) if isinstance(i, dict)] if isinstance(status, dict) else []
    missing = [i.get("name") for i in access if i.get("required") and i.get("state") != "ok"]
    mons = [m for m in (k.read(ctx, "monitors.json", []) or []) if isinstance(m, dict)]
    usage = read_table(ctx, "usage-summary.json") or read_table(ctx, "limits.json")
    skipped = [f"{s.get('job')}: {s.get('reason')}" for s in board.get("skipped") or [] if isinstance(s, dict)][-8:]
    warns = [ln.strip("-* ") for ln in str(k.read(ctx, "qa/report.md", "") or "").splitlines() if re.search(r"warn", ln, re.I)][:8]
    failed = [str(c.get("id")) for c in qa.get("checks", []) if isinstance(c, dict) and str(c.get("result", "")).lower() not in ("pass", "passed", "ok")]
    runbook = ["# Runbook", "", "## Run locally"] + [f"- `{c}`" if not c.startswith("open") else f"- {c}" for c in (run_cmds + [test_cmd])[:3]] + [
        "", "## Redeploy", "Push to main. The free host connected in the `deploy: connect free host` issue redeploys from main.", "",
        "## Roll back", "Revert the commit, push, wait for the host to redeploy.", "", "## Rotate a key", "Repository Settings, Secrets and variables, Actions. Replace the value of one of these names:"] + [f"- `{n}`" for n in env] + [
        "", "## What the monitors watch"] + ([f"- {m.get('id')} ({m.get('type')})" for m in mons] or ["- No monitors recorded yet."]) + [
        "", "## Free-tier limits (as of Oct 2026, check the limit)", limits or "No docs/integrations/limits.md in the repo yet.", "", "## Who to tell", "Charlie Page-Blair, by a GitHub issue in this repository."]
    arch = ["# Architecture", "", para, "", "## Schedules"] + [f"- {f}" for f in flows or ["none"]] + ["", "## Files"] + files
    known = ["# Known issues", ""] + [f"- QA warning: {w}" for w in warns] + [f"- QA check not passed: {c}" for c in failed] + [f"- Skipped: {s}" for s in skipped] + [
        "- Not tested: the commands in the runbook were not run by the job that wrote this file."]
    readme = [f"# {title}", price + ".", "", f"Live: {url or 'not recorded yet'}", "", "## Run", *[f"- {c}" for c in run_cmds or ["see docs/handoff/runbook.md"]], "", "## Test", f"- {test_cmd}", "", "See docs/handoff/ for the runbook and architecture."]
    docs = {"handoff/repo/docs/handoff/runbook.md": runbook, "handoff/repo/docs/handoff/architecture.md": arch, "handoff/repo/docs/handoff/known-issues.md": known, "handoff/repo/README.md": readme}
    for rel, lines in docs.items():
        body = tidy("\n".join(lines))
        if KEY.search(body):
            return {"skipped": "a key pattern appeared in the generated docs: nothing written"}
        for named in re.findall(r"`((?:app|tests|docs|\.github)/[\w./-]+)`", body):
            if named not in paths and not named.startswith("docs/handoff/"):
                body = body.replace(f"`{named}`", named + " (not found)")
        k.write(ctx, rel, body)
    table = ["| Service | Used | Limit |", "|---|---|---|"] + [f"| {r.get('service')} | {r.get('used', 'n/a')} | {r.get('limit', 'n/a')} {r.get('unit', '')} |" for r in usage[:10]] if usage else ["Usage and limits are not tracked yet."]
    note = [f"# {title}: handoff", f"{price}.", "", f"Live: {url or 'not recorded in board.json yet'}", f"QA: PASS on {qa.get('date') or today}, commit {qa_sha[:7]}.", "", "## Live and not live",
            f"- Live: {'the product at the URL above' if url else 'nothing recorded as live'}.", f"- Not live yet: {', '.join(missing) if missing else 'nothing flagged'}" + (" (required secrets not ok)." if missing else "."), "",
            "## Cost now", "Expected cost: nothing. Free-tier table (as of Oct 2026, check the limit):"] + table + ["", "## Next three actions",
            "1. Use the product once end to end.", f"2. Set gates.build to passed in ventures/{slug}/board.json.", "3. Start the Launch stage.", "", "## Where everything is",
            f"- Repo: {repo} (pull request `handoff: {slug}` once you run handoff/publish-commands.md).", f"- Docs staged in ventures/{slug}/handoff/repo/, runbook in docs/handoff/runbook.md.", f"- Board and monitors: ventures/{slug}/board.json and monitors.json."]
    k.write(ctx, "handoff.md", tidy("\n".join(note[:45])))
    cmds = ["# Publish the handoff docs", "", "Run from the root of the private foundry-ventures checkout. Nothing is pushed from the job.", "", "```", f"git clone https://github.com/{repo} /tmp/{slug}-handoff && cd /tmp/{slug}-handoff",
            "git checkout -b handoff", f"cp -r <ventures checkout>/ventures/{slug}/handoff/repo/. .", "git add -A && git commit -m \"handoff: docs\" && git push -u origin handoff", f"gh pr create -R {repo} --title \"handoff: {slug}\" --body \"Runbook, architecture, known issues and README.\"", "```", "", "This replaces README.md in the repo; the old text stays in git history."]
    k.write(ctx, "handoff/publish-commands.md", "\n".join(cmds))
    return {"summary": f"Handoff note and 4 repo docs staged for {repo} at commit {qa_sha[:7]}; {len(failed)} QA checks not passed, {len(missing)} required secrets not ok", "flag": "caution" if failed or missing else "ok"}


if __name__ == "__main__":
    k.run(main)
