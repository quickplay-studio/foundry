"""Bank and Payments Setup: GitHub implementation of departments/legal/formation/bank-and-payments-setup/SKILL.md.

Reads each provider's pricing page fresh (URL and date recorded), has the free model pull the fees out, checks each quote
appears on the page, and works out cost at volume in code. Candidates only, never a bank recommendation. It never opens an
account, enters a login or holds a card: it writes the brief for Charlie. Not legal advice.
"""
import datetime as dt
import json
import re
from urllib.parse import urlparse

from foundry import jobkit as k

PAGES = {  # label, url, search query, official hosts, word the page must contain
    "apple": ("Apple App Store Small Business Program", "https://developer.apple.com/app-store/small-business-program/", "Apple App Store Small Business Program commission", (".apple.com",), "commission"),
    "google": ("Google Play service fees", "https://support.google.com/googleplay/android-developer/answer/112622", "Google Play service fees subscriptions 15%", (".google.com",), "fee"),
    "stripe": ("Stripe UK pricing", "https://stripe.com/gb/pricing", "Stripe UK pricing card payments", (".stripe.com",), "card"),
    "paypal": ("PayPal UK business fees", "https://www.paypal.com/uk/business/paypal-business-fees", "PayPal UK business fees", (".paypal.com",), "fee"),
    "gocardless": ("GoCardless UK pricing", "https://gocardless.com/en-gb/pricing/", "GoCardless UK pricing direct debit", (".gocardless.com",), "debit"),
    "paddle": ("Paddle pricing", "https://www.paddle.com/pricing", "Paddle merchant of record pricing", (".paddle.com",), "paddle"),
    "appledev": ("Apple Developer Program fee", "https://developer.apple.com/programs/enroll/", "Apple Developer Program annual membership fee", (".apple.com",), "membership"),
    "googledev": ("Google Play developer registration fee", "https://support.google.com/googleplay/android-developer/answer/6112435", "Google Play developer registration fee", (".google.com",), "fee"),
    "fscs": ("FSCS bank protection limit", "https://www.fscs.org.uk/what-we-cover/banks-building-societies/", "FSCS deposit protection limit banks building societies", (".fscs.org.uk",), "protect"),
    "starling": ("Starling business account", "https://www.starlingbank.com/business-account/", "Starling business account fees", (".starlingbank.com",), "business"),
    "monzo": ("Monzo Business", "https://monzo.com/business-banking/", "Monzo business account fees", (".monzo.com",), "business"),
    "tide": ("Tide business account", "https://www.tide.co/", "Tide business account fees", (".tide.co",), "business"),
}
REGULATED = r"marketplace|wallet|escrow|split payment|hold(s|ing)? (customer )?(funds|money)|pool(s|ed|ing)? (funds|money)|payouts?|pay out|stored value|e-money|virtual card|prepaid|issues? cards?|money transfer|send money|remittance|payment initiation|peer.to.peer pay"
CRITERIA = ["Eligible for the chosen structure", "Free tier or a free first period (read the current terms)", "FSCS protection, or safeguarding if it is an e-money account", "Can receive payouts from the chosen provider", "Terms on business use of a personal account"]
IDENTITY = ["Proof of identity and address", "A description of the business and expected turnover", "Charlie opens and verifies every account himself; the job never creates one or enters credentials"]
NOTICE = "Not legal advice. Drafts are checked by Charlie or a solicitor before use."


def norm(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def num(v):
    try:
        return float(str(v).replace(",", "").replace("£", "").replace("%", "")) if v not in (None, "") and not isinstance(v, bool) else None
    except ValueError:
        return None


def ground(v, text):
    return v is not None and any(re.search(r"(?<![\d.,])" + re.escape(f) + r"(?!\d)", text) for f in {f"{v:,.0f}", f"{v:g}", f"{v:,.2f}"})


def zero(s):
    return bool(re.match(r"^(none|nil|no\b|free|£?0(\.0+)?\b)", norm(s)))


def read_pages(keys):
    out, day = {}, dt.date.today().isoformat()
    for key in keys:
        label, url, query, hosts, word = PAGES[key]
        text = k.fetch(url, 30000)
        if len(text) < 200:
            for r in k.search(query, 3):
                u = r.get("url", "")
                if ("." + urlparse(u).netloc.lower()).endswith(hosts):
                    url, text = u, k.fetch(u, 30000)
                    if len(text) >= 200:
                        break
        ok = len(text) >= 200 and word in text.lower()
        out[key] = {"label": label, "url": url, "read_on": day, "ok": ok, "text": text if ok else ""}
    return out


def figures(text, n=1100):
    parts = re.split(r"(?<=[.!?])\s+|\n", text)
    return " ".join(p.strip() for p in parts if "£" in p or "%" in p or "free" in p.lower())[:n]


def main(ctx):
    idea, brain = ctx["idea"], ctx["brain"]
    day = dt.date.today().isoformat()
    facts = json.dumps({key: idea.get(key) for key in ("title", "kind", "problem", "who", "mvp", "money", "channels")}, ensure_ascii=False)
    text = (facts + " " + brain).lower()
    entity = (k.read(ctx, "clear/entity-and-structure.md") or "").split("\n", 1)[0].strip() or "no structure brief yet"
    ios, droid = bool(re.search(r"\bios\b|iphone|app store|apple", text)), bool(re.search(r"android|google play|play store", text))
    store_only = (ios or droid) and not re.search(r"\bweb\b|website|checkout|stripe|paypal|invoice", text)
    skip = ("apple", "appledev") if droid and not ios else ("google", "googledev") if ios and not droid else ()
    keys = [x for x in PAGES if x not in skip]
    pages = read_pages(keys)
    kw = sorted({m.group(0) for m in re.finditer(REGULATED, text)})
    ans = k.ask(
        "You extract payment fees for a UK solo founder. Not legal advice. Use only the extracts; a number only if stated, else null; quote the exact words that show the fee. "
        "holds_or_moves_money is yes if the venture holds, pools or transfers other people's money.\nReturn JSON only: {\"holds_or_moves_money\": \"yes|no|unclear\", \"price_gbp\": 0, "
        "\"providers\": [{\"key\": \"<page key>\", \"name\": \"...\", \"setup\": \"...\", \"monthly\": \"...\", \"per_txn\": \"...\", \"pct\": 0, \"fixed_gbp\": 0, \"payout\": \"...\", \"vat\": \"...\", \"eligible\": \"...\", \"quote\": \"...\"}], "
        "\"banks\": [{\"key\": \"<page key>\", \"name\": \"...\", \"monthly\": \"...\", \"eligible\": \"...\", \"quote\": \"...\"}], \"fscs_limit\": \"...\", "
        "\"costs\": [{\"item\": \"...\", \"amount\": \"...\", \"frequency\": \"...\", \"quote\": \"...\"}], \"reason\": \"<one sentence>\"}\n\nVENTURE\n" + facts + "\n\nBRAIN\n" + brain[:2000]
        + "\n\nPAGES\n" + "\n".join(f"[{key}] {figures(p['text'])}" for key, p in pages.items() if p["ok"]))
    ans = ans if isinstance(ans, dict) else {}
    why, flag = [], "clear"
    unread = [p["label"] for p in pages.values() if not p["ok"]]
    if not ans:
        why.append("no free model answered, so no fees were extracted")
    if unread:
        why.append("pages not read: " + ", ".join(unread))
    mv = str(ans.get("holds_or_moves_money", "unclear")).lower()
    if kw or mv == "yes":
        flag = "stop"
        why.insert(0, "money handling looks regulated (" + (", ".join(kw[:3]) or "model says it holds or moves customer money") + "): payment services or e-money rules apply, send to regulatory-screen")
    elif mv != "no":
        why.append("whether the venture holds or moves customer money is unconfirmed")
    price = num(ans.get("price_gbp"))
    price = price if ground(price, facts + brain) else None
    provs = []
    for p in ans.get("providers", []) if isinstance(ans.get("providers"), list) else []:
        if not isinstance(p, dict) or p.get("key") not in pages:
            continue
        pg = pages[p["key"]]
        t = {f: str(p.get(f, ""))[:90] for f in ("name", "setup", "monthly", "per_txn", "payout", "vat", "eligible")}
        t["verified"] = pg["ok"] and bool(p.get("quote")) and norm(p["quote"]) in norm(pg["text"])
        t["pct"], t["fixed"] = (num(p.get("pct")), num(p.get("fixed_gbp")))
        t["pct"], t["fixed"] = (t["pct"] if ground(t["pct"], pg["text"]) else None), (t["fixed"] if ground(t["fixed"], pg["text"]) else None)
        t["fits"] = t["verified"] and zero(t["setup"]) and zero(t["monthly"])
        t["store"] = p["key"] in ("apple", "google")
        t["key"] = p["key"]
        provs.append(t)
    usable = [p for p in provs if p["fits"] and (p["pct"] is not None or p["fixed"] is not None) and (not store_only or p["store"])]
    per_sale = lambda p: (price or 0) * (p["pct"] or 0) / 100 + (p["fixed"] or 0)
    usable.sort(key=per_sale)
    if not usable:
        why.append("no verified route with no set-up and no monthly fee: any workable route costs money up front or monthly, or could not be read")
    if any(not p["verified"] for p in provs) or not provs:
        why.append("some fees are unverified against the page")
    if not price:
        why.append("price not stated in the brain, so cost at volume is not computed")
    if why and flag == "clear":
        flag = "caution"
    banks = [b for b in ans.get("banks", []) if isinstance(b, dict) and b.get("key") in pages] if isinstance(ans.get("banks"), list) else []
    costs = [c for c in ans.get("costs", []) if isinstance(c, dict)] if isinstance(ans.get("costs"), list) else []
    seen = " ".join(norm(p["text"]) for p in pages.values())
    fscs_digits = re.sub(r"[^\d]", "", str(ans.get("fscs_limit", "")))
    fscs = str(ans.get("fscs_limit"))[:40] if fscs_digits and pages["fscs"]["ok"] and ground(float(fscs_digits), pages["fscs"]["text"]) else "not confirmed from the page"
    cell = lambda v: re.sub(r"\s+", " ", str(v or "")).strip().replace("|", "/") or "not read"
    reason = "; ".join(why) or "Routes verified on pages read; at least one needs no up-front or monthly cost."
    best, alt = (usable + [None, None])[:2]
    brief = [f"- Account owner: per the structure brief ({entity}); Charlie supplies the legal name.",
             f"- Recommended route to verify first: {best['name']} ({best['key']})." if best else "- No route recommended: nothing verified with zero set-up and monthly cost.",
             f"- Alternative: {alt['name']}." if alt else "- Alternative: none verified.",
             "- Cost at volume (fees only):" if best and price else "- Cost at volume: not computed.",
             *([f"  - {n} sales a month at {price:g} pounds: {n * per_sale(p):,.2f} pounds with {p['name']}" for p in (best, alt) if p for n in (10, 100, 1000)] if best and price else []),
             "- Charlie opens first: the business account, then the chosen provider. Everything else waits for revenue."]
    lines = [f"FLAG: {flag}", "", reason, "", NOTICE, "", "## Brief", *brief, "", "## Comparison (candidates to verify, not a recommendation)", "| Provider | Set-up | Monthly | Per transaction | Payout | VAT | Eligible | Checked against page |", "|---|---|---|---|---|---|---|---|",
             *([f"| {cell(p['name'])} | {cell(p['setup'])} | {cell(p['monthly'])} | {cell(p['per_txn'])} | {cell(p['payout'])} | {cell(p['vat'])} | {cell(p['eligible'])} | {'yes' if p['verified'] else 'NO'} |" for p in provs] or ["| none read | | | | | | | |"]), "",
             "## Business bank criteria", *[f"- {c}" for c in CRITERIA], f"- FSCS limit: {fscs}.", "- FCA Register: Charlie checks any named provider there; it cannot be read by the job.",
             *[f"- Option to verify: {cell(b.get('name'))}; monthly {cell(b.get('monthly'))}; eligible {cell(b.get('eligible'))}" + ("" if b.get("quote") and norm(b["quote"]) in norm(pages[b["key"]]["text"]) else " (unverified against the page)") for b in banks[:3]], "", "## Identity checks Charlie must pass", *[f"- {i}" for i in IDENTITY], "",
             "## Costs needing Charlie's approval before any spend", *[f"- {cell(c.get('item'))}: {cell(c.get('amount'))} {cell(c.get('frequency'))}" + ("" if c.get("quote") and norm(c["quote"]) in seen else " (unverified, check before approving)") for c in costs], "- Domain name: price not read, check a registrar.",
             "", "## On hold until revenue", "- Every fee, subscription and card; nothing is paid or put on a card before the first pound of revenue.", "", "## Sources read",
             *[f"- {p['label']}: {p['url']} (read {p['read_on']})" if p["ok"] else f"- NOT READ: {p['label']}, {p['url']} (tried {p['read_on']})" for p in pages.values()], "", f"Checked on {day}."]
    k.write(ctx, "clear/bank-and-payments.md", "\n".join(lines))
    return {"summary": f"Bank and payments: {flag}. {reason}"[:300], "flag": flag}


if __name__ == "__main__":
    k.run(main)
