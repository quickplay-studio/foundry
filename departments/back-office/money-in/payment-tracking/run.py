"""Payment Tracking: GitHub implementation of departments/back-office/money-in/payment-tracking/SKILL.md.

No model: money columns are never guessed. Reads Stripe and bank CSV exports Charlie drops in finance/,
never a live connection. Keeps only id, date, amount, currency, status, refund, a short description and an
invoice reference. A paid row keeps its full amount; a refund is a separate negative row with status
`refunded`, so net revenue is the sum of amount_minor over paid and refunded rows.
"""
import csv
import datetime as dt
import hashlib
import io
import re
from decimal import Decimal, ROUND_HALF_UP

from foundry import jobkit as k
from foundry import util

COLS = {"id": ("id", "payment id", "charge id"), "date": ("created date (utc)", "created (utc)", "created", "date"), "amount": ("amount",),
        "currency": ("currency",), "status": ("status",), "refunded": ("amount refunded", "refunded"), "desc": ("description",)}
STATUS = {"paid": ("paid", "succeeded", "complete", "captured", "received"), "pending": ("pending", "processing", "requires", "uncaptured"),
          "failed": ("failed", "cancel", "declin", "expired"), "refunded": ("refund",)}


def day(text):
    try:
        return dt.date.fromisoformat(str(text).strip()[:10])
    except ValueError:
        return None


def minor(text, in_minor=False):
    try:
        v = Decimal(re.sub(r"[^0-9.\-]", "", str(text)) or "x")
    except Exception:  # noqa: BLE001
        return None
    return int(v if in_minor else (v * 100).quantize(Decimal(1), ROUND_HALF_UP))


def rows_of(data, *keys):
    if isinstance(data, dict):
        data = next((data[x] for x in keys if isinstance(data.get(x), list)), [])
    return [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []


def norm_status(text):
    t = str(text).strip().lower()
    return next((s for s, words in STATUS.items() if any(w in t for w in words)), "pending")


def clean(text):
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "", str(text))
    return re.sub(r"\d{7,}", "", text).strip()[:80]


def read_file(name, text, cur):
    """Rows from one export, or a reason to skip the file."""
    bank = name.startswith("bank-")
    reader = csv.DictReader(io.StringIO(text))
    heads = {(h or "").strip().lower(): h for h in reader.fieldnames or []}
    pick = {key: next((heads[a] for a in aliases if a in heads), None) for key, aliases in COLS.items()}
    need = ["date", "amount"] if bank else ["date", "amount", "currency", "status"]
    miss = [c for c in need if not pick[c]]
    if miss:
        return None, f"{name} skipped: no {', '.join(miss)} column"
    in_minor = "minor" in (pick["amount"] or "").lower() or "cents" in (pick["amount"] or "").lower()
    out = []
    for i, raw in enumerate(reader):
        d, amt = day(raw.get(pick["date"])), minor(raw.get(pick["amount"]), in_minor)
        if not d or amt is None or (bank and amt <= 0):
            continue  # a bank debit or a row without a date or amount is not a payment
        st = norm_status(raw.get(pick["status"])) if pick["status"] else "paid"
        ref = minor(raw.get(pick["refunded"]), in_minor) or 0 if pick["refunded"] else 0
        raw_desc = raw.get(pick["desc"]) or "" if pick["desc"] else ""
        pid = (raw.get(pick["id"]) or "").strip() if pick["id"] else ""
        row = {"id": pid or hashlib.sha1(f"{name}{i}{d}{amt}".encode()).hexdigest()[:12], "date": d.isoformat(), "amount_minor": amt,
               "currency": (raw.get(pick["currency"]) or cur).strip().upper() if pick["currency"] else cur, "status": st, "refunded_minor": ref,
               "description": clean(raw_desc), "invoice": (re.search(r"INV-\d{4}-\d{4}", raw_desc) or [None])[0], "source": name}
        if st == "refunded" and amt < 0:  # an export row that is itself a refund
            out.append(row)
            continue
        if st == "refunded":  # Stripe shows a refunded charge as one row: keep the payment, add the refund
            row["status"], ref = "paid", ref or amt
            row["refunded_minor"] = ref
        out.append(row)
        if ref > 0:
            out.append(dict(row, id=row["id"] + "-refund", amount_minor=-ref, status="refunded", refunded_minor=0))
    return out, None


def main(ctx):
    fin = ctx["folder"] / "finance"
    if not fin.is_dir():
        return {"skipped": "no finance folder yet"}
    cur = (ctx.get("budget") or {}).get("currency") or "GBP"
    today = dt.date.fromisoformat(util.today())
    done = rows_of(k.read(ctx, "finance/processed.json", []), "files")
    seen = {r.get("sha256") for r in done}
    old = k.read(ctx, "finance/payments.json", {})
    rows = {r["id"]: r for r in rows_of(old.get("rows", []) if isinstance(old, dict) else []) if r.get("id")}
    skips, fresh = [], 0
    files = sorted(fin.glob("stripe-*.csv")) + sorted(fin.glob("bank-*.csv"))
    for path in files:
        raw = path.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        if sha in seen:
            continue
        got, why = read_file(path.name, raw.decode("utf-8-sig", errors="replace"), cur)
        if why:
            skips.append(why)
            continue
        for r in got:
            r["invoice"] = r["invoice"] or (rows.get(r["id"]) or {}).get("invoice")
            rows[r["id"]] = r
            fresh += 1
        done.append({"file": path.name, "sha256": sha, "read": today.isoformat()})
    register = [r for r in rows_of(k.read(ctx, "finance/invoices.json", []), "rows", "invoices") if r.get("status") not in ("draft", "void")]
    known = {r.get("number") for r in register}
    paid_on = lambda n: sum(r["amount_minor"] for r in rows.values() if r.get("invoice") == n and r.get("status") in ("paid", "refunded"))
    # match by reference, else by exact amount and currency within 30 days when exactly one open invoice fits
    unmatched = []
    for r in sorted(rows.values(), key=lambda x: x["date"]):
        if r.get("invoice") in known or r["status"] not in ("paid", "pending") or r["amount_minor"] <= 0:
            continue
        r["invoice"] = None
        fits = [i for i in register if i.get("currency", cur) == r["currency"] and i.get("total_minor") == r["amount_minor"] and day(i.get("date"))
                and abs((day(r["date"]) - day(i["date"])).days) <= 30 and paid_on(i.get("number")) < (i.get("total_minor") or 0)]
        if len(fits) == 1:
            r["invoice"] = fits[0]["number"]
        elif fits or r["source"].startswith("bank-") or re.search(r"INV-\d", r.get("description", "")):
            unmatched.append(r["id"])
    for r in rows.values():  # a refund follows its payment
        if r["id"].endswith("-refund") and rows.get(r["id"][:-7], {}).get("invoice"):
            r["invoice"] = rows[r["id"][:-7]]["invoice"]
    states = []
    for i in register:
        n, total, due = i.get("number"), i.get("total_minor") or 0, day(i.get("due"))
        got = paid_on(n)
        if total and got >= total:
            states.append({"number": n, "state": "paid", "days_late": 0})
        elif due and today > due:
            states.append({"number": n, "state": "late", "days_late": (today - due).days})
        else:
            states.append({"number": n, "state": "part-paid" if got > 0 else "due", "days_late": 0})
    note = "" if files else "no payment exports yet, so no revenue"
    out_rows = sorted(rows.values(), key=lambda r: (r["date"], r["id"]))
    payload = {"currency": cur, "updated": util.now(), "rows": [{c: r.get(c) for c in ("id", "date", "amount_minor", "currency", "status", "refunded_minor", "invoice", "source")} for r in out_rows],
               "invoices": states, "unmatched": unmatched}
    k.write(ctx, "finance/payments.json", dict(payload, note=note) if note else payload)
    month = today.isoformat()[:7]
    paid_m = sum(r["amount_minor"] for r in out_rows if r["date"][:7] == month and r["status"] in ("paid", "refunded"))
    dues = {i.get("number"): day(i.get("due")) for i in register}
    soon = [s for s in states if s["state"] == "due" and dues.get(s["number"]) and dues[s["number"]] <= today + dt.timedelta(days=7)]
    k.write(ctx, "finance/payments.md", "\n".join([
        f"# Payments, updated {today}", note, "", f"Paid this month: {cur} {paid_m / 100:,.2f} (net of refunds).", "",
        "## Due in the next seven days", *([f"- {s['number']}" for s in soon] or ["- none"]), "",
        "## Late", *([f"- {s['number']}: {s['days_late']} days late" for s in states if s["state"] == "late"] or ["- none"]), "",
        "## Unmatched, for Charlie", *([f"- {u}" for u in unmatched] or ["- none"]), ""]))
    k.write(ctx, "finance/processed.json", done)
    if skips:
        board = k.read(ctx, "board.json", None) or ctx.get("board") or {}
        held = board.get("skipped", [])
        add = [{"job": "payment-tracking", "reason": s, "date": today.isoformat()} for s in skips if not any(h.get("reason") == s for h in held if isinstance(h, dict))]
        if add:
            k.write(ctx, "board.json", dict(board, skipped=(held + add)[-40:]))
    late = sum(1 for s in states if s["state"] == "late")
    return {"summary": f"{fresh} new payment rows from {len(done)} files read; {late} late, {len(unmatched)} unmatched, {len(skips)} files skipped.",
            "flag": "caution" if late or unmatched or skips else "ok"}


if __name__ == "__main__":
    k.run(main)
