"""Renewals and Expansion: GitHub implementation of departments/customer/success/renewals-and-expansion/SKILL.md.

Lists accounts in the renewal window, classes them (safe, at-risk, upgrade-candidate), works out revenue
at stake and recommends one move each. Notes are drafts marked not sent. Never recommends a discount, never
sends a reminder or an offer: Charlie reads renewals.md. user_id only.
"""
import csv
import re
from datetime import datetime, timedelta, timezone

import requests

from foundry import jobkit as k, util

NOTE = {"personal note from Charlie": "I wanted to check in myself. Is the app doing what you hoped? If not, tell me what is missing.",
        "helpful nudge": "A quick check that everything is working for you. If anything is in the way, reply and I will help.",
        "upgrade mention": "You have been getting a lot out of it. If you are hitting a limit, a higher plan may suit you better. No pressure, and I am happy to answer questions."}
OFFER = r"discount|% off|free month|coupon|voucher|cheaper|credit"


def d(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def num(v):
    try:
        return float(re.sub(r"[^\d.]", "", str(v)) or "x")
    except ValueError:
        return None


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


def main(ctx):
    today, folder = datetime.now(timezone.utc).date(), ctx["folder"]
    health = {a["user_id"]: a for a in (k.read(ctx, "support/health.json", {}) or {}).get("accounts", []) if isinstance(a, dict) and a.get("user_id")}
    churn = {a["user_id"]: a for a in (k.read(ctx, "support/churn.json", {}) or {}).get("at_risk", []) if isinstance(a, dict) and a.get("user_id")}
    p = folder / "support" / "data" / "payments.csv"
    pay = {}
    for r in (csv.DictReader(p.open(encoding="utf-8-sig")) if p.exists() else []):
        low = {str(a).lower().strip(): b for a, b in r.items()}
        if low.get("user_id"):
            pay[low["user_id"]] = low
    if not health and not pay:
        return {"skipped": "no health or payment data yet"}
    ev = k.read(ctx, "support/events.json", {}) or {}
    use = {}
    names = [n for n in ("limit_hit", ev.get("paid_feature")) if n and re.fullmatch(r"\w{2,40}", str(n))]
    got = hogql("SELECT distinct_id, " + ", ".join(f"countIf(event = '{n}')" for n in names) + " FROM events WHERE timestamp > now() - INTERVAL 14 DAY GROUP BY 1") if names else None
    for row in got or []:
        use[str(row[0])] = {"limit": int(row[1]), "paid": int(row[2]) if len(row) > 2 else 0}
    open_p = {t["user_id"] for t in (k.read(ctx, "support/tickets.json", {}) or {}).get("tickets", []) if isinstance(t, dict) and t.get("status") == "open" and t.get("priority") in ("P1", "P2")}
    open_any = {t["user_id"] for t in (k.read(ctx, "support/tickets.json", {}) or {}).get("tickets", []) if isinstance(t, dict) and t.get("status") == "open"}
    money = f"{ctx['idea'].get('money', '')} {ctx['brain']}".lower()
    multi = len(re.findall(r"£\s?\d|\$\s?\d|\d+\s?gbp", ctx["idea"].get("money", "").lower())) >= 2 or bool(re.search(r"\b(pro|premium|plus|team|business|add-on|tier)\b", ctx["idea"].get("money", "").lower()))
    accounts, stake, risk_value = [], 0.0, 0.0
    for uid in sorted(set(health) | set(pay)):
        h, r, c = health.get(uid, {}), pay.get(uid, {}), churn.get(uid, {})
        interval = (r.get("billing_interval") or r.get("interval") or ("monthly" if r else "")).lower()
        renewal, trial = d(r.get("next_renewal") or r.get("renewal_date") or r.get("next_bill")), d(r.get("trial_end"))
        band = h.get("band", "unknown")
        in_win = [x for x, ok in (("annual renewal within 30 days", interval in ("annual", "yearly", "year") and renewal and 0 <= (renewal - today).days <= 30),
                                  (f"{band} monthly account", interval.startswith("month") and band in ("amber", "red")), ("trial ends within 7 days", trial and 0 <= (trial - today).days <= 7)) if ok]
        busy = uid in open_p or c.get("risk", 0) >= 50 or band in ("amber", "red")
        limit = bool(r.get("hit_limit") and str(r["hit_limit"]).lower() in ("1", "true", "yes")) or use.get(uid, {}).get("limit", 0) > 0 or (num(r.get("paid_feature_uses_14d")) or 0) >= 3 or use.get(uid, {}).get("paid", 0) >= 3
        upgrade = multi and band == "green" and h.get("tenure_days", 0) >= 30 and uid not in open_any and limit
        if not in_win and not upgrade:
            continue
        cls = "at-risk" if busy else "upgrade-candidate" if upgrade else "safe"
        why = in_win + (["open P1 or P2 ticket"] if uid in open_p else []) + ([f"churn risk {c['risk']}"] if c.get("risk", 0) >= 50 else []) + (["hitting a plan limit or using a paid feature"] if upgrade else [])
        move = ("personal note from Charlie" if band == "red" or c.get("risk", 0) >= 70 or uid in open_p else "helpful nudge") if cls == "at-risk" else "upgrade mention" if cls == "upgrade-candidate" else "helpful nudge" if "trial ends within 7 days" in in_win else "leave alone"
        value = num(r.get("price") or r.get("amount"))
        stake += (value or 0) if in_win and cls not in ("upgrade-candidate",) else 0
        risk_value += (value or 0) if cls == "at-risk" else 0
        accounts.append({"user_id": uid, "class": cls, "plan": r.get("plan") or h.get("plan", ""), "renewal_date": str(renewal or trial or ""), "value": value, "reasons": why or [cls], "move": move})
    top = sorted((a for a in accounts if a["move"] in NOTE), key=lambda a: (-(a["value"] or 0), a["user_id"]))[:3]
    ans = k.ask('Write one short note per account in plain UK English, no exclamation marks, 60 words or fewer. Ask one question or offer help. Never offer a discount, credit or free time. '
                'Return JSON only: {"notes": [{"user_id": "<id>", "body": "..."}]}\nACCOUNTS: ' + str([(a["user_id"], a["move"], a["reasons"]) for a in top])) if top else None
    made = {str(x.get("user_id")): str(x.get("body", "")) for x in (ans.get("notes") if isinstance(ans, dict) and isinstance(ans.get("notes"), list) else []) if isinstance(x, dict)}
    notes = []
    for a in top:
        body = made.get(a["user_id"], "").replace(chr(33), ".")
        notes.append((a, body if body and not re.search(OFFER, body.lower()) and len(body.split()) <= 70 else NOTE[a["move"]]))
    counts = {c: sum(1 for a in accounts if a["class"] == c) for c in ("safe", "at-risk", "upgrade-candidate")}
    md = [f"# Renewals {util.today()}", "", "Window: 30 days for annual plans, amber or red monthly plans, trials ending in 7 days. The ask is Charlie's. Nothing is sent.", ""]
    md += [f"Safe {counts['safe']}, at-risk {counts['at-risk']}, upgrade-candidate {counts['upgrade-candidate']}. Revenue at stake in the window: {round(stake, 2) if stake else 'blank, no price known'}. Gross value of at-risk accounts: {round(risk_value, 2) if risk_value else 'blank'}.", ""]
    if not multi:
        md += ["Single plan, no expansion route.", ""]
    if not pay:
        md += ["Payments could not be read (no support/data/payments.csv), so this brief comes from health alone.", ""]
    md += ["## Accounts", *([f"- {a['user_id']} ({a['class']}, {a['plan'] or 'no plan'}): {'; '.join(a['reasons'])}. Move: {a['move']}." for a in accounts[:10]] or ["- Nothing in the window. That is correct for a small consumer app."]), ""]
    if any(a["class"] == "at-risk" and (churn.get(a["user_id"], {}).get("risk", 0) >= 70) for a in accounts):
        md += ["Question for Charlie: does any at-risk account need a discount? Not recommended by default; your call only.", ""]
    if any(str(a["renewal_date"]) and "annual" in " ".join(a["reasons"]) for a in accounts):
        md += ["Before the first annual plan renews, ask Legal consumer-law-check what notice duties apply to auto-renewal. Not legal advice.", ""]
    md += ["## Drafted notes (draft, not sent)", *([f"### {a['user_id']}\n\nHello,\n\n{b}\n" for a, b in notes] or ["none"])]
    k.write(ctx, "support/renewals.md", "\n".join(md))
    k.write(ctx, "support/renewals.json", {"updated": util.now(), "window_days": 30, "accounts": accounts})
    return {"summary": f"Renewals: {len(accounts)} accounts listed ({counts['at-risk']} at-risk, {counts['upgrade-candidate']} upgrade), {len(notes)} notes drafted, none sent.", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
