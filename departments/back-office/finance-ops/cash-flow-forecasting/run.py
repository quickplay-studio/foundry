"""Cash-Flow Forecasting: GitHub implementation of departments/back-office/finance-ops/cash-flow-forecasting/SKILL.md.

Thirteen weekly buckets, three scenarios, in integer pence. The model may only phrase the commentary;
a fixed template is the fallback. Nothing unapproved is forecast and no tax is worked out.
"""
import calendar
import datetime as dt
import re
from decimal import Decimal, ROUND_HALF_UP

from foundry import jobkit as k
from foundry import util

OFF = "../../office/"
WEEKS = 13


def tidy(text):
    """Model prose: no dashes, no exclamation marks."""
    return re.sub("[" + chr(0x2013) + chr(0x2014) + "]", ", ", str(text)).replace(chr(33), ".").strip()


def pence(x):
    try:
        return int((Decimal(str(x)) * 100).quantize(Decimal(1), ROUND_HALF_UP))
    except Exception:  # noqa: BLE001
        return 0


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def day(text):
    try:
        return dt.date.fromisoformat(str(text)[:10])
    except ValueError:
        return None


def jread(ctx, rel, default):
    try:
        data = k.read(ctx, rel, default)
    except ValueError:
        return default
    return data if isinstance(data, type(default)) else default


def rj(path, default):
    """A JSON file on disk, or the default when missing, unreadable or the wrong shape."""
    try:
        data = util.read_json(path, default)
    except ValueError:
        return default
    if isinstance(default, dict):
        return data if isinstance(data, dict) else default
    return data if isinstance(data, (list, dict)) else default


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    return dt.date(d.year + y, m + 1, min(d.day, calendar.monthrange(d.year + y, m + 1)[1]))


def occurs(first, every, start, end):
    """Dates in [start, end) on which a commitment falls."""
    out, i, d = [], 0, first
    while d < end and i < 400:
        if d >= start:
            out.append(d)
        i += 1
        d = first + dt.timedelta(days=7 * i) if every == "week" else add_months(first, i) if every == "month" else add_months(first, 12 * i) if every == "year" else end
    return out


def gbp(x, cur, rates):
    v = num(x)
    r = 1.0 if cur == "GBP" else rates.get(cur)
    return None if v is None or not r else v * r


def phrase(facts, fallback):
    ans = k.ask('Write the commentary for a cash forecast in at most five plain sentences, facts only, using only the numbers given. '
                'Return JSON only: {"commentary": "<text>"}\n\nFACTS\n' + facts)
    text = str(ans.get("commentary", "")) if isinstance(ans, dict) else ""
    text = tidy(text)
    nums = set(re.findall(r"\d+(?:\.\d+)?", facts))
    ok = text and len(re.findall(r"[.?]", text)) <= 5 and set(re.findall(r"\d+(?:\.\d+)?", text)) <= nums
    return text if ok else fallback


def main(ctx):
    today = dt.date.fromisoformat(util.today())
    rates = (jread(ctx, OFF + "finance/rates.json", {}).get("rates") or {})
    notes, asks = [], []
    cash = jread(ctx, OFF + "finance/cash.json", {})
    asm = {"low_factor": 0.5, "high_factor": 1.25, "buffer": 0, "tax_set_aside_rate": 0, **jread(ctx, OFF + "finance/assumptions.json", {})}
    as_of, bal = day(cash.get("as_of")), gbp(cash.get("cash"), cash.get("currency") or "GBP", rates)
    anchored = as_of is not None and (today - as_of).days <= 14 and bal is not None
    if not anchored:
        asks.append("Please type the current cash balance and date into office/finance/cash.json (one figure, never an account number).")
    base = as_of if anchored else today
    start = base + dt.timedelta(days=7 - base.weekday())
    starts = [start + dt.timedelta(days=7 * i) for i in range(WEEKS)]
    end = starts[-1] + dt.timedelta(days=7)
    out, inc, names = [0] * WEEKS, [0] * WEEKS, {}

    def spend(i, name, p):
        out[i] += p
        names[name] = names.get(name, 0) + p

    # cash out: commitments, then remaining approved ad budget at the recent pace
    for c in jread(ctx, OFF + "finance/commitments.json", []):
        if not isinstance(c, dict) or not day(c.get("first")):
            continue
        amt = gbp(c.get("amount"), c.get("currency") or "GBP", rates)
        if amt is None:
            notes.append(f"commitment {c.get('name')} left out: no rate for {c.get('currency')}")
            continue
        for d in occurs(day(c["first"]), str(c.get("every")), start, end):
            spend((d - start).days // 7, str(c.get("name") or "commitment"), pence(amt))
    office = ctx["folder"].parent.parent / "office"
    folders = [p for p in sorted(ctx["folder"].parent.iterdir()) if p.is_dir()] if ctx["folder"].parent.is_dir() else []
    revenue = {}
    for f in sorted((office / "finance" / "revenue").glob("*.json")):
        for v in rj(f, {}).get("ventures", []):
            if isinstance(v, dict) and num(v.get("gbp")) is not None:
                revenue.setdefault(v.get("slug"), []).append((f.stem, float(v["gbp"])))
    for f in folders:
        slug, budget, board = f.name, rj(f / "budget.json", {}), rj(f / "board.json", {})
        lines = [x for x in (budget.get("lines") or []) if isinstance(x, dict) and x.get("kind") == "ad"]
        left = (gbp(budget.get("ad_budget"), budget.get("currency") or "GBP", rates) or 0) - sum(num(x.get("amount")) or 0 for x in lines)
        pace = sum(num(x.get("amount")) or 0 for x in lines if day(x.get("date")) and (today - day(x.get("date"))).days <= 28) / 4
        for i in range(WEEKS):
            take = min(pace, max(left, 0))
            left -= take
            if take > 0:
                spend(i, f"ad spend: {slug}", pence(take))
        # cash in, base case: trailing three months spread evenly, plus due invoices at due date plus average days late
        if not board.get("verdict") == "park":
            last3 = [g for _, g in sorted(revenue.get(slug, []))[-3:]]
            for i in range(WEEKS):
                inc[i] += pence(sum(last3) / len(last3) * 12 / 52) if last3 else 0
        reg = rj(f / "finance" / "invoices.json", [])
        reg = reg.get("rows", []) if isinstance(reg, dict) else reg
        pays = rj(f / "finance" / "payments.json", {})
        states = {r.get("number"): r for r in pays.get("invoices", []) if isinstance(r, dict)}
        late = [num(r.get("days_late")) or 0 for r in states.values() if (num(r.get("days_late")) or 0) > 0]
        avg_late = round(sum(late) / len(late)) if late else 0
        for r in reg if isinstance(reg, list) else []:
            if isinstance(r, dict) and states.get(r.get("number"), {}).get("state") in ("due", "late", "part-paid") and day(r.get("due")):
                when = day(r["due"]) + dt.timedelta(days=avg_late)
                amt = gbp((num(r.get("total_minor")) or 0) / 100, r.get("currency") or "GBP", rates)
                if amt is not None and when < end:
                    inc[max((when - start).days // 7, 0)] += pence(amt)

    # scenarios: costs identical, revenue scaled
    rate = num(asm.get("tax_set_aside_rate")) or 0
    buf = pence(asm.get("buffer") or 0)
    scen, weeks = {}, [{"start": s.isoformat(), "in": 0, "out": 0} for s in starts]
    for name, factor in (("base", 1.0), ("low", num(asm.get("low_factor")) or 0.5), ("high", num(asm.get("high_factor")) or 1.25)):
        bal_p, closes = pence(bal) if anchored else 0, []
        for i in range(WEEKS):
            cash_in = round(inc[i] * factor)
            bal_p += cash_in - out[i] - (round(cash_in * rate) if rate > 0 and cash_in > 0 else 0)
            closes.append(bal_p)
            weeks[i][f"close_{name}"] = bal_p / 100
            if name == "base":
                weeks[i].update({"in": cash_in / 100, "out": out[i] / 100})
        neg = next((i for i, c in enumerate(closes) if c < 0), None)
        low = next((i for i, c in enumerate(closes) if c < buf), None)
        scen[name] = {"runway": None if not anchored else ">13" if neg is None else neg,
                      "below": None if not anchored else "none in 13 weeks" if low is None else {"week": low + 1, "start": starts[low].isoformat()}, "close": closes[-1] / 100}
    big = sorted(names.items(), key=lambda kv: -kv[1])[:3]
    runway = {n: s["runway"] for n, s in scen.items()}
    head = (f"Base-case runway: {runway['base']} weeks" if anchored else
            "Unanchored forecast: no current cash balance, so closing figures are net change only and runway is unknown")
    facts = f"Base runway {runway['base']}. Close base {scen['base']['close']}, low {scen['low']['close']}, high {scen['high']['close']}. Largest outflows: " + ", ".join(f"{n} {p / 100}" for n, p in big)
    fallback = (f"{head}. After {WEEKS} weeks the base case closes at {scen['base']['close']:.2f}, low at {scen['low']['close']:.2f} and high at {scen['high']['close']:.2f}. "
                + ("Largest outflows are " + ", ".join(f"{n} ({p / 100:.2f})" for n, p in big) + "." if big else "No outflows are forecast."))
    text = phrase(facts, fallback)
    rows = [f"| {w['start']} | {w['in']:.2f} | {w['out']:.2f} | {w['close_base']:.2f} | {w['close_low']:.2f} | {w['close_high']:.2f} |" for w in weeks]
    md = [head + ".", "", "All figures in GBP. Costs are the same in every scenario. No unapproved spend is forecast and no tax is worked out.", "",
          "| Week start | In (base) | Out | Close base | Close low | Close high |", "|---|---|---|---|---|---|", *rows, "", "## Commentary", text, ""]
    md += ["## First week below buffer"] + [f"- {n}: {s['below']}" for n, s in scen.items()] + [""] if anchored else []
    md += ["## Notes", *[f"- {n}" for n in notes], "", "## For the pull request body", *[f"- {a}" for a in asks or ["Read the assumptions in office/finance/assumptions.json and merge when happy."]]]
    k.write(ctx, OFF + "finance/forecast.md", "\n".join(md))
    k.write(ctx, OFF + "finance/forecast.json", {"as_of": base.isoformat(), "anchored": anchored, "currency": "GBP", "weeks": weeks, "runway_weeks": runway,
            "first_below_buffer": {n: s["below"] for n, s in scen.items()}, "largest_outflows": [{"name": n, "gbp": p / 100} for n, p in big], "notes": notes + asks, "commentary": text})
    return {"summary": head + ". Forecast written for Charlie to read and merge.", "flag": "ok" if anchored else "caution"}


if __name__ == "__main__":
    k.run(main)
