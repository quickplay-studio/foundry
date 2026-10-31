"""QBR Prep: GitHub implementation of departments/customer/success/qbr-prep/SKILL.md.

Builds the review of the last full calendar quarter. Every number is computed in code from PostHog or
support/data/ exports, tickets, health history and board.json; the model only words the story from
the numbers. Blank cells mean a missing source. Account pages only in b2b account mode. Nothing is sent.
"""
import csv
import json
import re
import statistics
from collections import Counter
from datetime import date, datetime, timedelta, timezone

import requests

from foundry import jobkit as k, util

ROWS = [("sign_ups", "Sign-ups"), ("activation_rate", "Activation rate (%)"), ("active_28d", "28-day active users"), ("paying_users", "Paying users"),
        ("revenue", "Revenue (GBP)"), ("refunds", "Refunds (GBP)"), ("cancellations", "Cancellations"), ("tickets", "Tickets"),
        ("median_first_response_h", "Median first response (hours)"), ("macro_share", "Tickets answered by macro (%)"),
        ("green", "Green accounts at quarter end"), ("amber", "Amber accounts"), ("red", "Red accounts"), ("spent", "Ad spend (GBP)"), ("cost_per_sign_up", "Cost per sign-up (GBP)")]


def d(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def span(y, q):
    start = date(y, 3 * q - 2, 1)
    return start, (date(y + (q == 4), (3 * q) % 12 + 1, 1) - timedelta(days=1))


def rows(ctx, rel):
    p = ctx["folder"] / rel
    return [{str(a).lower().strip(): b for a, b in r.items()} for r in csv.DictReader(p.open(encoding="utf-8-sig"))] if p.exists() else []


def hogql(query):
    key, pid = k.secret("POSTHOG_API_KEY"), k.secret("POSTHOG_PROJECT_ID")
    for host in ("us", "eu") if key and pid else ():
        try:
            r = requests.post(f"https://{host}.posthog.com/api/projects/{pid}/query/", json={"query": {"kind": "HogQLQuery", "query": query}},
                              headers={"Authorization": f"Bearer {key}"}, timeout=60)
            if r.ok:
                return r.json().get("results", [])
        except Exception:  # noqa: BLE001
            continue
    return None


def num(v):
    try:
        return float(re.sub(r"[^\d.\-]", "", str(v)))
    except ValueError:
        return None


def main(ctx):
    today = datetime.now(timezone.utc).date()
    cur = (today.month - 1) // 3 + 1
    y, q = (today.year, cur - 1) if cur > 1 else (today.year - 1, 4)
    start, end = span(y, q)
    ny, nq = (y, q + 1) if q < 4 else (y + 1, 1)
    nstart, nend = span(ny, nq)
    py, pq = (y, q - 1) if q > 1 else (y - 1, 4)
    tag, missing, n = f"{y}-q{q}", [], {}
    ev = k.read(ctx, "support/events.json", {}) or {}
    sig, act = ev.get("signup", "signed_up"), ev.get("activation", "activated")
    got = hogql(f"SELECT uniqIf(distinct_id, event = '{sig}'), uniqIf(distinct_id, event = '{act}'), uniqIf(distinct_id, timestamp >= toDateTime('{end - timedelta(days=27)}')) "
                f"FROM events WHERE timestamp >= toDateTime('{start}') AND timestamp < toDateTime('{end + timedelta(days=1)}')") if re.fullmatch(r"\w{2,40}", str(sig)) and re.fullmatch(r"\w{2,40}", str(act)) else None
    if got and len(got[0]) == 3:
        n["sign_ups"], n["active_28d"] = int(got[0][0]), int(got[0][2])
        n["activation_rate"] = round(100 * got[0][1] / got[0][0]) if got[0][0] else None
    else:
        e = [r for r in rows(ctx, "support/data/events.csv") if d(r.get("date")) and start <= d(r["date"]) <= end]
        if e:
            su, ac = {r["user_id"] for r in e if r.get("event") == sig}, {r["user_id"] for r in e if r.get("event") == act}
            n["sign_ups"], n["activation_rate"] = len(su), (round(100 * len(ac) / len(su)) if su else None)
            n["active_28d"] = len({r["user_id"] for r in e if d(r["date"]) >= end - timedelta(days=27)})
        else:
            missing.append("PostHog or support/data/events.csv")
    pay = rows(ctx, "support/data/payments.csv")
    if pay:
        n["paying_users"] = len({r.get("user_id") for r in pay if (r.get("status") or "active").lower() in ("active", "past_due", "trialing") and r.get("plan", "x")})
        n["cancellations"] = len({r.get("user_id") for r in pay if start <= (d(r.get("cancelled_on") or r.get("canceled_at") or "") or date.min) <= end})
        events = [r for r in pay if d(r.get("date")) and start <= d(r["date"]) <= end and num(r.get("amount")) is not None]
        if events:
            n["refunds"] = round(sum(abs(num(r["amount"])) for r in events if num(r["amount"]) < 0 or "refund" in str(r.get("type", "")).lower()), 2)
            n["revenue"] = round(sum(num(r["amount"]) for r in events if num(r["amount"]) > 0 and "refund" not in str(r.get("type", "")).lower()), 2)
    else:
        missing.append("support/data/payments.csv")
    weekly = [w for w in (ctx["board"].get("weekly") or []) if isinstance(w, dict) and d(w.get("week") or w.get("date") or "") and start <= d(w.get("week") or w.get("date")) <= end]
    if weekly:
        n["spent"] = round(sum(num(w.get("spent")) or 0 for w in weekly), 2)
        n["revenue"] = n.get("revenue", round(sum(num(w.get("revenue")) or 0 for w in weekly), 2))
        n["sign_ups"] = n.get("sign_ups", int(sum(num(w.get("sign_ups")) or 0 for w in weekly)))
        n["cost_per_sign_up"] = round(n["spent"] / n["sign_ups"], 2) if n.get("sign_ups") else None
    tix = [t for t in (k.read(ctx, "support/tickets.json", {}) or {}).get("tickets", []) if isinstance(t, dict) and d(t.get("received")) and start <= d(t["received"]) <= end]
    cats = Counter(t.get("category", "other") for t in tix)
    if tix:
        n["tickets"] = len(tix)
        n["macro_share"] = round(100 * sum(1 for t in tix if t.get("macro_id") and t.get("route") in ("auto-reply", "draft")) / len(tix))
        n["median_first_response_h"] = statistics.median(x for x in (num(t.get("first_response_hours")) for t in tix) if x is not None) if any(num(t.get("first_response_hours")) is not None for t in tix) else None
    else:
        missing.append("tickets")
    snaps = sorted(p for p in (ctx["folder"] / "support" / "health-history").glob("*.json") if d(p.stem) and start <= d(p.stem) <= end) if (ctx["folder"] / "support" / "health-history").exists() else []
    if snaps:
        n.update((b, (util.read_json(snaps[-1], {}) or {}).get("summary", {}).get(b)) for b in ("green", "amber", "red"))
    else:
        missing.append("health history for the quarter")
    asks = Counter(" ".join(str(t.get("summary", "")).lower().split()[:8]) for t in tix if t.get("category") == "feature-request")
    prev = k.read(ctx, f"support/qbr/{py}-q{pq}.json", None)
    pn = (prev or {}).get("numbers", {})
    ans = k.ask('Write the narrative for a quarterly review from these numbers only. Every sentence must trace to a number given. Do not calculate or round. Return JSON only: '
                '{"what_changed": ["..."], "causes": ["up to three the data supports"], "risks": ["..."], "actions": [{"action": "...", "owner": "Charlie or a job name", "date": "YYYY-MM-DD"}]}\n'
                f"NUMBERS: {json.dumps(n)}\nPREVIOUS: {json.dumps(pn)}") if n else None
    ans = ans if isinstance(ans, dict) else {}
    digits = set(re.findall(r"\d+", json.dumps(n)))
    trace = lambda key: [str(s) for s in (ans.get(key) if isinstance(ans.get(key), list) else []) if re.search(r"\d+", str(s)) and set(re.findall(r"\d+", str(s))) & digits][:5]
    acts = [a for a in (ans.get("actions") if isinstance(ans.get("actions"), list) else []) if isinstance(a, dict) and a.get("action")][:5]
    for i, a in enumerate(acts):
        a["owner"] = str(a.get("owner") or "Charlie")[:40]
        a["date"] = a["date"] if d(a.get("date")) and nstart <= d(a["date"]) <= nend else (nstart + timedelta(days=7 * (i + 1))).isoformat()
    acts = acts or [{"action": "Read this draft, edit the story and choose the actions", "owner": "Charlie", "date": (nstart + timedelta(days=7)).isoformat()}]
    md = [f"# Quarterly review {y} Q{q} ({start:%d %B} to {end:%d %B %Y})", "", "Draft for Charlie to edit. Nothing here goes to customers.", ""]
    if missing:
        md += [f"Missing sources, rows left blank: {', '.join(missing)}.", ""]
    if not prev:
        md += ["First quarter on record, so there is no comparison.", ""]
    md += ["## Numbers", "", "| Metric | This quarter | Last quarter | Change | Goal |", "|---|---|---|---|---|"]
    for key, label in ROWS:
        v, p = n.get(key), pn.get(key)
        md.append(f"| {label} | {'' if v is None else v} | {'' if p is None else p} | {round(v - p, 2) if prev and isinstance(v, (int, float)) and isinstance(p, (int, float)) else ''} | |")
    md += ["", f"Tickets by category: {', '.join(f'{c} {m}' for c, m in cats.most_common()) or 'none'}.", ""]
    if (n.get("paying_users") or 0) < 30:
        md += ["Under 30 paying users, so percentages move a lot on small counts.", ""]
    md += ["## What happened", *([f"- {s}" for s in trace("what_changed") + trace("causes")] or ["- No narrative traced to the numbers this run. Charlie writes it."]), "",
           "## What customers asked for", *([f"- {s} ({c})" for s, c in asks.most_common(5)] or ["- no feature requests logged"]), "",
           "## Risks", *([f"- {s}" for s in trace("risks")] or ["- none traced to the numbers"]), "", "## Actions", *[f"- {a['action']} (owner {a['owner']}, by {a['date']})" for a in acts]]
    k.write(ctx, f"support/qbr/{tag}.md", "\n".join(md))
    k.write(ctx, f"support/qbr/{tag}.json", {"quarter": tag, "start": start.isoformat(), "end": end.isoformat(), "numbers": n, "tickets_by_category": dict(cats), "missing": missing})
    health = (k.read(ctx, "support/health.json", {}) or {}).get("accounts", [])
    b2b = (ctx["idea"].get("business_model") or (k.read(ctx, "audit.json", {}) or {}).get("business_model")) == "b2b"
    pages = 0
    if b2b and (k.read(ctx, "support/config.json", {}) or {}).get("qbr_mode") == "account":
        renew = {r.get("user_id"): r.get("renewal_date") or r.get("next_renewal") or "" for r in pay}
        for a in [a for a in health if isinstance(a, dict) and a.get("user_id")][:20]:
            uid = a["user_id"]
            op = sum(1 for t in tix if t.get("user_id") == uid and t.get("status") == "open")
            step = {"green": "Keep as is and check for a plan limit.", "amber": "Check in with a short note.", "red": "Personal note from Charlie."}.get(a.get("band"), "No move yet.")
            k.write(ctx, f"support/qbr/{tag}-{util.slugify(uid)}.md", f"# {y} Q{q} account {uid}\n\n- Plan: {a.get('plan', '')}. Usage score {a.get('usage')}, health {a.get('score')} ({a.get('band')}).\n- Open issues: {op}.\n- Renewal date: {renew.get(uid) or 'not recorded'}.\n- Proposed next step: {step}\n\nDraft for Charlie. Nothing is sent to the account.")
            pages += 1
    return {"summary": f"QBR {y} Q{q} drafted from {len(n)} numbers, {len(missing)} missing source(s)" + (f", {pages} account pages" if pages else "") + ". Nothing sent.", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
