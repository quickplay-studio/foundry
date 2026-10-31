"""Invoice Generation: GitHub implementation of departments/back-office/money-in/invoice-generation/SKILL.md.

No model. Validates each request, numbers it gapless, calculates in integer pence and renders HTML and
Markdown drafts. Nothing is emailed. Account and sort code numbers never go in the repo.
"""
import base64
import datetime as dt
import hashlib
import html
import re
from decimal import Decimal, ROUND_HALF_UP
from string import Template

from foundry import jobkit as k
from foundry import util

OFF = "../../office/"
HMRC = "https://www.gov.uk/vat-record-keeping/vat-invoices"
PAGE = Template("<" + chr(33) + """doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><title>$number</title><meta name="viewport" content="width=device-width, initial-scale=1">
<style>:root{--accent:$accent}body{font:15px/1.5 system-ui,sans-serif;max-width:760px;margin:2rem auto;padding:0 1rem;color:#222}
h1{color:var(--accent);margin:0}table{width:100%;border-collapse:collapse;margin:1.5rem 0}th,td{padding:.4rem .5rem;text-align:left;border-bottom:1px solid #ddd}
td.n,th.n{text-align:right}.tot td{font-weight:700;border-top:2px solid var(--accent)}img{max-height:56px}@media print{body{margin:0}}</style></head><body>
$logo<h1>Invoice $number</h1><p>Date: $date<br>Due: $due<br>Reference: $reference</p>
<p><strong>From</strong><br>$issuer</p><p><strong>To</strong><br>$customer</p>
<table><tr><th>Description</th><th class="n">Qty</th><th class="n">Unit price</th><th class="n">Net</th><th class="n">VAT</th></tr>$rows
<tr class="tot"><td colspan="3">Total ($currency)</td><td class="n">$net</td><td class="n">$vat</td></tr></table>
<p><strong>Total due: $total $currency by $due</strong></p><p>$vatline</p><p>How to pay: $pay</p></body></html>
""")


def dec(x):
    return Decimal(str(x))


def minor(x):
    return int((dec(x) * 100).quantize(Decimal(1), ROUND_HALF_UP))


def fmt(p):
    return f"{p / 100:,.2f}"


def jread(ctx, rel, default):
    try:
        data = k.read(ctx, rel, default)
    except ValueError:
        return default
    return data if isinstance(data, type(default)) else default


def check(r):
    """A reason to reject the request, or None. Nothing is repaired."""
    if not isinstance(r, dict):
        return "not an object"
    if not str(r.get("customer") or "").strip() or not str(r.get("customer_address") or "").strip():
        return "customer or address missing"
    if not str(r.get("reference") or "").strip():
        return "no reference"
    if not re.fullmatch(r"[A-Z]{3}", str(r.get("currency") or "")):
        return "no currency code"
    due = r.get("due_days")
    if isinstance(due, bool) or not isinstance(due, int) or not 0 <= due <= 365:
        return "due_days missing or not a whole number"
    items = r.get("items")
    if not isinstance(items, list) or not items:
        return "no items"
    for i in items:
        ok = isinstance(i, dict) and str(i.get("description") or "").strip()
        for f in ("quantity", "unit_price"):
            ok = ok and isinstance(i.get(f), (int, float)) and not isinstance(i.get(f), bool) and i[f] > 0
        if not ok:
            return "an item needs a description, a positive quantity and a positive unit price"
    return None


def main(ctx):
    issuer = jread(ctx, OFF + "finance/issuer.json", {})
    tax = jread(ctx, "finance/tax.json", {})
    name, addr = issuer.get("name") or issuer.get("issuer"), issuer.get("address")
    if not (name and addr) or not tax:
        return {"skipped": "no issuer set"}
    vat_on = bool(tax.get("vat_registered"))
    vat_no = issuer.get("vat_number") or issuer.get("vat")
    if vat_on and not vat_no:
        return {"skipped": "VAT registered but no VAT number in issuer.json"}
    rate = dec(tax.get("vat_rate") or 0)
    rate = rate if rate <= 1 else rate / 100
    reqs = k.read(ctx, "finance/invoice-requests.json", [])
    if not isinstance(reqs, list) or not reqs:
        return {"skipped": "no invoice requests"}
    reg = k.read(ctx, "finance/invoices.json", [])
    meta = reg if isinstance(reg, dict) else {}
    rows = [r for r in (reg.get("rows", []) if isinstance(reg, dict) else reg) if isinstance(r, dict)]
    line = str(issuer.get("payment_line") or issuer.get("payment") or "")
    if not line or re.search(r"\d{6,}|\d{2}-\d{2}-\d{2}", line):
        line = "reply for bank details"
    logo = k.read(ctx, "brand/logo.svg", "") or ""
    accent = (re.search(r"#[0-9a-fA-F]{6}\b", logo) or [None])[0] or "#1f4e79"
    img = f'<img alt="" src="data:image/svg+xml;base64,{base64.b64encode(logo.encode()).decode()}">' if logo else ""
    today = dt.date.fromisoformat(util.today())
    done, bad = [], []
    for req in reqs:
        why = check(req)
        if why:
            bad.append(f"{req.get('reference') if isinstance(req, dict) else '?'}: {why}")
            continue
        if any(r.get("reference") == req["reference"] for r in rows):
            continue  # issued already
        seqs = [int(m.group(1)) for r in rows for m in [re.fullmatch(rf"INV-{today.year}-(\d{{4}})", str(r.get("number")))] if m]
        number = f"INV-{today.year}-{max(seqs, default=0) + 1:04d}"
        due = today + dt.timedelta(days=req["due_days"])
        net = vat = 0
        body, md = [], []
        for i in req["items"]:
            n = minor(dec(i["quantity"]) * dec(i["unit_price"]))
            v = int((dec(n) * rate).quantize(Decimal(1), ROUND_HALF_UP)) if vat_on else 0
            net, vat = net + n, vat + v
            d = html.escape(str(i["description"]))
            body.append(f'<tr><td>{d}</td><td class="n">{i["quantity"]}</td><td class="n">{fmt(minor(i["unit_price"]))}</td><td class="n">{fmt(n)}</td><td class="n">{fmt(v)}</td></tr>')
            md.append(f"| {str(i['description']).replace('|', '/')} | {i['quantity']} | {fmt(minor(i['unit_price']))} | {fmt(n)} | {fmt(v)} |")
        vatline = f"VAT at {(rate * 100).normalize():f} percent. VAT number {html.escape(str(vat_no))}." if vat_on else "No VAT charged."
        esc = lambda s: html.escape(str(s)).replace("\n", "<br>")
        k.write(ctx, f"finance/invoices/{number}.html", PAGE.substitute(
            number=number, accent=accent, logo=img, date=today, due=due, reference=esc(req["reference"]), issuer=esc(f"{name}\n{addr}\n{issuer.get('email') or ''}"),
            customer=esc(f"{req['customer']}\n{req['customer_address']}"), rows="".join(body), currency=req["currency"], net=fmt(net), vat=fmt(vat),
            total=fmt(net + vat), vatline=vatline, pay=esc(line)))
        k.write(ctx, f"finance/invoices/{number}.md", "\n".join([
            f"# Invoice {number}", "", f"Date: {today}  \nDue: {due}  \nReference: {req['reference']}", "", f"From: {name}, {addr}  \nTo: {req['customer']}, {req['customer_address']}", "",
            "| Description | Qty | Unit price | Net | VAT |", "|---|---|---|---|---|", *md, "",
            f"Net {fmt(net)} {req['currency']}, VAT {fmt(vat)}, **total {fmt(net + vat)} {req['currency']}** due {due}.", "", vatline, f"How to pay: {line}", ""]))
        rows.append({"number": number, "reference": req["reference"], "date": today.isoformat(), "due": due.isoformat(), "customer": req["customer"], "currency": req["currency"],
                     "net_minor": net, "vat_minor": vat, "total_minor": net + vat, "status": "draft"})
        done.append(number)
    if done:
        # quarterly look at the HMRC guidance; a changed page is noted for Charlie
        g = meta.get("guidance") if isinstance(meta.get("guidance"), dict) else {}
        if not g or (today - dt.date.fromisoformat(g.get("checked_on", "2000-01-01"))).days > 90:
            text = k.fetch(HMRC, 20000)
            if text:
                h = hashlib.sha256(re.sub(r"\s+", " ", text).encode()).hexdigest()[:16]
                note = g.get("note", "")
                if g.get("hash") and not g["hash"] == h:
                    note = f"{today}: the HMRC invoice guidance page changed since {g.get('checked_on')}; check the invoice list still holds"
                g = {"url": HMRC, "checked_on": today.isoformat(), "hash": h, "note": note}
        k.write(ctx, "finance/invoices.json", dict(meta, rows=rows, last_number=done[-1], guidance=g))
    if not done:
        return {"skipped": "no new valid invoice request" + (f"; rejected: {'; '.join(bad)}" if bad else "")}
    return {"summary": f"Drafted {', '.join(done)}." + (f" Rejected: {'; '.join(bad)}." if bad else "") + " Charlie checks the totals, sends and marks sent.", "flag": "caution" if bad else "ok"}


if __name__ == "__main__":
    k.run(main)
