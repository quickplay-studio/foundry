"""Churn Prediction: GitHub implementation of departments/customer/success/churn-prediction/SKILL.md.

Rule-based risk points (summed, capped at 100), a back-test on accounts that already cancelled, a ranked
at-risk list and held win-back notes in support/outbox/. Nothing is sent, and notes never offer a discount.
"""
import csv
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import requests

from foundry import jobkit as k, util

POINTS = {"core": 30, "score": 25, "failed": 30, "cancel": 40, "trial": 30, "negative": 15, "unanswered": 15}
NOTE = {"ask-why": "I noticed you have not been in the app for a while. Is something not working for you? A one-line reply helps me fix it.",
        "help-email": "I saw something that may have gone wrong with your account. If you would like a hand, reply and I will help.",
        "win-back": "I am sorry to see you may be leaving. What would have made it work better for you? Any answer helps, and cancelling stays easy."}
OFFER = r"discount|% off|free month|coupon|voucher|cheaper|credit"


def d(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).date()
    except ValueError:
        return None


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


def load_events(ctx):
    days = defaultdict(lambda: defaultdict(Counter))
    got = hogql("SELECT distinct_id, toString(toDate(timestamp)), event, count() FROM events WHERE timestamp > now() - INTERVAL 90 DAY GROUP BY 1, 2, 3 LIMIT 100000")
    for uid, day, event, n in got or []:
        if d(day):
            days[str(uid)][d(day)][event] += int(n)
    if got is None:
        for r in rows(ctx, "support/data/events.csv"):
            if r.get("user_id") and d(r.get("date")):
                days[r["user_id"]][d(r["date"])][r.get("event", "event")] += int(float(r.get("count") or 1))
    return days


def risk(uid, asof, live, hist, days, core, pay, tix):
    """Risk points and plain reasons for one account as at a date. Payment rules need live data."""
    pts, why = 0, []
    mine = days.get(uid, {})
    prior = [x for x in mine if asof - timedelta(days=20) <= x <= asof - timedelta(days=7)]
    if days and len(prior) >= 3 and not any(mine[x][core] for x in mine if asof - timedelta(days=6) <= x <= asof):
        pts, why = pts + POINTS["core"], why + ["no core use for 7 days after steady use"]
    snaps = [s[uid] for dt_, s in hist if dt_ <= asof and uid in s]
    if len(snaps) >= 2 and snaps[-1] <= snaps[max(0, len(snaps) - 3)] - 20:
        pts, why = pts + POINTS["score"], why + ["health score fell 20 or more"]
    if live and pay.get(uid):
        p = pay[uid]
        for key, flag, text in (("failed", p["failed"], "failed payment not recovered"), ("cancel", p["cancel"], "set to cancel at period end"),
                                ("trial", p["trial"] and p["trial"] <= asof + timedelta(days=3) and not p["activated"], "trial ends within 3 days and not activated")):
            if flag:
                pts, why = pts + POINTS[key], why + [text]
    t = [x for x in tix.get(uid, []) if (d(x.get("received")) or asof) <= asof]
    if sum(1 for x in t if x.get("sentiment", 0) <= -1 and (d(x.get("received")) or asof) >= asof - timedelta(days=30)) >= 2:
        pts, why = pts + POINTS["negative"], why + ["two negative tickets in 30 days"]
    if live and any(x.get("status") == "open" and (d(x.get("received")) or asof) <= asof - timedelta(days=3) for x in t):
        pts, why = pts + POINTS["unanswered"], why + ["a ticket unanswered for over 72 hours"]
    return min(100, pts), why


def main(ctx):
    today = datetime.now(timezone.utc).date()
    health = k.read(ctx, "support/health.json", None)
    if not health:
        return {"skipped": "no health data yet: run health-scoring first"}
    accounts = {a["user_id"]: a for a in health.get("accounts", []) if isinstance(a, dict) and a.get("user_id")}
    hist = []
    folder = ctx["folder"] / "support" / "health-history"
    for p in sorted(folder.glob("*.json"))[-8:] if folder.exists() else []:
        if d(p.stem):
            hist.append((d(p.stem), {a["user_id"]: a.get("score", 0) for a in (util.read_json(p, {}) or {}).get("accounts", []) if isinstance(a, dict) and a.get("user_id")}))
    note_hist = "" if len(hist) > 1 else " Health history is one snapshot, so score-drop rules are idle."
    ev = k.read(ctx, "support/events.json", {}) or {}
    core, days = ev.get("core", "core_action"), load_events(ctx)
    pay, churned = {}, {}
    for r in rows(ctx, "support/data/payments.csv"):
        uid = r.get("user_id")
        if not uid:
            continue
        acc = accounts.get(uid, {})
        pay[uid] = {"plan": r.get("plan", ""), "failed": "failed-payment" in acc.get("flags", []) or (r.get("status") or "").lower() in ("past_due", "unpaid"),
                    "cancel": "cancel-at-period-end" in acc.get("flags", []) or str(r.get("cancel_at_period_end")).lower() in ("1", "true", "yes"),
                    "trial": d(r.get("trial_end")), "activated": "not-activated" not in acc.get("flags", []), "next": r.get("next_bill") or r.get("next_renewal") or r.get("renewal_date") or ""}
        gone = d(r.get("cancelled_on") or r.get("canceled_at") or r.get("cancelled_at"))
        if (r.get("status") or "").lower() in ("cancelled", "canceled") or gone:
            churned[uid] = gone or d(r.get("last_payment"))
    for uid, mine in days.items():  # a cancel event in the last 90 days also marks a churned account
        hit = [x for x, c in mine.items() if ev.get("cancel") and c[ev["cancel"]]]
        if hit and uid not in churned:
            churned[uid] = max(hit)
    tix = defaultdict(list)
    for t in (k.read(ctx, "support/tickets.json", {}) or {}).get("tickets", []):
        if isinstance(t, dict) and t.get("user_id"):
            tix[t["user_id"]].append(t)
    churned = {u: c for u, c in churned.items() if not c or (today - c).days <= 90}
    caught = sum(1 for u, c in churned.items() if c and risk(u, c - timedelta(days=14), False, hist, days, core, pay, tix)[0] >= 50)
    false_alarms = sum(1 for u in accounts if u not in churned and risk(u, today - timedelta(days=30), False, hist, days, core, pay, tix)[0] >= 50)
    n = len(accounts)
    bt = {"churned": len(churned), "caught": caught, "false_alarms": false_alarms,
          "note": ("too few to tune: default points kept" if len(churned) < 30 else "30 or more churned: points can be reviewed one step a week") + f". Based on {n} accounts" + (", a prompt for a look, not a forecast." if n < 30 else ".")}
    scored = sorted(((risk(u, today, True, hist, days, core, pay, tix) + (u,) for u in accounts if u not in churned)), key=lambda x: -x[0])
    cfg = k.read(ctx, "support/config.json", {}) or {}
    at_risk = []
    for score, why, uid in scored:
        if score < 50:
            continue
        p, acc = pay.get(uid, {}), accounts[uid]
        urgent = any(t.get("status") == "open" and t.get("priority") in ("P1", "P2") for t in tix.get(uid, []))
        action = "none" if urgent else "win-back" if p.get("cancel") and acc.get("score", 0) >= 60 else "help-email" if p.get("failed") or "trial" in " ".join(why) else "ask-why"
        at_risk.append({"user_id": uid, "risk": score, "reasons": why, "plan": p.get("plan") or acc.get("plan", ""), "next_bill": p.get("next", ""), "suggested_action": action, "escalate": urgent})
    top = [a for a in at_risk if a["suggested_action"] in NOTE][:5]
    ans = k.ask('Write one short note per user in plain UK English, no exclamation marks, 60 words or fewer. Ask one question or offer help. Never offer a discount or credit and never make cancelling harder. '
                'Return JSON only: {"notes": [{"user_id": "<id>", "body": "..."}]}\nUSERS: ' + str([(a["user_id"], a["suggested_action"], a["reasons"]) for a in top])) if top else None
    made = {str(x.get("user_id")): str(x.get("body", "")) for x in (ans.get("notes") if isinstance(ans, dict) and isinstance(ans.get("notes"), list) else []) if isinstance(x, dict)}
    for a in top:
        body = made.get(a["user_id"], "")
        body = body.replace(chr(33), ".") if body and not re.search(OFFER, body.lower()) and len(body.split()) <= 70 else NOTE[a["suggested_action"]]
        k.write(ctx, f"support/outbox/winback-{util.slugify(a['user_id'])}.md", f"send: hold\nuser_id: {a['user_id']}\naction: {a['suggested_action']}\n\nHello,\n\n{body}\n\n{cfg.get('signoff') or 'The team'}")
    k.write(ctx, "support/churn.json", {"updated": util.now(), "horizon_days": 30, "rules_version": 1, "backtest": bt, "at_risk": at_risk})
    md = [f"# Churn risk {util.today()}", "", f"{len(at_risk)} of {n} accounts at risk (50 or more).{note_hist}", "", "## Top 10",
          *([f"- {a['user_id']}: {a['risk']} ({a['suggested_action']}) {'; '.join(a['reasons'])}" for a in at_risk[:10]] or ["- none"]), "",
          f"Back-test: {bt['churned']} churned, {bt['caught']} caught 14 days out, {bt['false_alarms']} false alarms. {bt['note']}"]
    k.write(ctx, "support/churn.md", "\n".join(md))
    return {"summary": f"Churn: {len(at_risk)} of {n} accounts at risk, {len(top)} held notes. Back-test {caught} of {len(churned)} churned caught.{note_hist}", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
