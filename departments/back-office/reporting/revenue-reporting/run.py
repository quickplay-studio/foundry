"""Revenue Reporting: GitHub implementation of departments/back-office/reporting/revenue-reporting/SKILL.md.

Monthly revenue across ventures and currencies, in integer pence. The month is the last complete calendar
month, or REVENUE_MONTH (YYYY-MM) when set. Paid rows count up and refund rows (negative, status refunded)
count down, both dated in the month. Rates come from the ECB reference rates over the Frankfurter API and are
never guessed: with no rate a currency stays in its own column and gbp is null. The model only phrases the paragraph.
"""
import calendar
import datetime as dt
import os
import re
from decimal import Decimal, ROUND_HALF_UP

import requests

from foundry import jobkit as k
from foundry import util

OFF = "../../office/"
RATE_URLS = ("https://api.frankfurter.dev/v1/{d}?base=GBP&symbols={s}", "https://api.frankfurter.app/{d}?from=GBP&to={s}")


def tidy(text):
    """Model prose: no dashes, no exclamation marks."""
    return re.sub("[" + chr(0x2013) + chr(0x2014) + "]", ", ", str(text)).replace(chr(33), ".").strip()


def day(text):
    try:
        return dt.date.fromisoformat(str(text)[:10])
    except ValueError:
        return None


def gbp_of(minor, rate):
    return int((Decimal(minor) * Decimal(str(rate))).quantize(Decimal(1), ROUND_HALF_UP))


def month_rates(month_end, currencies):
    """GBP per unit of each currency on the last working day on or before month_end, or {} when unavailable."""
    for url in RATE_URLS:
        try:
            r = requests.get(url.format(d=month_end.isoformat(), s=",".join(sorted(currencies))), timeout=10)
            got = r.json().get("rates", {}) if r.ok else {}
            if got:
                return {c: 1 / float(v) for c, v in got.items() if v}, str(r.json().get("date", month_end))
        except Exception:  # noqa: BLE001
            continue
    return {}, None


def phrase(facts, fallback):
    ans = k.ask('Write one plain paragraph of at most four sentences on what changed in revenue this month, facts only, using only the numbers given. Return JSON only: {"paragraph": "<text>"}\n\nFACTS\n' + facts)
    text = tidy(ans.get("paragraph", "")) if isinstance(ans, dict) else ""
    nums = set(re.findall(r"\d+(?:\.\d+)?", facts))
    return text if text and len(re.findall(r"[.?]", text)) <= 5 and set(re.findall(r"\d+(?:\.\d+)?", text)) <= nums else fallback


def note_skip(ctx, reason):
    path = ctx["folder"].parent.parent / "office" / "skipped.json"
    rows = [r for r in (util.read_json(path, []) if path.exists() else []) if isinstance(r, dict)]
    if not ctx["dry_run"] and not any(r.get("job") == "revenue-reporting" and r.get("reason") == reason for r in rows):
        util.write_json(path, rows + [{"date": util.today(), "job": "revenue-reporting", "reason": reason}])


def main(ctx):
    root = ctx["folder"].parent.parent / "office"
    today = dt.date.fromisoformat(util.today())
    want = os.environ.get("REVENUE_MONTH", "").strip()
    first = dt.date.fromisoformat(want + "-01") if re.fullmatch(r"\d{4}-\d{2}", want) else (today.replace(day=1) - dt.timedelta(days=1)).replace(day=1)
    month = first.isoformat()[:7]
    end = first.replace(day=calendar.monthrange(first.year, first.month)[1])
    vdirs = [p for p in sorted(ctx["folder"].parent.iterdir()) if p.is_dir() and (p / "board.json").exists()] if ctx["folder"].parent.is_dir() else []
    seen, native = [], {}
    for p in vdirs:
        pay = util.read_json(p / "finance" / "payments.json", None) if (p / "finance" / "payments.json").exists() else None
        if not isinstance(pay, dict):
            seen.append({"slug": p.name, "no_data": True, "gbp": None})
            continue
        tot, refunds, ids, rec = {}, {}, set(), 0
        for r in pay.get("rows", []):
            if not isinstance(r, dict) or str(r.get("date", ""))[:7] > month or str(r.get("date", ""))[:7] < month or r.get("status") not in ("paid", "refunded"):
                continue
            amt, c = int(r.get("amount_minor") or 0), str(r.get("currency") or "GBP").upper()
            amt = -abs(amt) if r["status"] == "refunded" else amt
            tot[c] = tot.get(c, 0) + amt
            if amt < 0:
                refunds[c] = refunds.get(c, 0) + amt
            elif r.get("id"):
                ids.add(r["id"])
            rec += amt if re.search(r"subscription|recurring|renewal|monthly", str(r.get("description", "")), re.I) and amt > 0 else 0
        bud = util.read_json(p / "budget.json", {}) if (p / "budget.json").exists() else {}
        bud = bud if isinstance(bud, dict) else {}
        spend = sum(float(x.get("amount") or 0) for x in bud.get("lines", []) if isinstance(x, dict) and str(x.get("date", ""))[:7] == month)
        seen.append({"slug": p.name, "tot": tot, "refunds": refunds, "customers": len(ids), "rec": rec, "spend": spend, "scur": bud.get("currency") or "GBP"})
    # rates for the month end, only when a non-GBP currency is involved
    need = {c for v in seen for c in list(v.get("tot", {})) + [v.get("scur", "GBP")] if c not in ("GBP",)}
    rates, rdate, notes = {"GBP": 1.0}, None, []
    if need:
        got, rdate = month_rates(end, need)
        rates.update(got)
        stored = k.read(ctx, OFF + "finance/rates.json", {})
        if got and (not isinstance(stored, dict) or not day(stored.get("date")) or (today - day(stored["date"])).days > 7):
            k.write(ctx, OFF + "finance/rates.json", {"date": rdate, "source": "ECB reference rates via Frankfurter", "rates": {c: v for c, v in got.items()}})
        for c in sorted(need - set(rates)):
            notes.append(f"no rate for {c} on {end}, kept in its own column with gbp null")
            note_skip(ctx, f"no {c} rate for {month}, left as native only")
    def pence_of(d):
        """Pence in GBP for a {currency: minor} dict, or None when any currency has no rate."""
        return None if any(c not in rates for c in d) else sum(gbp_of(a, rates[c]) for c, a in d.items())

    rows, total = [], 0
    for v in seen:
        if v.get("no_data"):
            rows.append(v)
            continue
        g, rf = pence_of(v["tot"]), pence_of(v["refunds"])
        row = {"slug": v["slug"], "native": {c: a / 100 for c, a in v["tot"].items()}, "gbp": None if g is None else g / 100, "refunds_gbp": None if rf is None else rf / 100,
               "spend_gbp": round(v["spend"] * rates[v["scur"]], 2) if v["scur"] in rates else None, "customers": v["customers"]}
        if v["rec"] and g is not None and list(v["tot"]) == ["GBP"]:  # one line unless the descriptions allow a split
            row.update(new_gbp=(g - v["rec"]) / 100, recurring_gbp=v["rec"] / 100)
        total += g or 0
        rows.append(row)
    prev = util.read_json(root / "finance" / "revenue" / f"{(first - dt.timedelta(days=1)).isoformat()[:7]}.json", {}) if (root / "finance" / "revenue" / f"{(first - dt.timedelta(days=1)).isoformat()[:7]}.json").exists() else {}
    prev_total = prev.get("total_gbp") if isinstance(prev, dict) else None
    spend_all = sum(r["spend_gbp"] or 0 for r in rows if not r.get("no_data"))
    if not vdirs:
        notes.append("no ventures found")
    for r in rows:
        if r.get("no_data"):
            notes.append(f"{r['slug']}: no data (no payments.json)")
    out = {"month": month, "rates_date": rdate, "total_gbp": total / 100, "change_gbp": None if prev_total is None else round(total / 100 - prev_total, 2), "spend_gbp": round(spend_all, 2),
           "revenue_minus_spend_gbp": round(total / 100 - spend_all, 2), "ventures": rows, "notes": notes}
    facts = f"Month {month}. Total revenue {total / 100:.2f} GBP across {sum(1 for r in rows if not r.get('no_data'))} ventures. Change on last month {out['change_gbp']}. Spend {spend_all:.2f}. Revenue minus spend {out['revenue_minus_spend_gbp']}."
    fallback = (f"Revenue for {month} was {total / 100:.2f} GBP. " + ("The month before has no report, so there is no change to show. " if prev_total is None else f"That is {out['change_gbp']:+.2f} GBP on the month before. ")
                + f"Spend was {spend_all:.2f} GBP, leaving {out['revenue_minus_spend_gbp']:.2f} GBP.")
    text = phrase(facts, fallback)
    k.write(ctx, OFF + f"finance/revenue/{month}.json", out)
    table = [f"| {r['slug']} | " + ("no data | | | |" if r.get("no_data") else f"{r['gbp'] if r['gbp'] is not None else 'null'} | {r['refunds_gbp']} | {r['spend_gbp']} | {r['customers']} |") for r in rows]
    k.write(ctx, OFF + f"finance/revenue/{month}.md", "\n".join([f"# Revenue {month}", "", f"Total: {total / 100:.2f} GBP. Rates date: {rdate or 'not needed'}.", "",
            "| Venture | GBP | Refunds GBP | Spend GBP | Customers |", "|---|---|---|---|---|", *table, "", text, "", *[f"- {n}" for n in notes], ""]))
    return {"summary": f"Revenue {month}: {total / 100:.2f} GBP across {len(rows)} ventures. {len(notes)} notes.", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
