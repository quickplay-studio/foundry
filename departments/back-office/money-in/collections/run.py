"""Collections: GitHub implementation of departments/back-office/money-in/collections/SKILL.md.

Picks the next touch for each late invoice and drafts it from a fixed template; the model may add one
personal line, nothing else. Nothing is sent: Charlie sends and marks the log row `sent`.
"""
import datetime as dt
import re

from foundry import jobkit as k
from foundry import util

OFF = "../../office/"
INTEREST = "https://www.gov.uk/late-commercial-payments-interest-debt-recovery"
CLAIM = "https://www.gov.uk/make-court-claim-for-money"
TOUCH = {
    1: ("friendly reminder", "A quick reminder that invoice {n} for {amt}, due on {due}, is now {days} days overdue. The invoice is attached as {n}.",
        "If it is already on its way, please ignore this note."),
    2: ("payment date needed", "Invoice {n} for {amt} was due on {due} and is now {days} days overdue. I have not yet had a payment or a date.",
        "Please reply with the date you will pay it."),
    3: ("final reminder", "This is the final reminder for invoice {n}, {amt}, due on {due} and now {days} days overdue.",
        "If I have not heard from you by {by}, I will decide the next steps, which may include pausing further work for you."),
}


def tidy(text):
    """Model prose: no dashes, no exclamation marks."""
    return re.sub("[" + chr(0x2013) + chr(0x2014) + "]", ", ", str(text)).replace(chr(33), ".").strip()


def day(text):
    try:
        return dt.date.fromisoformat(str(text)[:10])
    except ValueError:
        return None


def rows_of(data, *keys):
    if isinstance(data, dict):
        data = next((data[x] for x in keys if isinstance(data.get(x), list)), [])
    return [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []


def personal_line(customer, brain):
    ans = k.ask('Write one short, friendly sentence for a payment reminder to this customer, using only facts in the context, no figures, '
                'no threats. If there is nothing to say, use an empty string. Return JSON only: {"personal_line": "<sentence>"}\n\nCUSTOMER\n'
                + customer + "\n\nCONTEXT\n" + brain[:1500])
    text = tidy(ans.get("personal_line", "")) if isinstance(ans, dict) else ""
    return text if 0 < len(text) <= 160 and not re.search(r"\d", text) else ""


def main(ctx):
    audit = k.read(ctx, "audit.json", {})
    model = str(ctx["idea"].get("business_model") or (audit.get("business_model") if isinstance(audit, dict) else "") or "").lower()
    if model == "b2c":
        return {"skipped": "buyer is a consumer: no chasing drafts, see Legal consumer-law-check"}
    pay = k.read(ctx, "finance/payments.json", {})
    late = [r for r in rows_of(pay.get("invoices", []) if isinstance(pay, dict) else [], "invoices") if r.get("state") == "late"]
    register = {r.get("number"): r for r in rows_of(k.read(ctx, "finance/invoices.json", []), "rows", "invoices")}
    log = k.read(ctx, "finance/collections/log.json", [])
    log = [r for r in (log if isinstance(log, list) else []) if isinstance(r, dict)]
    issuer = k.read(ctx, OFF + "finance/issuer.json", {})
    issuer = issuer if isinstance(issuer, dict) else {}
    pay_line = str(issuer.get("payment_line") or issuer.get("payment") or "")
    if not pay_line or re.search(r"\d{6,}|\d{2}-\d{2}-\d{2}", pay_line):
        pay_line = "reply to this message and I will send the payment details"
    today = dt.date.fromisoformat(util.today())
    wk = today.isocalendar()[:2]
    made, held, briefs = [], [], []
    for inv in late:
        n, rec = inv.get("number"), register.get(inv.get("number"))
        mine = [r for r in log if r.get("invoice") == n]
        if not rec or any(r.get("status") in ("paid", "closed", "disputed") for r in mine):
            continue
        if any(day(r.get("promised")) and day(r.get("promised")) >= today for r in mine):
            held.append(n)  # a promised date has not passed yet
            continue
        days = int(inv.get("days_late") or 0)
        drafted = {int(r["touch"]): day(r.get("drafted")) for r in mine if str(r.get("touch", "")).isdigit()}
        last = max(drafted, default=0)
        amt = f"{'£' if rec.get('currency', 'GBP') == 'GBP' else rec.get('currency', '') + ' '}{(rec.get('total_minor') or 0) / 100:,.2f}"
        if last >= 3 and days >= 21:
            if not k.read(ctx, f"finance/collections/brief-{n}.md"):
                tl = ", ".join(f"touch {t} on {d}" for t, d in sorted(drafted.items())) or "none"
                k.write(ctx, f"finance/collections/brief-{n}.md", "\n".join([
                    f"# Decision brief: {n}", "", f"Owed: {amt}, due {rec.get('due')}, {days} days late. Customer: {rec.get('customer')}.", f"Touches drafted: {tl}.", "",
                    "## Options", "- Wait: no cost, but cash stays out and the risk grows.", f"- Write off: lose {amt}; Charlie decides and sets the log row to closed.",
                    f"- Solicitor or small claims: costs and court fees change, so read the current figures on gov.uk first: {CLAIM}", "",
                    f"Statutory interest on late business debts: read the current rate and rules on gov.uk before adding any line: {INTEREST}", "",
                    "Drafting has stopped. Charlie decides."]))
                briefs.append(n)
            continue
        touch = min(last + 1, 3, 1 if days < 7 else 2 if days < 14 else 3)
        if touch <= last or any(d and d.isocalendar()[:2] == wk for d in drafted.values()):
            continue  # already drafted, or one went out this week
        name, lead, ask = TOUCH[touch]
        by = (today + dt.timedelta(days=7)).isoformat()
        body = "\n\n".join(x for x in (f"Hello {rec.get('customer') or ''},".replace(" ,", ","), lead.format(n=n, amt=amt, due=rec.get("due"), days=days),
                                       personal_line(str(rec.get("customer") or ""), ctx["brain"]), f"How to pay: {pay_line}.", ask.format(by=by), "Thanks,\nCharlie") if x)
        reason = f"Touch {touch} because the invoice is {days} days late and the last touch drafted was {last or 'none'}."
        k.write(ctx, f"finance/collections/drafts/{n}-touch-{touch}.md", f"Subject: Invoice {n}: {name}\n\n{body}\n\nReason chosen: {reason}\nNot sent. Charlie sends and sets the log row to sent.")
        log.append({"invoice": n, "touch": touch, "drafted": today.isoformat(), "status": "drafted"})
        made.append(f"{n} touch {touch}")
    if made:
        k.write(ctx, "finance/collections/log.json", log)
    if not (made or briefs):
        return {"skipped": "no late invoice needs a touch" + (f" (held for promised dates: {', '.join(held)})" if held else "")}
    return {"summary": f"Drafted {', '.join(made) or 'no reminders'}; decision briefs: {', '.join(briefs) or 'none'}. Charlie sends each one.", "flag": "caution" if briefs else "ok"}


if __name__ == "__main__":
    k.run(main)
