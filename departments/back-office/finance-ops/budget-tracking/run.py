"""Budget Tracking: GitHub implementation of departments/back-office/finance-ops/budget-tracking/SKILL.md.

No model. Totals spend and revenue, flags the ad budget, applies the kill rule and writes the weekly line.
It never moves money or touches an ad account.
"""
import csv
import datetime as dt
import re
from decimal import Decimal, ROUND_HALF_UP

from foundry import jobkit as k
from foundry import util

OFF = "../../office/"


def money(x):
    return float(Decimal(str(x)).quantize(Decimal("0.01"), ROUND_HALF_UP))


def num(text):
    try:
        return float(re.sub(r"[^0-9.\-]", "", str(text)))
    except ValueError:
        return None


def day(text):
    try:
        return dt.date.fromisoformat(str(text)[:10])
    except ValueError:
        return None


def table(text):
    reader = csv.DictReader((text or "").splitlines())
    rows = [{h.strip().lower(): (v or "").strip() for h, v in r.items() if isinstance(h, str)} for r in reader]
    return [h.strip().lower() for h in reader.fieldnames or []], rows


def conv(amount, frm, to, rates):
    if amount is None or frm == to:
        return amount
    a, b = rates.get(frm), rates.get(to)
    return amount * a / b if a and b else None


def signed(r):
    """Paid rows count up; a refund row counts down whatever sign it carries. Pending and failed never count."""
    a = num(r.get("amount_minor")) or 0
    return -abs(a) if r.get("status") == "refunded" else a if r.get("status") == "paid" else 0


def main(ctx):
    board = k.read(ctx, "board.json", None) or ctx.get("board") or {}
    budget = k.read(ctx, "budget.json", None) or ctx.get("budget") or {}
    if board.get("verdict") in ("park", "kill", "blocked"):
        return {"skipped": f"verdict is {board['verdict']}, the agents have stopped or Charlie must decide"}
    if (board.get("gates") or {}).get("launch") == "open":
        return {"skipped": "nothing has launched yet (launch gate open)"}
    today = dt.date.fromisoformat(util.today())
    mon = today - dt.timedelta(days=today.weekday() + 7)  # the last complete ISO week, so a run on any weekday reports a whole week
    sun = mon + dt.timedelta(days=6)
    iso = mon.isocalendar()
    label = f"{iso[0]}-W{iso[1]:02d}"
    cur = budget.get("currency") or "GBP"
    rates = {"GBP": 1.0, **(k.read(ctx, OFF + "finance/rates.json", {}) or {}).get("rates", {})}
    notes = []
    lines = [dict(x) for x in budget.get("lines", []) if isinstance(x, dict)]

    # 2. ad lines: one per platform per day, a re-export replaces
    fin = ctx["folder"] / "finance"
    for path in sorted(fin.glob("ads-*.csv")) if fin.is_dir() else []:
        platform = re.split(r"[-_.]", path.stem[4:])[0] or "ads"
        heads, rows = table(k.read(ctx, f"finance/{path.name}", ""))
        dcol = next((h for h in heads if h in ("date", "day")), None)
        scol = next((h for h in heads if h in ("spend", "cost", "amount spent")), None)
        if not dcol or not scol:
            notes.append(f"{path.name} skipped: no date and spend headers")
            continue
        per = {}
        for r in rows:
            d, a = day(r[dcol]), num(r[scol])
            if d and a is not None:
                per[d.isoformat()] = per.get(d.isoformat(), 0) + a
        for d, a in per.items():
            note = f"ads:{platform}:{d}"
            lines = [x for x in lines if not x.get("note") == note] + [{"date": d, "kind": "ad", "amount": money(a), "note": note}]

    # 2. other lines, added only when the key is new
    def key(x):
        return f"{x.get('date')}|{x.get('kind')}|{money(num(x.get('amount')) or 0):.2f}|{x.get('note')}"

    seen, dropped = {key(x) for x in lines}, 0
    expenses = k.read(ctx, "finance/expenses.json", [])
    for r in expenses if isinstance(expenses, list) else []:
        if not isinstance(r, dict) or r.get("kind") == "ad" or not day(r.get("date")):
            continue
        amt = conv(num(r.get("amount")), r.get("currency") or cur, cur, rates)
        if amt is None:
            dropped += 1
            continue
        line = {"date": str(r["date"])[:10], "kind": r.get("kind") if r.get("kind") in ("tool", "domain", "fee") else "other",
                "amount": money(amt), "note": str(r.get("merchant") or r.get("key") or "expense")[:80]}
        if key(line) not in seen:
            seen.add(key(line))
            lines.append(line)
    if dropped:
        notes.append(f"{dropped} expense rows left out: no rate to {cur}")
    lines.sort(key=lambda x: (str(x.get("date")), str(x.get("note"))))

    # 3. totals and revenue
    spent = sum(num(x.get("amount")) or 0 for x in lines)
    ad_spent = sum(num(x.get("amount")) or 0 for x in lines if x.get("kind") == "ad")
    pay = k.read(ctx, "finance/payments.json", None)
    pay = pay if isinstance(pay, dict) else {}
    rev = rev_week = 0.0
    for r in pay.get("rows", []):
        v = conv(signed(r) / 100, r.get("currency") or cur, cur, rates) if isinstance(r, dict) else 0
        if v is None:
            notes.append(f"revenue in {r.get('currency')} left out: no rate")
            continue
        rev += v
        if day(r.get("date")) and mon <= day(r.get("date")) <= sun:
            rev_week += v
    week_spent = sum(num(x.get("amount")) or 0 for x in lines if day(x.get("date")) and mon <= day(x.get("date")) <= sun)

    # 5. sign-ups
    raw = k.read(ctx, "finance/signups.csv", None)
    heads, srows = table(raw) if raw is not None else ([], [])
    daily = [(day(r.get("date")), num(r.get("count"))) for r in srows]
    daily = [(d, c) for d, c in daily if d and c is not None]
    known = raw is not None and "count" in heads
    w = [sum(c for d, c in daily if mon - dt.timedelta(days=7 * i) <= d <= sun - dt.timedelta(days=7 * i)) for i in range(4)]
    cum = sum(c for d, c in daily)
    cpa = money(ad_spent / cum) if cum > 0 else None
    trend_up, no_trend = w[0] + w[1] > w[2] + w[3], sum(w) == 0 or w[0] + w[1] <= w[2] + w[3]

    # 4. ad budget flags
    ab, flag = num(budget.get("ad_budget")) or 0, "ok"
    if ab <= 0:
        notes.insert(0, "no approved budget")
    else:
        recent = sum(num(x.get("amount")) or 0 for x in lines if x.get("kind") == "ad" and day(x.get("date")) and sun - dt.timedelta(days=13) <= day(x.get("date")) <= sun) / 2
        if ad_spent >= ab:
            notes.insert(0, "red: ad budget used up, Charlie pauses ads and decides on more")
            flag = "caution"
        elif ad_spent >= 0.8 * ab:
            notes.insert(0, f"amber: {round(100 * ad_spent / ab)}% of ad budget used")
            flag = "caution"
        elif recent > 0 and ab - ad_spent <= 2 * recent:
            notes.insert(0, "amber: last two weeks' pace would exhaust the ad budget within two weeks")
            flag = "caution"

    # 6. ad rule against the ceiling in the ad brief
    brief = k.read(ctx, "launch/ad-brief.md", "") or ""
    m = re.search(r"target cost per sign-?up[:*\s]*£\s*([0-9]+(?:\.[0-9]+)?)", brief, re.I)
    if ad_spent > 50 and known and m and (cpa is None or cpa > float(m.group(1))):
        notes.append(f"ads_stop: cost per sign-up above £{m.group(1)} after £50 spent")
        flag = "caution"
    elif ad_spent > 50 and not m:
        notes.append("ad brief ceiling not found, ads_stop check skipped")

    # 7 and 8. verdict, never on stale or missing data
    weekly = [x for x in board.get("weekly", []) if isinstance(x, dict) and not x.get("week") == label]
    upd = day(pay.get("updated"))
    stripe_ever = bool(list(fin.glob("stripe-*.csv"))) if fin.is_dir() else False
    fresh = (upd is not None and (today - upd).days <= 7) or not stripe_ever
    verdict = "continue"
    if not known:
        notes.append("sign-up data missing")
    elif ab > 0 and ad_spent >= ab and rev <= 0 and no_trend and len(weekly) + 1 >= 4:
        if fresh:
            verdict, flag = "park", "caution"
        else:
            notes.append("payments data stale, not parked")
    elif spent > 0 and rev >= spent and trend_up:
        verdict = "scale"
    line = {"week": label, "spent": money(week_spent), "revenue": money(rev_week), "sign_ups": int(w[0]) if known else None,
            "cost_per_sign_up": cpa, "verdict": verdict, "note": "; ".join(notes)}

    # 9. write budget.json, then board.json
    budget = dict(budget, currency=cur, ad_budget=budget.get("ad_budget", 0), spent=money(spent), revenue=money(rev), lines=lines, updated=util.today())
    k.write(ctx, "budget.json", budget)
    board = dict(board, weekly=weekly + [line], verdict=verdict)
    if verdict == "park":
        board["gates"] = dict(board.get("gates") or {}, run="parked")
    k.write(ctx, "board.json", board)
    return {"summary": f"{label}: spent {cur} {money(spent)}, revenue {money(rev)}, verdict {verdict}. {line['note']}", "flag": flag}


if __name__ == "__main__":
    k.run(main)
