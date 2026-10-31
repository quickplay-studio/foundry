"""Monitoring and Alerting: GitHub implementation of departments/operations/reliability/monitoring-and-alerting/SKILL.md.

Checks workflow runs, live URLs and file freshness, keeps failure counts in monitor-state.json and
writes incidents and skipped lines into board.json (nothing else in it changes). It never says a
check passed when it could not run. Alert issues are not opened from here: alerts.md holds the
exact gh commands. Read-only GitHub API calls use GH_TOKEN. No model.
"""
import datetime as dt
import re
import shlex

import requests

from foundry import jobkit as k, util

API, FOUNDRY = "https://api.github.com", "quickplay-studio/foundry"


def gh(path, token, params=None, raw=False):
    """GET a GitHub API path: JSON (or text when raw), or None on any failure."""
    try:
        r = requests.get(API + path, params=params, timeout=20, headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github.raw" if raw else "application/vnd.github+json"})
        return (r.text if raw else r.json()) if r.ok else None
    except Exception:  # noqa: BLE001
        return None


def hours_since(stamp):
    return (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))).total_seconds() / 3600


def max_age(crons):
    """Default max_age_hours: 26 for a daily schedule, twice the interval for anything more frequent."""
    best = None
    for cron in crons:
        f = cron.split()
        if len(f) != 5:
            continue
        m, h, dom, _, dow = f
        if h.startswith("*/") and h[2:].isdigit():
            step = int(h[2:])
        elif h == "*":
            step = max(int(m[2:]) / 60, 1) if m.startswith("*/") and m[2:].isdigit() else 1
        elif "," in h:
            step = 24 // len(h.split(","))
        else:
            step = 168 if dow != "*" else 720 if dom != "*" else 24
        age = 26 if step == 24 else step * 2 if step < 24 else step + 2
        best = age if best is None else min(best, age)
    return int(best or 26)


def scheduled(repo, name, text):
    crons = re.findall(r"cron:\s*['\"]([^'\"]+)['\"]", text)
    if "schedule" in text and crons:
        return {"id": f"{repo.split('/')[-1]}:{name}", "type": "workflow", "repo": repo, "workflow": name, "max_age_hours": max_age(crons)}


def build_monitors(ctx, token, skipped):
    out = []
    for p in sorted((util.ROOT / ".github" / "workflows").glob("*.yml")):
        out += [m for m in [scheduled(FOUNDRY, p.name, p.read_text(encoding="utf-8"))] if m]
    repo = f"quickplay-studio/{ctx['slug']}"
    listing = gh(f"/repos/{repo}/contents/.github/workflows", token) if token else None
    if isinstance(listing, list):
        for f in listing:
            name = str(f.get("name", ""))
            text = gh(f"/repos/{repo}/contents/.github/workflows/{name}", token, raw=True) if name.endswith((".yml", ".yaml")) else None
            out += [m for m in [scheduled(repo, name, text or "")] if m]
    else:
        skipped.append("venture repo workflows not readable" if token else "no GH_TOKEN: venture repo workflows not listed")
    url = next((str(ctx["board"].get(key)) for key in ("live_url", "url", "live") if str(ctx["board"].get(key) or "").startswith("http")), "")
    if url:
        out.append({"id": "live-url", "type": "url", "url": url, "expect_text": "", "max_age_hours": 0})
    return out


def check(m, token):
    """(True, '') passed, (False, what) failed, (None, reason) could not run."""
    kind = m.get("type")
    if kind == "url":
        try:
            r = requests.get(m["url"], timeout=15)
        except Exception as exc:  # noqa: BLE001
            return False, f"{m['url']} did not answer ({type(exc).__name__})"
        if r.status_code != 200:
            return False, f"{m['url']} returned HTTP {r.status_code}"
        return (False, f"{m['url']} is missing the expected text") if m.get("expect_text") and m["expect_text"] not in r.text else (True, "")
    if not token:
        return None, "no GH_TOKEN"
    limit = float(m.get("max_age_hours") or 26)
    if kind == "workflow":
        data = gh(f"/repos/{m.get('repo')}/actions/workflows/{m.get('workflow')}/runs", token, {"per_page": 5})
        if not isinstance(data, dict):
            return None, f"GitHub API error for {m.get('id')}"
        done = [r for r in data.get("workflow_runs", []) if r.get("status") == "completed"]
        if done and done[0].get("conclusion") == "failure":
            return False, f"{m.get('workflow')} last run failed {done[0].get('html_url', '')}".strip()
        good = [r for r in done if r.get("conclusion") == "success"]
        if not good or hours_since(good[0].get("updated_at", "")) > limit:
            return False, f"{m.get('workflow')} has no successful run in {limit:g} hours (silent stall)"
        return True, ""
    if kind == "file":
        data = gh(f"/repos/{m.get('repo')}/commits", token, {"path": m.get("path", ""), "per_page": 1})
        if not isinstance(data, list):
            return None, f"GitHub API error for {m.get('id')}"
        stamp = (data[0].get("commit", {}).get("committer", {}) or {}).get("date") if data else None
        return (True, "") if stamp and hours_since(stamp) <= limit else (False, f"{m.get('path')} not committed in {limit:g} hours")
    return None, f"unknown monitor type for {m.get('id')}"


def main(ctx):
    board = k.read(ctx, "board.json")
    if not isinstance(board, dict):
        return {"skipped": "no board.json: the venture has not launched"}
    token, today, slug = k.secret("GH_TOKEN"), util.today(), ctx["slug"]
    reasons = []
    monitors = k.read(ctx, "monitors.json")
    if not isinstance(monitors, list):
        monitors = build_monitors(ctx, token, reasons)
        k.write(ctx, "monitors.json", monitors)
    raw_state = k.read(ctx, "monitor-state.json", {}) or {}
    state = raw_state.get("monitors", {}) if isinstance(raw_state, dict) else {}
    incidents = [i for i in board.get("incidents") or [] if isinstance(i, dict)]
    opened = []
    for m in [m for m in monitors if isinstance(m, dict) and m.get("id")]:
        try:
            ok, what = check(m, token)
        except Exception as exc:  # noqa: BLE001
            ok, what = None, f"{m['id']} check error: {type(exc).__name__}"
        if ok is None:
            what = "no GH_TOKEN: workflow and file checks not run" if what == "no GH_TOKEN" else what
            if what not in reasons:
                reasons.append(what)
            continue
        st = state.setdefault(m["id"], {"fails": 0, "passes": 0})
        st["fails"], st["passes"] = (0, st.get("passes", 0) + 1) if ok else (st.get("fails", 0) + 1, 0)
        live = next((i for i in incidents if i.get("source") == m["id"] and i.get("status") in ("open", "mitigated")), None)
        if ok and live and st["passes"] >= 2:
            live["status"] = "resolved"
        elif not ok and st["fails"] >= (2 if m.get("type") == "url" else 1):
            if live:
                live["last_seen"], live["what"] = today, what
            else:
                n = sum(1 for i in incidents if str(i.get("id", "")).startswith("inc-" + today.replace("-", ""))) + 1
                new = {"id": f"inc-{today.replace('-', '')}-{n}", "date": today, "severity": "high" if m.get("type") == "url" else "warn",
                       "what": what, "source": m["id"], "status": "open", "last_seen": today}
                incidents.append(new)
                opened.append(new)
    skipped = [s for s in board.get("skipped") or [] if isinstance(s, dict)]
    for reason in reasons:
        line = {"job": "monitoring-and-alerting", "reason": reason[:160], "date": today}
        if line not in skipped:
            skipped.append(line)
    board["incidents"], board["skipped"] = incidents[-100:], skipped[-40:]
    k.write(ctx, "board.json", board)
    k.write(ctx, "monitor-state.json", {"checked": util.now(), "monitors": state})
    if opened:
        cmds = ["gh issue create -R %s --title %s --body %s" % (FOUNDRY, shlex.quote("incident: %s %s" % (slug, i["source"])), shlex.quote(i["what"])) for i in opened]
        k.write(ctx, "alerts.md", "# Alerts to open\n\nNo issue is opened from the job. Run these once so GitHub notifies you.\n\n```\n" + "\n".join(cmds) + "\n```")
    n_open = sum(1 for i in incidents if i.get("status") in ("open", "mitigated"))
    return {"summary": f"{len(monitors)} monitors, {len(opened)} new incidents, {n_open} open" + (f"; could not run: {'; '.join(reasons)[:120]}" if reasons else ""),
            "flag": "caution" if opened or n_open or reasons else "ok"}


if __name__ == "__main__":
    k.run(main)
