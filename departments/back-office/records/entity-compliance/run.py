"""Entity Compliance: GitHub implementation of departments/back-office/records/entity-compliance/SKILL.md.

A dated brief and a register; nothing is ever filed, registered or paid. Nothing here is legal or tax advice.
The rules in RULES are starting prompts to check, not a source of truth: every date is marked unconfirmed
until the matching page in office/records/sources.json has been read, and a threshold is only ever taken
from a page, never from memory. No GitHub issues are opened (the job token belongs to the public repo):
items due within 30 days are listed under "Raise now" for Charlie.
"""
import calendar
import datetime as dt
import hashlib
import re

from foundry import jobkit as k
from foundry import util

OFF = "../../office/"
TOPIC = {"sa": ("self-assessment", "self assessment", "sa-"), "cs": ("confirmation-statement", "confirmation statement"), "acc": ("annual-accounts", "accounts"),
         "ct": ("corporation-tax", "corporation tax"), "vat": ("vat",), "paye": ("paye", "payroll", "employer"), "dp": ("data-protection", "ico")}
HELP = {"sa": ("Gather income and expense records, your UTR if you have one", "an accountant or the HMRC helpline"),
        "cs": ("Company authentication code, registered office and officer details", "Companies House or an accountant"),
        "acc": ("Year-end records and the bookkeeping file", "an accountant or Companies House"),
        "ct": ("Year-end accounts and the tax computation", "an accountant or HMRC"), "vat": ("Rolling 12-month taxable turnover", "an accountant or HMRC"),
        "paye": ("Employee details and payroll software", "an accountant or HMRC"), "dp": ("The ICO fee tier answers", "Legal data-protection or the ICO")}


def day(text):
    try:
        return dt.date.fromisoformat(str(text)[:10])
    except ValueError:
        return None


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    return dt.date(d.year + y, m + 1, min(d.day, calendar.monthrange(d.year + y, m + 1)[1]))


def md(y, m, d):
    return dt.date(y, m, min(d, calendar.monthrange(y, m)[1]))


def squash(t):
    return re.sub(r"\s+", " ", str(t)).strip().lower()


def jread(ctx, rel, default):
    try:
        data = k.read(ctx, rel, default)
    except ValueError:
        return default
    return data if isinstance(data, type(default)) else default


def rules(e, today):
    """(topic, kind, due) starting rules for one entity; due is None for a watch item. To be confirmed on the pages."""
    out, start = [], day(e.get("start_date"))
    ye = day(e.get("year_end")) or (day(f"2000-{e.get('year_end')}") if re.fullmatch(r"\d{2}-\d{2}", str(e.get("year_end") or "")) else None)
    floor = today - dt.timedelta(days=30)

    def nxt(month, d, y0=0):
        return next((x for y in range(today.year - 1, today.year + 3) if y >= y0 for x in [md(y, month, d)] if x >= floor), None)

    if e.get("type") == "sole-trader" and start:
        ty = start.year if start >= md(start.year, 4, 6) else start.year - 1
        if md(ty + 1, 10, 5) >= floor:
            out.append(("sa", "Register for Self Assessment", md(ty + 1, 10, 5)))
        out += [("sa", "Self Assessment return and balancing payment", nxt(1, 31, ty + 2)), ("sa", "Payment on account (January)", nxt(1, 31, ty + 2)),
                ("sa", "Payment on account (July)", nxt(7, 31, ty + 2)), ("sa", "Trading allowance limit check", None)]
    if e.get("type") == "company":
        if start:
            out.append(("cs", "Confirmation statement", nxt(start.month, start.day, start.year + 1)))
        if ye:
            ends = [md(y, ye.month, ye.day) for y in range(today.year - 2, today.year + 2)]
            for t, kind, fn in (("acc", "Annual accounts", lambda pe: add_months(pe, 9)), ("ct", "Corporation Tax return", lambda pe: add_months(pe, 12)),
                                ("ct", "Corporation Tax payment", lambda pe: add_months(pe, 9) + dt.timedelta(days=1))):
                due = min((fn(pe) for pe in ends if fn(pe) >= floor and (not start or pe > start)), default=None)
                out.append((t, kind, due))
    out.append(("vat", "VAT registration threshold watch", None))
    if e.get("has_staff"):
        out.append(("paye", "PAYE obligations check", None))
    out.append(("dp", "Data protection fee check", None))
    return [x for x in out if x[2] or x[1].endswith(("watch", "check"))]


def main(ctx):
    root = ctx["folder"].parent.parent / "office"
    today = dt.date.fromisoformat(util.today())
    ents = [e for e in jread(ctx, OFF + "records/entities.json", []) if isinstance(e, dict)]
    revenue = []
    for f in sorted((root / "finance" / "revenue").glob("*.json")) if (root / "finance" / "revenue").is_dir() else []:
        data = util.read_json(f, {})
        revenue.append((f.stem, data if isinstance(data, dict) else {}))
    earned = any((d.get("total_gbp") or 0) > 0 for _, d in revenue)
    for p in ctx["folder"].parent.iterdir() if ctx["folder"].parent.is_dir() else []:
        pay = util.read_json(p / "finance" / "payments.json", {}) if (p / "finance" / "payments.json").exists() else {}
        earned = earned or any(r.get("status") == "paid" for r in (pay.get("rows", []) if isinstance(pay, dict) else []) if isinstance(r, dict))
    register = [r for r in jread(ctx, OFF + "records/compliance.json", []) if isinstance(r, dict)]
    if not ents:
        brief = ["# Compliance brief", f"Dated {today}. Nothing here is legal or tax advice. Nothing is filed by the job.", "",
                 "No entity, nothing due." if not earned else "No entity is recorded, but a venture has taken money.", "",
                 "## Watch item", "When a venture takes its first payment, ask Legal `entity-and-structure` and check whether you must register as self-employed with HMRC."
                 + (" A venture has now taken money: do this now." if earned else "")]
        k.write(ctx, OFF + "records/compliance-brief.md", "\n".join(brief))
        k.write(ctx, OFF + "records/compliance.json", register)
        return {"summary": "No entity and " + ("revenue exists: Charlie asks Legal entity-and-structure." if earned else "no revenue: nothing due."), "flag": "caution" if earned else "clear"}
    srcs = k.read(ctx, OFF + "records/sources.json", [])
    pairs = [(str(label), str(u)) for label, u in srcs.items()] if isinstance(srcs, dict) else \
        [(str(r.get("topic") or r.get("name") or r.get("kind") or ""), str(r.get("url") or "")) if isinstance(r, dict) else ("", str(r)) for r in srcs] if isinstance(srcs, list) else []
    url_for = lambda t: next((u for lbl, u in pairs if u.startswith("http") and any(w in (lbl + " " + u).lower() for w in TOPIC[t])), None)
    pages, vat_limit, rows, notes = {}, None, [], []
    cut = add_months(today, -12).isoformat()[:7]
    for e in ents:
        slugs = [str(v) for v in e.get("ventures", [])] if isinstance(e.get("ventures"), list) else []
        total = sum(sum((v.get("gbp") or 0) for v in d.get("ventures", []) if isinstance(v, dict) and (not slugs or v.get("slug") in slugs)) if d.get("ventures") else (d.get("total_gbp") or 0)
                    for stem, d in revenue if stem > cut)
        for t, kind, due in rules(e, today):
            url, prior = url_for(t), next((r for r in register if r.get("entity") == e.get("id") and r.get("kind") == kind), {})
            if url and url not in pages:
                text = k.fetch(url, 15000)
                ans = k.ask("List up to 8 deadlines, thresholds or rules stated on this gov.uk page, each with an exact quote from the page. "
                            'Return JSON only: {"facts": [{"item": "<short label>", "quote": "<exact words from the page>"}]}\n\nPAGE\n' + text) if text else None
                facts = [f for f in (ans.get("facts") if isinstance(ans, dict) and isinstance(ans.get("facts"), list) else []) if isinstance(f, dict) and squash(f.get("quote", "")) and squash(f["quote"]) in squash(text)]
                pages[url] = {"read": bool(text), "asked": ans is not None, "fp": hashlib.sha1("|".join(sorted(squash(f["quote"]) for f in facts)).encode()).hexdigest()[:12] if facts else None}
                for f in facts if t == "vat" else []:
                    m = re.search(r"£\s?(\d{2,3}(?:,\d{3})+)", f["quote"])
                    if m and "threshold" in squash(f.get("item", "") + f["quote"]):
                        vat_limit = int(m.group(1).replace(",", ""))
            pg = pages.get(url or "", {})
            status = "dates-changed" if prior.get("fp") and pg.get("asked") and not pg.get("fp") == prior["fp"] else \
                "done" if prior.get("status") == "done" and prior.get("due") == (due.isoformat() if due else None) else "due" if due and (due - today).days <= 30 else "upcoming"
            if t == "vat" and vat_limit and total >= 0.7 * vat_limit:  # 70 percent of the threshold read from the page
                status = "due"
                notes.append(f"{e.get('name') or e.get('id')}: rolling turnover {total:,.0f} is {100 * total / vat_limit:.0f} percent of the {vat_limit:,} threshold read on the page. Register within 30 days of passing it.")
            rows.append({"id": f"{e.get('id')}:{kind}:{due or 'watch'}", "entity": e.get("id"), "kind": kind, "due": due.isoformat() if due else None, "source_url": url,
                         "checked_on": today.isoformat() if pg.get("read") else None, "status": status, "fp": pg.get("fp"), "topic": t})
    if not vat_limit:
        notes.append("VAT threshold not read from a page this run, so no VAT turnover check was made.")
    rows.sort(key=lambda r: (r["due"] or "9999", r["kind"]))
    lines = [f"# Compliance brief, {today}", "", "Nothing here is legal or tax advice. The job files nothing: you file. Dates marked UNCONFIRMED are starting rules not yet checked against a gov.uk page.", "",
             "| Due | Days | Entity | Obligation | Where | Have ready | Who can help | Status |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        have, who = HELP[r["topic"]]
        left = (day(r["due"]) - today).days if r["due"] else ""
        lines.append(f"| {r['due'] or 'watch'} | {left} | {r['entity']} | {r['kind']} | {r['source_url'] or 'no page in sources.json'} | {have} | {who} | {r['status']}{'' if r['checked_on'] else ', UNCONFIRMED'} |")
    soon = [r for r in rows if r["due"] and (day(r["due"]) - today).days <= 30]
    lines += ["", "## Raise now (due within 30 days)", *([f"- {r['kind']} for {r['entity']}, due {r['due']}" for r in soon] or ["- nothing"]), "", "## Notes", *([f"- {n}" for n in notes] or ["- none"]), ""]
    k.write(ctx, OFF + "records/compliance-brief.md", "\n".join(lines))
    k.write(ctx, OFF + "records/compliance.json", [{c: r.get(c) for c in ("id", "entity", "kind", "due", "source_url", "checked_on", "status", "fp")} for r in rows])
    return {"summary": f"{len(rows)} obligations listed for {len(ents)} entities, {len(soon)} due within 30 days, {sum(1 for r in rows if r['status'] == 'dates-changed')} page changes. Charlie files.",
            "flag": "caution" if soon or any(r["status"] == "dates-changed" for r in rows) else "ok"}


if __name__ == "__main__":
    k.run(main)
