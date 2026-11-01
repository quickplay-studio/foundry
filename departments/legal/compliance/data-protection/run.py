"""Data Protection: GitHub implementation of departments/legal/compliance/data-protection/SKILL.md.

Drafts the data map, lawful bases, ICO fee answer, DPIA screen, processors, retention and rights plan from the brain.
Placeholders only go to the free model (step 10). ICO pages are read and dated; a failed read or model is caution.
Not legal advice.
"""
import datetime as dt
import json
import re
from urllib.parse import urlparse

from foundry import jobkit as k

ICO = "https://ico.org.uk/for-organisations/"
G = "uk-gdpr-guidance-and-resources/"
PAGES = {
    "fee": ("ICO data protection fee", ICO + "data-protection-fee/", "ICO data protection fee how much do I need to pay"),
    "basis": ("ICO lawful basis guide", ICO + G + "lawful-basis/a-guide-to-lawful-basis/", "ICO guide to lawful basis"),
    "dpia": ("ICO DPIA guidance", ICO + G + "accountability-and-governance/data-protection-impact-assessments-dpias/", "ICO when do we need to do a DPIA"),
    "pecr": ("ICO cookies and similar technologies", ICO + "direct-marketing-and-privacy-and-electronic-communications/guide-to-pecr/cookies-and-similar-technologies/", "ICO PECR cookies and similar technologies guidance"),
    "transfers": ("ICO international transfers", ICO + G + "international-transfers/", "ICO international transfers UK GDPR IDTA addendum"),
    "children": ("ICO Children's code", ICO + G + "childrens-information/childrens-code-guidance-and-resources/", "ICO children's code guidance"),
    "duaa": ("Data (Use and Access) Act 2025", "https://www.legislation.gov.uk/ukpga/2025/18/contents", "Data (Use and Access) Act 2025 changes to UK GDPR ICO"),
}
HOSTS = (".ico.org.uk", ".gov.uk")
BASES = ("contract", "legitimate interests", "consent", "legal obligation")
# trigger words, data type, category, purpose, lawful basis, retention, delete trigger
SKELETON = [
    (("sign up", "account", "login", "log in", "email", "register", "user"), "Account name and email", "identifiers and contact details", "Create and run the account", "contract", "Life of the account", "30 days after account closure"),
    (("pay", "subscri", "checkout", "stripe", "paddle", "billing", "price"), "Payment references and invoices", "payment references", "Take payment and keep tax records", "legal obligation", "6 years after the financial year", "End of the tax record period"),
    (("analytics", "usage", "track", "posthog", "telemetry"), "Device and usage data", "device and usage data", "Keep the service secure and see basic use", "legitimate interests", "12 months", "Rolling deletion"),
    (("cookie", "advert", "retarget", "marketing", "newsletter"), "Marketing contact and cookie choices", "marketing and cookies", "Marketing and non-essential cookies", "consent", "Until consent is withdrawn", "Withdrawal or 24 months of inactivity"),
    (("post", "upload", "note", "content", "comment", "message", "chat", "profile"), "Content users enter", "user content", "Provide the feature the user asked for", "contract", "Life of the account", "User deletes it or closes the account"),
    (("support", "contact us", "help"), "Support messages", "contact details", "Answer support requests", "legitimate interests", "24 months", "Ticket closed for 24 months"),
]
LOGS = ("Server and security logs, including IP address", "device and usage data", "Keep the service secure", "legitimate interests", "30 days", "Rolling deletion")
HOSTING = {"github": "GitHub", "netlify": "Netlify", "vercel": "Vercel", "firebase": "Google Firebase", "supabase": "Supabase", "aws": "Amazon Web Services", "stripe": "Stripe", "paddle": "Paddle",
           "posthog": "PostHog", "mailchimp": "Mailchimp", "resend": "Resend", "sendgrid": "SendGrid", "gemini": "Google Gemini API", "openai": "OpenAI", "anthropic": "Anthropic"}
SPECIAL = r"health|medical|biometric|fingerprint|ethnic|racial|religio|belief|politic|sex life|sexual|trade union|genetic|criminal|conviction|disabilit"
ORDER = {"clear": 0, "caution": 1, "stop": 2}
NOTICE = "Not legal advice. Drafts are checked by Charlie or a solicitor before use."


def worse(a, b):
    return a if ORDER.get(a, 1) >= ORDER.get(b, 1) else b


def rows_of(v):
    return [r for r in v if isinstance(r, dict)] if isinstance(v, list) else []


def scrub(t):
    return re.sub(r"\+?\d[\d\s().-]{8,}\d", "[number]", re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[email]", str(t)))


def read_pages(sources):
    out, day = {}, dt.date.today().isoformat()
    for key, (label, url, query) in sources.items():
        text = k.fetch(url, 30000)
        if len(text) < 200:
            for r in k.search(query, 3):
                u = r.get("url", "")
                if ("." + urlparse(u).netloc.lower()).endswith(HOSTS):
                    url, text = u, k.fetch(u, 30000)
                    if len(text) >= 200:
                        break
        ok = len(text) >= 200
        out[key] = {"label": label, "url": url, "read_on": day, "ok": ok, "text": text if ok else ""}
    return out


def figures(text, n=1500):
    parts = re.split(r"(?<=[.!?])\s+|\n", text)
    return " ".join(p.strip() for p in parts if "£" in p or "tier" in p.lower())[:n]


def route(location):
    loc = str(location).lower()
    if not loc or loc in ("unknown", "stub"):
        return "location unknown: confirm where the data goes"
    if re.search(r"\buk\b|united kingdom|britain|england", loc):
        return "none needed (UK)"
    if re.search(r"\beu\b|eea|europe|ireland|germany|france|netherlands", loc):
        return "UK adequacy regulations for the EEA (confirm in current ICO guidance)"
    if re.search(r"\bus\b|usa|united states|america", loc):
        return "UK-US data bridge if the provider is certified, else the IDTA or UK Addendum"
    return "IDTA or UK Addendum unless an adequacy route applies"


def main(ctx):
    idea, brain = ctx["idea"], ctx["brain"]
    day = dt.date.today().isoformat()
    facts = scrub(json.dumps({key: idea.get(key) for key in ("title", "kind", "problem", "who", "mvp", "money", "channels", "note")}, ensure_ascii=False))
    text = (facts + " " + scrub(brain)).lower()
    rs = k.read(ctx, "clear/regulatory-screen.json")
    rs = rs if isinstance(rs, dict) else None
    area = {str(a.get("area", "")): str(a.get("flag", "caution")) for a in rows_of(rs.get("areas"))} if rs else {}
    pages = read_pages(PAGES)
    prompt = (
        "You are the data protection check of a UK solo founder's AI workforce. Not legal advice. Placeholders only, no real personal data. "
        "From the venture below list every kind of personal data the product will hold or send. Use lawful bases contract, legitimate interests, consent or legal obligation; "
        "consent only for marketing and non-essential cookies, never for everything. Give legitimate interests a one-line balancing note. "
        "Return JSON only: {\"data\": [{\"data_type\": \"...\", \"category\": \"...\", \"purpose\": \"...\", \"source\": \"...\", \"who_sees\": \"...\", \"stored\": \"...\", \"processor\": \"...\", "
        "\"lawful_basis\": \"...\", \"balancing_note\": \"...\", \"special_category\": false, \"retention\": \"...\", \"delete_trigger\": \"...\"}], "
        "\"processors\": [{\"name\": \"...\", \"role\": \"...\", \"location\": \"...\", \"data\": \"...\"}], \"children_likely\": false, \"marketing\": false, \"cookies\": false, "
        "\"special_category_found\": false, \"profiling_or_tracking\": false, \"large_scale\": false, "
        "\"fee\": {\"applies\": \"likely|no|unclear\", \"tier\": \"...\", \"amount\": \"...\", \"quote\": \"exact words from the fee page\", \"reason\": \"...\"}, "
        "\"dpia_draft\": [\"...\"], \"flag\": \"clear|caution|stop\", \"reason\": \"<two sentences>\"}\n\nVENTURE\n" + facts + "\n\nBRAIN\n" + scrub(brain)[:3500]
        + "\n\nFEE PAGE FIGURES\n" + (figures(pages["fee"]["text"]) if pages["fee"]["ok"] else "not read"))
    ans = k.ask(prompt)
    ans = ans if isinstance(ans, dict) else {}
    why = []
    rows = []
    for r in rows_of(ans.get("data")):
        t = {f: str(r.get(f, ""))[:160] for f in ("data_type", "category", "purpose", "source", "who_sees", "stored", "processor", "lawful_basis", "balancing_note", "retention", "delete_trigger")}
        t["special_category"] = r.get("special_category") is True
        b = t["lawful_basis"].lower()
        if b not in BASES or (b == "consent" and not re.search(r"market|cookie|newsletter|advert|non-essential|tracking", (t["purpose"] + t["category"]).lower())):
            t["lawful_basis"] = "to confirm"
            why.append(f"lawful basis for {t['data_type'][:40]} needs Charlie")
        rows.append(t)
    if not rows:
        why.append("no usable model data map: skeleton from brain keywords")
        for words, dtype, cat, purpose, basis, keep, trig in SKELETON:
            if any(w in text for w in words):
                rows.append({"data_type": dtype, "category": cat, "purpose": purpose, "source": "the user", "who_sees": "Charlie", "stored": "to confirm", "processor": "to confirm", "lawful_basis": basis,
                             "balancing_note": "", "special_category": False, "retention": keep, "delete_trigger": trig})
        dtype, cat, purpose, basis, keep, trig = LOGS
        rows.append({"data_type": dtype, "category": cat, "purpose": purpose, "source": "the browser", "who_sees": "Charlie", "stored": "to confirm", "processor": "to confirm", "lawful_basis": basis,
                     "balancing_note": "", "special_category": False, "retention": keep, "delete_trigger": trig})
    for t in rows:
        if t["lawful_basis"] == "legitimate interests" and not t["balancing_note"]:
            t["balancing_note"] = "Default note, Charlie to confirm: needed for " + t["purpose"].lower() + "; no less intrusive way; low impact; users can object."
        t["retention"] = t["retention"] or "to set"
        t["delete_trigger"] = t["delete_trigger"] or "to set"
    procs = [{f: str(p.get(f, ""))[:120] for f in ("name", "role", "location", "data")} for p in rows_of(ans.get("processors"))]
    named = {p["name"].lower() for p in procs}
    procs += [{"name": n, "role": "processor named in the brain", "location": "", "data": "to confirm"} for w, n in HOSTING.items() if w in text and n.lower() not in named]
    for p in procs:
        p["transfer_route"] = route(p["location"])
        p["terms_checked"] = False
    special = ans.get("special_category_found") is True or any(r["special_category"] for r in rows) or bool(re.search(SPECIAL, text))
    children = ans.get("children_likely") is True or bool(re.search(r"\bkids?\b|child|teen|school|under.?18", text)) or any(a.startswith("Children") and f != "clear" for a, f in area.items())
    track = ans.get("profiling_or_tracking") is True or bool(re.search(r"profil|location|tracking", text))
    triggers = [n for n, on in (("special category data", special), ("children", children), ("profiling or tracking", track), ("large-scale processing", ans.get("large_scale") is True)) if on]
    flag = "clear"
    unread = [pages[x]["label"] for x in ("fee", "basis", "dpia") + (("children",) if children else ()) + (("pecr",) if ans.get("cookies") is True or "cookie" in text else ()) if not pages[x]["ok"]]
    if unread:
        flag = "caution"
        why.append("ICO pages not read: " + ", ".join(unread))
    if not ans or not rows_of(ans.get("data")):
        flag = "caution"
    if rs is None:
        flag = "caution"
        why.append("clear/regulatory-screen.json missing, so children and special category flags are unchecked")
    for a, f in area.items():
        if a.startswith(("Children", "Special category")) and f != "clear":
            flag = worse(flag, f)
    if special:
        flag = worse(flag, "caution")
        why.append("special category data possible: UK GDPR Article 9 needs a further condition; tell the regulatory screen")
    if "special category data" in triggers and len(triggers) > 1:
        flag = "stop"
        why.append("DPIA triggers include special category data plus " + ", ".join(t for t in triggers if t != "special category data"))
    elif triggers:
        flag = worse(flag, "caution")
        why.append("DPIA needed: " + ", ".join(triggers))
    mflag = str(ans.get("flag", "caution")).lower()
    flag = worse(flag, "caution" if mflag in ("caution", "stop") else "clear")  # the model's own flag raises to caution at most: stops come from the rules above
    fee = ans.get("fee") if isinstance(ans.get("fee"), dict) else {}
    ftext = pages["fee"]["text"]
    amount = str(fee.get("amount", ""))
    shown = re.sub(r"\s+", " ", ftext).lower()
    fee_ok = pages["fee"]["ok"] and bool(amount.strip()) and bool(fee.get("quote")) and re.sub(r"\s+", " ", str(fee["quote"])).strip().lower() in shown and amount.replace("£", "") in ftext
    applies = str(fee.get("applies", "unclear")).lower()
    applies = applies if applies in ("likely", "no", "unclear") else "unclear"
    if applies == "no":
        why.append("model says no ICO fee: Charlie runs the ICO self-assessment before relying on it")
        flag = worse(flag, "caution")
    fee_answer = {"applies": applies, "tier": str(fee.get("tier", ""))[:80] if fee_ok else "not confirmed from the page", "amount": amount if fee_ok else "not confirmed from the page",
                  "source": pages["fee"]["url"], "read_on": pages["fee"]["read_on"], "reason": str(fee.get("reason", ""))[:200]}
    if not fee_ok or applies == "unclear":
        why.append("ICO fee answer or amount not confirmed from the page")
    if any("to set" in (r["retention"], r["delete_trigger"]) for r in rows):
        why.append("retention or delete trigger missing for some data")
    if why:
        flag = worse(flag, "caution")
    dpia = [str(x)[:200] for x in (ans.get("dpia_draft") if isinstance(ans.get("dpia_draft"), list) else [])] if triggers else []
    if triggers and not dpia:
        dpia = ["Describe the processing and its purpose (placeholders only)", "Necessity and proportion: why this data, nothing less", "Risks to people: " + ", ".join(triggers), "Measures: minimise, encrypt, delete on trigger, human review", "Charlie or an adviser signs off"]
    reason = "; ".join(why) or str(ans.get("reason", ""))[:300] or "Data map drafted and every required ICO page read."
    sources = [f"- {p['label']}: {p['url']} (read {p['read_on']})" if p["ok"] else f"- NOT READ: {p['label']}, {p['url']} (tried {p['read_on']})" for p in pages.values()]
    cell = lambda v: str(v).replace("|", "/").replace("\n", " ")
    lines = [f"FLAG: {flag}", "", reason, "", NOTICE, "", "Drafted from the brain with placeholders only; no real personal data was sent to a model.", "",
             "## Data map", "| Data | Purpose | Source | Who sees | Stored | Processor |", "|---|---|---|---|---|---|",
             *[f"| {cell(t['data_type'])} | {cell(t['purpose'])} | {cell(t['source'])} | {cell(t['who_sees'])} | {cell(t['stored'])} | {cell(t['processor'])} |" for t in rows], "",
             "## Lawful basis per purpose", "| Purpose | Basis | Note |", "|---|---|---|", *[f"| {cell(t['purpose'])} | {t['lawful_basis']} | {cell(t['balancing_note'])} |" for t in rows], "",
             "## Cookies and marketing (PECR)", "- Non-essential cookies and marketing email or SMS need consent, with soft opt-in limits for email; every message carries an unsubscribe. Read the ICO page dated below.", "",
             "## ICO fee", f"- Applies: {applies}. Tier: {fee_answer['tier']}. Amount: {fee_answer['amount']}. Read {fee_answer['read_on']} at {fee_answer['source']}.",
             "- Charlie runs the ICO self-assessment on that page and pays if due; nothing is paid before revenue without his say.", "",
             "## DPIA screen", f"- Triggers: {', '.join(triggers) or 'none found'}.", *[f"- {x}" for x in dpia], "",
             "## Processors and transfers", *[f"- {p['name']}: {p['role']}; {p['location'] or 'location unknown'}; route: {p['transfer_route']}; terms checked: no, Charlie confirms" for p in procs], "",
             "## Retention schedule", *[f"- {t['data_type']}: kept {t['retention']}; delete trigger: {t['delete_trigger']}" for t in rows], "",
             "## Rights and breach plan", "- Access, deletion and export requests: answer within one month; log each one.", "- Breach: tell the ICO within 72 hours if there is a risk to people; keep a breach log.",
             "- Children: ICO Children's code standards apply and consent age is 13 (DPA 2018 s.9)." if children else "- No under-18 users expected; confirm.",
             "- Check the Data (Use and Access) Act 2025 page below for changes that apply.", "", "## Sources read", *sources, "", f"Checked on {day}."]
    k.write(ctx, "clear/data-protection.md", "\n".join(lines))
    k.write(ctx, "clear/data-map.json", {"flag": flag, "notice": NOTICE, "reason": reason, "checked_on": day, "rows": rows, "processors": procs,
                                         "transfers": [{"processor": p["name"], "location": p["location"], "route": p["transfer_route"]} for p in procs if p["location"]],
                                         "ico_fee": fee_answer, "dpia": {"required": bool(triggers), "triggers": triggers}, "children_likely": children, "special_category": special,
                                         "sources_read": [{"label": p["label"], "url": p["url"], "read_on": p["read_on"], "ok": p["ok"]} for p in pages.values()], "incomplete": not rows_of(ans.get("data"))})
    return {"summary": f"Data protection: {flag}. {reason}"[:300], "flag": flag}


if __name__ == "__main__":
    k.run(main)
