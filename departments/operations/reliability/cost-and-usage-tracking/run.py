"""Cost and Usage Tracking: GitHub implementation of departments/operations/reliability/cost-and-usage-tracking/SKILL.md.

Arithmetic only, no model. Seeds and refreshes limits.json, sums usage.jsonl and Actions minutes,
writes usage-summary.json and raises or resolves `source: cost` incidents in board.json (nothing
else in the board changes). It cannot pay for or stop anything: each incident names the action
for Charlie. Every limit is "as of Oct 2026, check the limit"; a limit it cannot read is kept, never guessed.
"""
import calendar
import datetime as dt
import json
import math
import re
from decimal import ROUND_HALF_UP, Decimal

import requests

from foundry import jobkit as k, util

FOUNDRY = "quickplay-studio/foundry"
SEEDS = [  # service, unit, period, limit (None until read), page to read it from
    ("github-actions", "minutes", "month", 2000, ""),
    ("gemini-2.5-flash", "requests", "day", None, "https://ai.google.dev/gemini-api/docs/rate-limits"),
    ("groq", "requests", "day", None, "https://console.groq.com/docs/rate-limits"),
    ("firecrawl", "credits", "month", None, "https://www.firecrawl.dev/pricing"),
    ("apify", "credits", "month", None, "https://apify.com/pricing"),
    ("supabase", "MAU", "month", None, "https://supabase.com/pricing"),
    ("posthog", "events", "month", None, "https://posthog.com/pricing"),
    ("cloudflare-pages-or-netlify", "builds", "month", None, "https://www.netlify.com/pricing/"),
]
UNIT_WORD = {"requests": "requests?|calls?", "credits": "credits?", "minutes": "minutes", "MAU": "MAU|monthly active users", "events": "events?", "builds": "builds?"}
SKIP_TOKENS = {"pages", "actions", "flash"}


def half_up(x, places=1):
    return float(Decimal(str(x)).quantize(Decimal(1).scaleb(-places), ROUND_HALF_UP))


def aliases(service):
    return {t for t in re.split(r"[^a-z]+", service.lower()) if len(t) > 3 and t not in SKIP_TOKENS}


def read_limit(text, unit):
    for m in re.finditer(r"free", text, re.I):
        n = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*([kKmM])?\s*(?:" + UNIT_WORD.get(unit, re.escape(unit)) + ")", text[m.start(): m.start() + 300], re.I)
        if n:
            v = float(n.group(1).replace(",", "")) * {"k": 1e3, "m": 1e6}.get((n.group(2) or "").lower(), 1)
            return int(v) if v == int(v) else v
    return None


def stale(checked, today):
    try:
        return (today - dt.date.fromisoformat(str(checked)[:10])).days > 30
    except ValueError:
        return True


def actions_minutes(repo, token, since):
    total = 0
    for page in (1, 2, 3):
        try:
            r = requests.get(f"https://api.github.com/repos/{repo}/actions/runs", params={"per_page": 100, "page": page, "created": f">={since}"},
                             headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json"}, timeout=25)
            runs = r.json().get("workflow_runs", []) if r.ok else None
        except Exception:  # noqa: BLE001
            runs = None
        if runs is None:
            return total if page > 1 else None
        for run in runs:
            try:
                a, b = (dt.datetime.fromisoformat(str(run[f]).replace("Z", "+00:00")) for f in ("run_started_at", "updated_at"))
                total += max(1, math.ceil((b - a).total_seconds() / 60))
            except (KeyError, ValueError):
                continue
        if len(runs) < 100:
            break
    return total


def pounds(x):
    return f"£{x:,.2f}".replace(".00", "")


def main(ctx):
    board = k.read(ctx, "board.json")
    if not isinstance(board, dict):
        return {"skipped": "no board.json: the venture has not launched"}
    today = dt.date.fromisoformat(util.today())
    month, token, days = today.strftime("%Y-%m"), k.secret("GH_TOKEN"), calendar.monthrange(today.year, today.month)[1]
    notes = []
    limits = [e for e in (k.read(ctx, "limits.json", []) or []) if isinstance(e, dict) and e.get("service")]
    for service, unit, period, limit, _ in SEEDS:
        if not any(e["service"] == service for e in limits):
            limits.append({"service": service, "unit": unit, "limit": limit, "period": period, "checked": today.isoformat() if limit else ""})
    unread = []
    for e in limits:
        src = next((s[4] for s in SEEDS if s[0] == e["service"]), "")
        if src and stale(e.get("checked"), today):
            value = read_limit(k.fetch(src), e.get("unit", ""))
            if value is None:
                unread.append(e["service"])
            else:
                e["limit"], e["checked"] = value, today.isoformat()
    if unread:
        notes.append("could not read limits for " + ", ".join(unread) + " (old entries kept, none guessed)")
    usage = []
    for line in (k.read(ctx, "usage.jsonl", "") or "").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and str(row.get("date", "")).startswith(month):
            usage.append(row)
    minutes = None
    if token:
        parts = [actions_minutes(r, token, month + "-01") for r in (FOUNDRY, f"quickplay-studio/{ctx['slug']}")]
        minutes = sum(p for p in parts if p) if any(p is not None for p in parts) else None
    if minutes is None:
        notes.append("Actions minutes not read" + ("" if token else ": no GH_TOKEN"))
    rows, incidents = [], [i for i in board.get("incidents") or [] if isinstance(i, dict)]
    wanted = {}  # incident key -> (severity, text)
    for e in limits:
        svc, unit, period, limit = e["service"], e.get("unit", ""), e.get("period", "month"), e.get("limit")
        mine = [u for u in usage if aliases(svc) & aliases(str(u.get("service", "")))]
        if period == "day":
            mine = [u for u in mine if str(u.get("date", ""))[:10] == today.isoformat()]
        used = (sum(int(u.get("tokens_in", 0) or 0) + int(u.get("tokens_out", 0) or 0) for u in mine) if unit == "tokens" else sum(int(u.get("calls", 0) or 0) for u in mine))
        if svc == "github-actions" and minutes is not None:
            used = minutes
        pct = half_up(used * 100 / limit) if isinstance(limit, (int, float)) and limit > 0 else None
        projected = used if period == "day" else int(half_up(used / today.day * days, 0))
        rows.append({"service": svc, "unit": unit, "used": used, "limit": limit, "pct": pct, "projected": projected, "generated": today.isoformat()})
        model = svc.startswith(("gemini", "groq"))
        move = f"Move this job to {'Groq' if svc.startswith('gemini') else 'Gemini'}." if model else "Wait for the reset or cut its use."
        if e.get("bill") or e.get("card_on_file"):
            wanted[svc] = ("high", f"{svc} shows a bill or a card on file. Free tools only until revenue: remove the card or leave the service.")
        elif pct is not None and pct >= 100:
            wanted[svc] = ("high", f"{svc} limit reached ({used} of {limit} {unit} per {period}). {move}")
        elif pct is not None and (pct >= 80 or (projected > limit and period != "day")):
            wanted[svc] = ("warn", f"{svc} at {pct}% of {limit} {unit} per {period}" + (f", projected {projected} by month end" if period != "day" else "") + f". {move}")
    budget = ctx["budget"] or {}
    spent, plan = round(float(budget.get("spent", 0) or 0) * 100), round(float(budget.get("ad_budget", 0) or 0) * 100)
    if plan > 0 and spent * 100 >= plan * 80:
        wanted["ad-budget"] = ("high", f"Ad spend is {pounds(spent / 100)} of the {pounds(plan / 100)} budget. Stop the campaign unless you approve more budget.")
    ceiling = re.search(r"target cost per sign-up:\**\s*£\s*([\d.]+)", k.read(ctx, "launch/ad-brief.md", "") or "", re.I)
    weekly = [w for w in board.get("weekly") or [] if isinstance(w, dict)]
    cps = weekly[-1].get("cost_per_sign_up") if weekly else None
    if ceiling and isinstance(cps, (int, float)) and spent > 5000 and cps > float(ceiling.group(1)):
        wanted["ad-kill-rule"] = ("high", f"Kill rule: cost per sign-up {pounds(cps)} is above the {pounds(float(ceiling.group(1)))} target after {pounds(spent / 100)} spent. Stop the campaign.")
    date = today.isoformat()
    for key, (sev, text) in wanted.items():
        live = next((i for i in incidents if i.get("source") == "cost" and i.get("service") == key and i.get("status") in ("open", "mitigated")), None)
        if live:
            live.update(severity=sev, what=text, last_seen=date)
        else:
            incidents.append({"id": f"cost-{key}-{date.replace('-', '')}", "date": date, "severity": sev, "what": text, "source": "cost", "status": "open", "service": key, "last_seen": date})
    pcts = {r["service"]: r["pct"] for r in rows}
    pcts["ad-budget"], pcts["ad-kill-rule"] = (spent * 100 / plan if plan else None), 0
    for i in incidents:  # resolve once use falls under 70 percent
        pct = pcts.get(i.get("service"))
        if i.get("source") == "cost" and i.get("status") == "open" and i.get("service") not in wanted and pct is not None and pct < 70:
            i["status"] = "resolved"
    skipped = [s for s in board.get("skipped") or [] if isinstance(s, dict)]
    done_jobs = [j["id"] for j in board.get("jobs") or [] if isinstance(j, dict) and j.get("status") in ("done", "review")]
    logged = {str(u.get("job")) for u in usage}
    notes += [f"no usage log from {j}" for j in done_jobs if j not in logged and not any(s.get("reason") == f"no usage log from {j}" for s in skipped)][:5]
    for note in notes:
        line = {"job": "cost-and-usage-tracking", "reason": note[:160], "date": date}
        if line not in skipped:
            skipped.append(line)
    board["incidents"], board["skipped"] = incidents[-100:], skipped[-40:]
    k.write(ctx, "limits.json", limits)
    k.write(ctx, "usage-summary.json", rows)
    k.write(ctx, "board.json", board)
    n_open = sum(1 for i in incidents if i.get("source") == "cost" and i.get("status") == "open")
    return {"summary": f"{len(rows)} services tracked, {n_open} open cost incidents" + (f"; {len(notes)} notes in skipped" if notes else ""), "flag": "caution" if n_open else "ok"}


if __name__ == "__main__":
    k.run(main)
