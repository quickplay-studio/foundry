"""Consumer Law Check: GitHub implementation of departments/legal/compliance/consumer-law-check/SKILL.md.

Reads the instruments on legislation.gov.uk and the subscription position on gov.uk, dated. The rules list lives
in code so runs repeat; the free model maps it to the product. A failed read or a silent model is caution, never clear.
Not legal advice.
"""
import datetime as dt
import json
import re
from urllib.parse import urlparse

from foundry import jobkit as k

LEG = "https://www.legislation.gov.uk/"
SOURCES = {
    "cra": ("Consumer Rights Act 2015, digital content", LEG + "ukpga/2015/15/part/1/chapter/3", "Consumer Rights Act 2015 digital content legislation.gov.uk"),
    "cra2": ("Consumer Rights Act 2015, Part 2", LEG + "ukpga/2015/15/part/2", "Consumer Rights Act 2015 Part 2 unfair terms legislation.gov.uk"),
    "ccr": ("Consumer Contracts Regulations 2013", LEG + "uksi/2013/3134/contents", "Consumer Contracts Information Cancellation and Additional Charges Regulations 2013"),
    "dmcc": ("Digital Markets, Competition and Consumers Act 2024", LEG + "ukpga/2024/13/contents", "Digital Markets Competition and Consumers Act 2024 legislation.gov.uk"),
    "subs": ("gov.uk subscription regime position", "", "gov.uk DMCC Act subscription contracts regime commencement date"),
    "ecr": ("Electronic Commerce Regulations 2002", LEG + "uksi/2002/2013/regulation/6", "Electronic Commerce (EC Directive) Regulations 2002 regulation 6"),
    "adr": ("ADR for Consumer Disputes Regulations 2015", LEG + "uksi/2015/542/contents", "Alternative Dispute Resolution for Consumer Disputes Regulations 2015"),
    "pmo": ("Price Marking Order 2004", LEG + "uksi/2004/102/contents", "Price Marking Order 2004 legislation.gov.uk"),
}
# id, rule, source key, word the page must contain, what the product must do, what it affects
RULES = [
    ("quality", "Digital content is of satisfactory quality, fit for purpose and as described; repair, replacement and refund cannot be excluded (CRA 2015 ss.34 to 47)", "cra", "digital content", "Describe the product accurately; no term limits these rights", "Listing, terms"),
    ("unfair", "Terms are fair and in plain, intelligible wording; check the grey list (CRA 2015 Part 2)", "cra2", "unfair", "Test each term against the grey list; no one-sided variation, penalty or exclusion terms", "Terms"),
    ("info", "Pre-contract information and a 14-day right to cancel for distance sales (CCR 2013)", "ccr", "cancel", "Show characteristics, total price, trader identity and cancellation rights before payment; keep the record", "Checkout, confirmation email"),
    ("digital", "Digital content: the right to cancel is lost only after express consent and acknowledgement before download or streaming starts (CCR 2013)", "ccr", "cancel", "Tick-box consent and acknowledgement before access; store both", "Checkout"),
    ("services", "A service started within the cancellation period needs an express request, and a proportionate payment if the customer cancels (CCR 2013)", "ccr", "cancel", "Ask for the express request; compute the proportionate charge", "Checkout, refunds"),
    ("practices", "No unfair commercial practices, drip pricing, fake or incentivised reviews or fake urgency (DMCC Act 2024; CMA fines up to 10 percent of global turnover)", "dmcc", "consumer", "Full price up front; no invented reviews, scarcity or countdowns", "Landing page, checkout"),
    ("subscription", "Subscription contracts regime: pre-contract information, reminder notices, easy exit, cooling off (confirm commencement)", "subs", "subscription", "Apply from the commencement date read below; exit as easy as sign-up", "Checkout, account, emails"),
    ("price", "Price including VAT up front, no hidden fees, trial conversion, renewal price and date stated before payment", "dmcc", "consumer", "State price, VAT, trial end, renewal price and renewal date on the payment screen", "Pricing page, checkout"),
    ("goods", "Price Marking Order 2004 for any goods", "pmo", "price", "Show the selling price of goods in pounds, including VAT", "Product pages"),
    ("trader", "Trader details: name, geographic address, email, and company or VAT number where one applies (ECR 2002; Companies Act 2006 for a company)", "ecr", "information", "Put the details on the site, in the terms and in the receipt", "Footer, terms"),
    ("adr", "Say whether you will use an ADR provider for consumer disputes (ADR Regulations 2015)", "adr", "dispute", "Add the ADR statement and a complaints route", "Terms, help page"),
    ("refund", "Refunds generally within 14 days of the cancellation; a clear complaints route", "ccr", "cancel", "Refund by the original method within 14 days; publish the route", "Refund policy, support"),
    ("store", "Where Apple or Google take payment, refunds and renewals, do not promise what the store controls", "", "", "Point to the store for billing and refunds; promise nothing the store decides", "Listing, terms"),
]
WORDING = ["Total price including VAT shown before the pay button", "Trial length, the price after the trial and the first charge date stated in plain words",
           "Renewal price, billing period and renewal date stated before payment", "Cancel button in the account page, no more steps than sign-up",
           "Digital content: tick-box for consent to immediate access and acknowledgement that the cancellation right is lost", "Confirmation email repeats the terms, price and how to cancel",
           "Keep records of consent, acknowledgement, price shown and time for each sale", "Refund promise states the 14 day timing and the method"]
BAD = r"hidden (renewal|fee|charge)|auto-?renew\w* without|no (way to )?cancel\b|cannot cancel|can't cancel|impossible to cancel|non-?cancell?able|fake (review|urgency|testimonial)|countdown timer|drip pric"
ORDER = {"clear": 0, "caution": 1, "stop": 2}
NOTICE = "Not legal advice. Drafts are checked by Charlie or a solicitor before use."


def worse(a, b):
    return a if ORDER.get(a, 1) >= ORDER.get(b, 1) else b


def norm(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def rows_of(v):
    return [r for r in v if isinstance(r, dict)] if isinstance(v, list) else []


def read_pages(sources, hosts=(".gov.uk",)):
    """{key: (label, url, query)} -> {key: {label, url, read_on, ok, text}}; only real page text counts as read."""
    out, day = {}, dt.date.today().isoformat()
    for key, (label, url, query) in sources.items():
        text = k.fetch(url, 30000) if url else ""
        if len(text) < 200:
            for r in k.search(query, 3):
                u = r.get("url", "")
                if ("." + urlparse(u).netloc.lower()).endswith(hosts):
                    url, text = u, k.fetch(u, 30000)
                    if len(text) >= 200:
                        break
        ok = len(text) >= 200
        out[key] = {"label": label, "url": url, "read_on": day, "ok": ok, "text": text if ok else ""}
    return out


def around(text, word, n=900):
    i = text.lower().find(word)
    return re.sub(r"\s+", " ", text[max(0, i - 100):i + n]) if i >= 0 else ""


def main(ctx):
    idea, brain = ctx["idea"], ctx["brain"]
    facts = json.dumps({key: idea.get(key) for key in ("title", "kind", "problem", "who", "mvp", "money", "channels", "note")}, ensure_ascii=False)
    pages = read_pages(SOURCES)
    day = dt.date.today().isoformat()
    audit = k.read(ctx, "audit.json", {}) or {}
    b2b_hint = idea.get("business_model") == "b2b" or (isinstance(audit, dict) and audit.get("business_model") == "b2b")
    needle = {r[2]: r[3] for r in RULES if r[2]}
    excerpts = {key: around(p["text"], needle.get(key, "a"), 700) for key, p in pages.items() if p["ok"] and key != "subs"}
    prompt = (
        "You are the consumer law check of a UK solo founder's AI workforce. Not legal advice. Use only the venture facts and the page extracts below. "
        "Classify the contract and buyer, read the subscription position, and for each rule id say what the product must do and which screen or term it affects. "
        "status is ok, open (a question remains) or breach (the model depends on something unlawful). If both consumers and businesses may buy, buyer is both. "
        "Quote exact words from the subscription page for commenced; if the page does not say, commenced is unclear. "
        "Return JSON only: {\"contract\": \"digital content|digital service|goods|mixed\", \"buyer\": \"consumer|business|both\", \"sold_via\": [\"...\"], \"recurring\": true, "
        "\"subscription_regime\": {\"commenced\": \"yes|no|unclear\", \"date\": \"...\", \"quote\": \"...\"}, "
        "\"rules\": [{\"id\": \"...\", \"must_do\": \"...\", \"affects\": \"...\", \"status\": \"ok|open|breach\"}], \"wording\": [\"...\"], \"open_questions\": [\"...\"], "
        "\"flag\": \"clear|caution|stop\", \"reason\": \"<two sentences>\"}\n\nVENTURE\n" + facts + "\n\nBRAIN\n" + brain[:3500]
        + "\n\nRULE IDS\n" + "\n".join(f"- {r[0]}: {r[1]}" for r in RULES)
        + "\n\nSUBSCRIPTION PAGE\n" + (pages["subs"]["text"][:3000] if pages["subs"]["ok"] else "not read")
        + "\n\nEXTRACTS\n" + "\n".join(f"[{key}] {t}" for key, t in excerpts.items() if t))
    ans = k.ask(prompt)
    ans = ans if isinstance(ans, dict) else {}
    buyer, contract = str(ans.get("buyer", "")).lower(), str(ans.get("contract", "")).lower()
    sub = ans.get("subscription_regime") if isinstance(ans.get("subscription_regime"), dict) else {}
    recurring = ans.get("recurring") is True or bool(re.search(r"subscri|monthly|recurring|renew|trial|per month", facts.lower()))
    goods = contract in ("goods", "mixed")
    need = ["cra", "cra2", "ccr", "dmcc"] + (["subs"] if recurring else []) + (["pmo"] if goods else [])
    reasons, flag = [], "clear"
    unread = [pages[key]["label"] for key in need if not pages[key]["ok"]]
    if unread:
        flag = "caution"
        reasons.append("pages not read: " + ", ".join(unread))
    if not ans:
        flag = "caution"
        reasons.append("no free model answered, so the rules are the generic list, not mapped to the product")
    bad = sorted({m.group(0) for m in re.finditer(BAD, (facts + " " + brain).lower())})
    if bad:
        flag = "stop"
        reasons.append("the brief suggests an unlawful practice: " + ", ".join(bad[:3]))
    quote = str(sub.get("quote", ""))
    grounded = bool(quote) and pages["subs"]["ok"] and norm(quote) in norm(pages["subs"]["text"])
    regime = str(sub.get("commenced", "unclear")).lower() if grounded else "unclear"
    if recurring and regime not in ("yes", "no"):
        flag = worse(flag, "caution")
        reasons.append("subscription regime commencement not confirmed on a page read")
    if b2b_hint and buyer == "business":
        pure = "Classified as a pure business sale, so consumer rules likely do not apply. See contract-drafting. Charlie confirms no consumer can buy."
        lines = [f"FLAG: {worse(flag, 'caution')}", "", pure, "", NOTICE, "", "## Sources read", *source_lines(pages), "", f"Checked on {day}."]
        k.write(ctx, "clear/consumer-law-check.md", "\n".join(lines))
        return {"summary": "Consumer law check: business-only sale, consumer rules likely n/a. " + pure[:120], "flag": worse(flag, "caution")}
    mapped = {str(r.get("id")): r for r in rows_of(ans.get("rules"))}
    table = []
    for rid, rule, key, word, must, affects in RULES:
        if rid == "goods" and not goods or rid == "subscription" and not recurring:
            continue
        m = mapped.get(rid, {})
        p = pages.get(key)
        confirmed = p is None or (p["ok"] and word in p["text"].lower())
        status = str(m.get("status", "open")).lower() if m else "open"
        status = status if status in ("ok", "open", "breach") else "open"
        if not confirmed:
            status = "unconfirmed" if status == "ok" else status
        src = "store terms" if p is None else (f"{p['url']} (read {p['read_on']})" if p["ok"] else "NOT READ")
        table.append((rule, src, str(m.get("must_do") or must)[:220], str(m.get("affects") or affects)[:80], status))
        if status == "breach":
            flag = "stop"
            reasons.append(f"rule {rid} marked breach")
        elif status != "ok":
            flag = worse(flag, "caution")
    n_open = sum(1 for row in table if row[4] not in ("ok", "breach"))
    if n_open:
        reasons.append(f"{n_open} of {len(table)} rules open or unconfirmed")
    questions = [str(q)[:200] for q in (ans.get("open_questions") if isinstance(ans.get("open_questions"), list) else [])]
    if questions:
        flag = worse(flag, "caution")
    mflag = str(ans.get("flag", "caution")).lower()
    flag = worse(flag, mflag if mflag in ORDER else "caution")
    reason = "; ".join(reasons) or str(ans.get("reason", ""))[:300] or "All required pages read and every rule mapped."
    wording = [str(w)[:200] for w in (ans.get("wording") if isinstance(ans.get("wording"), list) else [])] or WORDING
    lines = [f"FLAG: {flag}", "", reason, "", NOTICE, "", "## Classification",
             f"- Contract: {contract or 'unknown'}. Buyer: {buyer or 'unknown'}. Sold via: {', '.join(str(x) for x in ans.get('sold_via', []) if isinstance(x, str)) if isinstance(ans.get('sold_via'), list) else 'unknown'}.",
             f"- Subscription regime commenced: {regime}" + (f" ({sub.get('date', '')}; page said: \"{quote[:160]}\")" if grounded else " (not confirmed from a page)"), "",
             "## Rules list", "| Rule | Source | What the product must do | Affects | Status |", "|---|---|---|---|---|",
             *[("| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in row) + " |") for row in table], "",
             "## Checkout and cancellation wording checklist", *[f"- [ ] {w}" for w in wording], "",
             "## Open questions for Charlie", *([f"- {q}" for q in questions] or ["- none raised: still confirm price, trial, refund policy and the cancellation flow"]), "",
             "## Sources read", *source_lines(pages), "", f"Checked on {day}."]
    k.write(ctx, "clear/consumer-law-check.md", "\n".join(lines))
    return {"summary": f"Consumer law check: {flag}. {reason}"[:300], "flag": flag}


def source_lines(pages):
    return [f"- {p['label']}: {p['url'] or 'no page found'} (read {p['read_on']})" if p["ok"] else f"- NOT READ: {p['label']}, {p['url'] or 'no page found'} (tried {p['read_on']})" for p in pages.values()]


if __name__ == "__main__":
    k.run(main)
