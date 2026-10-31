"""Goal Pacing: GitHub implementation of departments/back-office/reporting/goal-pacing/SKILL.md.

Reads the income target from a line starting `Income target:` in brain/company.md; with none it writes a
null target, notes the skip and stops, and the job stays todo until Charlie sets one. A yearly target is
divided by 12; a date turns the target into a total to reach by then, spread over the remaining months.
The trend forecast is capped, and every forecast prints how many months it rests on.
"""
import calendar
import datetime as dt
import re

from foundry import jobkit as k
from foundry import util

OFF = "../../office/"
MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}


def tidy(text):
    """Model prose: no dashes, no exclamation marks."""
    return re.sub("[" + chr(0x2013) + chr(0x2014) + "]", ", ", str(text)).replace(chr(33), ".").strip()


def months_between(a, b):
    return (b.year - a.year) * 12 + b.month - a.month


def parse_target(line):
    """(amount, currency, period, by) from an Income target line, or None when no amount can be read."""
    m = re.search(r"([£$€]|GBP|USD|EUR)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(k\b)?", line, re.I)
    if not m:
        return None
    amount = float(m.group(2).replace(",", "")) * (1000 if m.group(3) else 1)
    code = re.search(r"\b(GBP|USD|EUR)\b", line, re.I)
    cur = {"£": "GBP", "$": "USD", "€": "EUR"}.get(m.group(1) or "", (m.group(1) or (code.group(1) if code else "GBP")).upper())
    period = "year" if re.search(r"year|annual|yearly|/yr|pa\b", line, re.I) else "month" if re.search(r"month|/m\b|pcm", line, re.I) else None
    by = re.search(r"(\d{4}-\d{2}-\d{2})", line)
    if by:
        by = by.group(1)
    else:
        mm = re.search(r"by\s+(?:\d{1,2}\s+)?([A-Za-z]+)\s+(\d{4})", line)
        by = f"{mm.group(2)}-{MONTHS[mm.group(1).lower()]:02d}-{calendar.monthrange(int(mm.group(2)), MONTHS[mm.group(1).lower()])[1]}" if mm and mm.group(1).lower() in MONTHS else None
    return amount, cur, period or ("year" if by is None and amount > 5000 else "total" if by else "month"), by


def note_skip(ctx, reason):
    path = ctx["folder"].parent.parent / "office" / "skipped.json"
    rows = [r for r in (util.read_json(path, []) if path.exists() else []) if isinstance(r, dict)]
    if not ctx["dry_run"] and not any(r.get("job") == "goal-pacing" and r.get("reason") == reason for r in rows):
        util.write_json(path, rows + [{"date": util.today(), "job": "goal-pacing", "reason": reason}])


def main(ctx):
    root = ctx["folder"].parent.parent / "office"
    today = dt.date.fromisoformat(util.today())
    line = next((ln.strip() for ln in str(ctx.get("company", "")).splitlines() if ln.strip().startswith("Income target:")), None)
    target = parse_target(line[len("Income target:"):]) if line else None
    if not target or target[1] not in ("GBP",):
        why = "no income target in brain/company.md; Charlie sets one" if not target else "the income target is not in GBP; Charlie restates it in pounds"
        k.write(ctx, OFF + "finance/pacing.json", {"as_of": today.isoformat(), "target": None, "status": "no-target", "note": why})
        ctx["outputs"].clear()  # a skip must leave the job todo so it runs once a target exists
        note_skip(ctx, why)
        return {"skipped": why}
    amount, cur, period, by = target
    end = dt.date.fromisoformat(by) if by else None
    left = max(months_between(today.replace(day=1), end) + 1, 1) if end else (12 - today.month + 1 if period == "year" else 1)
    monthly = amount if period == "month" else amount / 12 if period == "year" and not end else amount / left
    # actuals per month in GBP, parked ventures left out of the forecast
    parked = set()
    ventures = []
    for p in sorted(ctx["folder"].parent.iterdir()) if ctx["folder"].parent.is_dir() else []:
        b = util.read_json(p / "board.json", {}) if (p / "board.json").exists() else {}
        if isinstance(b, dict) and b:
            weekly = [w for w in b.get("weekly", []) if isinstance(w, dict)][-4:]
            ventures.append({"slug": p.name, "sign_ups_4w": int(sum(w.get("sign_ups") or 0 for w in weekly)), "verdict": b.get("verdict", "pending")})
            if b.get("verdict") == "park":
                parked.add(p.name)
    series = {}
    for f in sorted((root / "finance" / "revenue").glob("*.json")) if (root / "finance" / "revenue").is_dir() else []:
        d = util.read_json(f, {})
        if isinstance(d, dict):
            vs = [v for v in d.get("ventures", []) if isinstance(v, dict) and not v.get("no_data")]
            series[f.stem] = sum(v.get("gbp") or 0 for v in vs if v.get("slug") not in parked) if vs else (d.get("total_gbp") or 0)
    months = sorted(series)[-4:]
    vals = [series[m] for m in months]
    this = series.get(today.isoformat()[:7], 0.0)
    trailing = sum(vals[-3:]) / len(vals[-3:]) if vals else 0.0
    best = max(vals, default=0.0)
    deltas = [b - a for a, b in zip(vals, vals[1:])][-3:]
    step = sum(deltas) / len(deltas) if deltas else 0.0
    step = max(min(step, 0.25 * trailing), -0.25 * trailing)  # one odd month cannot project a fantasy
    horizon = max(left, 1)
    flat, trend = trailing, max(trailing + step * horizon, 0.0)
    status = "not-started" if not any(vals) else "ahead" if flat >= monthly else "on-pace" if trend >= monthly else "behind"
    gap = max(monthly - flat, 0.0)
    need = next((n for n in range(0, 61) if trailing + step * n >= monthly), None) if any(vals) else None
    months_needed = "not reachable at this pace" if status in ("behind", "not-started") and need is None else need
    out = {"as_of": today.isoformat(), "target": {"amount": amount, "currency": cur, "period": period, "by": by, "monthly_gbp": round(monthly, 2)}, "actual_month_gbp": round(this, 2),
           "trailing_avg_gbp": round(trailing, 2), "best_month_gbp": round(best, 2), "share_of_monthly_target": round(this / monthly, 2) if monthly else None,
           "forecast_flat_gbp": round(flat, 2), "forecast_trend_gbp": round(trend, 2), "status_uses": "flat forecast for ahead, trend forecast for on-pace", "status": status,
           "gap_gbp": round(gap, 2), "months_needed": months_needed, "rests_on_months": len(vals), "ventures": ventures}
    facts = (f"Status {status}. Monthly target {monthly:.2f} GBP. Trailing average {trailing:.2f}. This month {this:.2f}. Best month {best:.2f}. Flat forecast {flat:.2f}, trend forecast {trend:.2f}. "
             f"Gap {gap:.2f}. Months needed {months_needed}. Based on {len(vals)} months.")
    fallback = (f"Status is {status}. The monthly target is {monthly:.2f} GBP and the trailing average is {trailing:.2f} GBP. The flat forecast is {flat:.2f} GBP and the trend forecast is {trend:.2f} GBP, "
                f"both resting on {len(vals)} months of data, so treat them as a guess.")
    ans = k.ask('Write one plain factual paragraph of at most four sentences on pace against the income target, using only the numbers given. Return JSON only: {"paragraph": "<text>"}\n\nFACTS\n' + facts)
    text = tidy(ans.get("paragraph", "")) if isinstance(ans, dict) else ""
    nums = set(re.findall(r"\d+(?:\.\d+)?", facts))
    text = text if text and set(re.findall(r"\d+(?:\.\d+)?", text)) <= nums and len(re.findall(r"[.?]", text)) <= 5 else fallback
    table = [f"| {n} | {v} |" for n, v in (("Monthly target (GBP)", f"{monthly:.2f}"), ("This month to date", f"{this:.2f}"), ("Trailing average", f"{trailing:.2f}"), ("Best month", f"{best:.2f}"),
                                           ("Share of monthly target", f"{out['share_of_monthly_target']}"), ("Flat forecast", f"{flat:.2f}"), ("Trend forecast", f"{trend:.2f}"),
                                           ("Gap", f"{gap:.2f}"), ("Months needed", months_needed), ("Months of data", len(vals)))]
    k.write(ctx, OFF + "finance/pacing.json", out)
    k.write(ctx, OFF + "finance/pacing.md", "\n".join([f"Status: {status}", "", "| Measure | Value |", "|---|---|", *table, "", text, "",
                                                       "Venture indicators: " + (", ".join(f"{v['slug']} {v['sign_ups_4w']} sign-ups in four weeks, verdict {v['verdict']}" for v in ventures) or "none"), ""]))
    return {"summary": f"Pace is {status}: trailing average {trailing:.2f} GBP against {monthly:.2f} GBP a month, on {len(vals)} months of data.", "flag": "ok" if status in ("ahead", "on-pace") else "caution"}


if __name__ == "__main__":
    k.run(main)
