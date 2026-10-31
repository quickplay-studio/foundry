"""Health Scoring: GitHub implementation of departments/customer/success/health-scoring/SKILL.md.

Scores every account on usage, engagement and sentiment with plain arithmetic (a model never sets
a number). Events come from PostHog (read only, HogQL) or support/data/events.csv, payments from
support/data/payments.csv. Writes health.json, health.md and a dated snapshot. user_id only.
"""
import csv
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import requests

from foundry import jobkit as k, util

WEIGHTS = {"usage": 50, "engagement": 30, "sentiment": 20}


def d(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def rows(ctx, rel):
    p = ctx["folder"] / rel
    return [{str(a).lower().strip(): b for a, b in r.items()} for r in csv.DictReader(p.open(encoding="utf-8-sig"))] if p.exists() else []


def hogql(query):
    """Rows from the PostHog query endpoint, or None when the keys are missing or the call fails."""
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


def load_events(ctx):
    days, note = defaultdict(lambda: defaultdict(Counter)), ""
    got = hogql("SELECT distinct_id, toString(toDate(timestamp)), event, count() FROM events WHERE timestamp > now() - INTERVAL 28 DAY GROUP BY 1, 2, 3 LIMIT 100000")
    if got is not None:
        for uid, day, event, n in got:
            if d(day):
                days[str(uid)][d(day)][event] += int(n)
    else:
        note = "PostHog keys missing or the call failed" if k.secret("POSTHOG_API_KEY") else "PostHog keys not set"
        for r in rows(ctx, "support/data/events.csv"):
            if r.get("user_id") and d(r.get("date")):
                days[r["user_id"]][d(r["date"])][r.get("event", "event")] += int(float(r.get("count") or 1))
    return days, got is not None or bool(days), note


def truthy(v):
    return str(v).strip().lower() in ("1", "true", "yes", "y")


def failed(r, today):
    """A failed payment in the last 30 days, or a past-due status."""
    last = d(r.get("last_failed"))
    count = float(re.sub(r"[^\d.]", "", r.get("failed_payments") or "") or 0)
    return bool((last and (today - last).days <= 30) or (not last and count > 0) or (r.get("status") or "").lower() in ("past_due", "unpaid"))


def main(ctx):
    today, folder = datetime.now(timezone.utc).date(), ctx["folder"]
    ev = k.read(ctx, "support/events.json", None)
    proposed = ev is None
    if proposed:
        ans = k.ask('Name two product analytics events for this app in snake_case: the first sign of activation and the core repeated action. Return JSON only: {"activation": "...", "core": "..."}\n'
                    f"MVP: {ctx['idea'].get('mvp')}")
        ok = lambda v, dflt: v if isinstance(v, str) and re.fullmatch(r"[a-z][a-z0-9_]{2,40}", v) else dflt
        ans = ans if isinstance(ans, dict) else {}
        ev = {"activation": ok(ans.get("activation"), "activated"), "core": ok(ans.get("core"), "core_action"), "paid": "subscription_started", "cancel": "subscription_cancelled",
              "expected_active_days_per_14": 6, "weights": WEIGHTS, "payments": "support/data/payments.csv", "proposed": True}
        k.write(ctx, "support/events.json", ev)
    w = {**WEIGHTS, **(ev.get("weights") or {})}
    days, have_events, note = load_events(ctx)
    pay = {}
    for r in rows(ctx, "support/data/payments.csv"):
        if r.get("user_id"):
            pay[r["user_id"]] = {"plan": r.get("plan", ""), "start": d(r.get("start_date")), "last": d(r.get("last_payment")), "status": (r.get("status") or "").lower(),
                                 "failed": failed(r, today), "cancel": truthy(r.get("cancel_at_period_end"))}
    tk = defaultdict(list)
    for t in (k.read(ctx, "support/tickets.json", {}) or {}).get("tickets", []):
        if isinstance(t, dict) and t.get("user_id") and (d(t.get("received")) or today) >= today - timedelta(days=60):
            tk[t["user_id"]].append(t)
    prev, history = {}, sorted((folder / "support" / "health-history").glob("*.json")) if (folder / "support" / "health-history").exists() else []
    for p in history:
        if p.stem < today.isoformat():
            prev = {a.get("user_id"): a.get("score") for a in (util.read_json(p, {}) or {}).get("accounts", [])}
    wk = [[today - timedelta(days=i) for i in range(a, a + 7)] for a in (0, 7, 14, 21)]
    accounts, summary = [], {"green": 0, "amber": 0, "red": 0, "new": 0, "dormant": 0}
    for uid in sorted(set(days) | set(pay) | set(tk)):
        mine, p, flags = days.get(uid, {}), pay.get(uid, {}), []
        recent_pay = bool(p) and (p.get("status") in ("active", "trialing", "past_due") or (p.get("last") and (today - p["last"]).days <= 90) or (p.get("start") and (today - p["start"]).days <= 90))
        if not mine and not recent_pay:
            summary["dormant"] += 1
            continue
        a14, core = [x for x in wk[0] + wk[1] if x in mine], ev["core"]
        n_now, n_before = sum(mine[x][core] for x in wk[0] + wk[1] if x in mine), sum(mine[x][core] for x in wk[2] + wk[3] if x in mine)
        usage = max(0, min(100, min(100, round(100 * len(a14) / max(1, ev.get("expected_active_days_per_14") or 6))) + max(-10, min(10, round(10 * (n_now - n_before) / max(n_before, 1))))))
        activated = any(ev["activation"] in c for c in mine.values())
        feats = {e for x in wk[0] + wk[1] if x in mine for e in mine[x]}
        engage = 40 * activated + 30 * (any(x in mine for x in wk[0]) and any(x in mine for x in wk[1])) + 30 * (len(feats) >= 2)
        sent = 70 + sum(-15 * (t.get("sentiment", 0) <= -1) - 25 * (t.get("route") == "escalate") + 10 * (t.get("category") == "praise") for t in tk.get(uid, []))
        sent = max(0, min(100, sent))
        score = round((usage * w["usage"] + engage * w["engagement"] + sent * w["sentiment"]) / max(1, sum(w.values())))
        if p.get("failed"):
            score, flags = min(score, 60), flags + ["failed-payment"]
        if p.get("cancel"):
            score, flags = min(score, 40), flags + ["cancel-at-period-end"]
        flags += [f for ok_, f in ((not a14, "no-activity-14d"), (n_now < n_before, "core-usage-falling"), (not activated, "not-activated"), (sent < 70, "negative-ticket")) if ok_]
        first = min([x for x in list(mine) + [p.get("start")] if x] or [today])
        tenure = (today - first).days
        band = "new" if tenure < 14 and not activated else "green" if score >= 70 else "amber" if score >= 40 else "red"
        summary[band] += 1
        accounts.append({"user_id": uid, "plan": p.get("plan", ""), "tenure_days": tenure, "score": score, "band": band, "trend": score - prev[uid] if prev.get(uid) is not None else 0,
                         "usage": usage, "engagement": engage, "sentiment": sent, "flags": flags})
    partial = not have_events
    out = {"updated": util.now(), "weights": w, "summary": summary, "accounts": accounts, "partial": partial}
    low = sorted(accounts, key=lambda a: a["score"])[:20]
    ans = k.ask('Summarise in two plain UK English sentences what the flags below say. Do not state any new number. Return JSON only: {"note": "..."}\n' + str([(a["band"], a["flags"]) for a in low])) if low else None
    md = [f"# Health {util.today()}", "", " ".join(f"{b}: {n}." for b, n in summary.items()), ""]
    if len(accounts) < 30:
        md += [f"Low data: {len(accounts)} accounts, so the bands are rough.", ""]
    if partial:
        md += [f"Partial: no event source this run ({note}). Add PostHog keys or drop support/data/events.csv (user_id, date, event).", ""]
    if proposed:
        md += ["support/events.json was proposed from the mvp line. Charlie names the real activation and core events and approves the weights.", ""]
    if isinstance(ans, dict) and isinstance(ans.get("note"), str):
        md += [ans["note"][:400], ""]
    md += ["## Lowest scores", *([f"- {a['user_id']}: {a['score']} ({a['band']}) {', '.join(a['flags'])}" for a in low] or ["- no accounts yet"])]
    k.write(ctx, "support/health.json", out)
    k.write(ctx, "support/health.md", "\n".join(md))
    k.write(ctx, f"support/health-history/{util.today()}.json", out)
    return {"summary": f"Health: {summary['green']} green, {summary['amber']} amber, {summary['red']} red, {summary['new']} new, {summary['dormant']} dormant" + ("; partial, no event source" if partial else "")
            + ("; events.json proposed for Charlie" if proposed else ""), "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
