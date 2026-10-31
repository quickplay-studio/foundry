"""Tax Registration: GitHub implementation of departments/legal/formation/tax-registration/SKILL.md.

Builds the dated calendar in code from the deadline rules, then checks each rule's wording and each threshold against
a gov.uk page read (URL and date recorded). Thresholds come from the pages, never from memory. It never logs in,
registers or pays: it writes the checklist and calendar for Charlie. Not legal advice.
"""
import calendar
import datetime as dt
import json
import re
from urllib.parse import urlparse

from foundry import jobkit as k

G = "https://www.gov.uk/"
PAGES = {  # label, url, search query, official hosts, word the page must contain
    "allow": ("Trading allowance", G + "guidance/tax-free-allowances-on-property-and-trading-income", "gov.uk trading allowance tax-free", "trading allowance"),
    "vat": ("VAT registration thresholds", G + "vat-registration-thresholds", "gov.uk VAT registration threshold", "threshold"),
    "vatreg": ("Register for VAT", G + "register-for-vat", "gov.uk register for VAT rolling 12 months 30 days", "30 day"),
    "ico": ("ICO data protection fee", "https://ico.org.uk/for-organisations/data-protection-fee/", "ICO data protection fee", "fee"),
    "st": ("Set up as a sole trader", G + "set-up-sole-trader", "gov.uk set up as a sole trader register for self assessment", "5 october"),
    "sa": ("Self Assessment deadlines", G + "self-assessment-tax-returns/deadlines", "gov.uk self assessment tax return deadlines 31 January", "31 january"),
    "poa": ("Payments on account", G + "understand-self-assessment-bill/payments-on-account", "gov.uk payments on account 31 January 31 July", "31 july"),
    "mtd": ("Making Tax Digital for Income Tax", G + "guidance/use-making-tax-digital-for-income-tax", "gov.uk Making Tax Digital for Income Tax who must sign up thresholds", "making tax digital"),
    "ctreg": ("Register for Corporation Tax", G + "limited-company-formation/register-for-corporation-tax", "gov.uk register for corporation tax within 3 months", "3 months"),
    "ctdead": ("Company Tax Return deadlines", G + "company-tax-returns/deadline", "gov.uk company tax return deadline 12 months", "12 months"),
    "ch": ("Annual accounts for a limited company", G + "prepare-file-annual-accounts-for-limited-company/deadlines", "gov.uk file annual accounts limited company 9 months", "9 months"),
    "cs": ("Confirmation statement", G + "file-your-confirmation-statement-with-companies-house", "gov.uk file confirmation statement Companies House", "confirmation statement"),
    "idv": ("Companies House identity verification", G + "guidance/verify-your-identity-for-companies-house", "Companies House director identity verification", "identity"),
    "paye": ("Register as an employer", G + "register-employer", "gov.uk register as an employer PAYE", "employer"),
}
KEYS = {"hold off": ("st",), "sole trader": ("st", "sa", "poa", "mtd"), "limited company": ("ctreg", "ctdead", "ch", "cs", "idv")}
SOURCES_EXTRA = ("allow", "vat", "vatreg", "ico")
LISTS = {"hold off": ["Records of income and costs for the tax year", "Nothing to register while trading income stays within the allowance"],
         "sole trader": ["National Insurance number", "Government Gateway sign-in (created by Charlie)", "Trading name, start date and address", "Bank details for payments on account", "Record of every sale and cost"],
         "limited company": ["Company number and the authentication code", "Government Gateway sign-in for the company", "Registered office address and director details", "Director identity verification code", "Accounting reference date"]}
ORDER = {"clear": 0, "caution": 1, "stop": 2}
NOTICE = "Not legal advice. Drafts are checked by Charlie or a solicitor before use."


def add_months(d, n):
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    return dt.date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def num(v):
    try:
        return float(str(v).replace(",", "").replace("£", "")) if v not in (None, "") and not isinstance(v, bool) else None
    except ValueError:
        return None


def ground(v, text):
    return v is not None and any(re.search(r"(?<![\d.,])" + re.escape(f) + r"(?!\d)", text) for f in {f"{v:,.0f}", f"{v:.0f}"})


def structure_of(v):
    v = str(v).lower()
    return "hold off" if "hold" in v else "limited company" if re.search(r"limited|ltd|company", v) else "sole trader" if "sole" in v else None


def read_pages(keys):
    out, day = {}, dt.date.today().isoformat()
    for key in keys:
        label, url, query, word = PAGES[key]
        hosts = (".ico.org.uk",) if key == "ico" else (".gov.uk",)
        text = k.fetch(url, 40000)
        if len(text) < 200:
            for r in k.search(query, 3):
                u = r.get("url", "")
                if ("." + urlparse(u).netloc.lower()).endswith(hosts):
                    url, text = u, k.fetch(u, 40000)
                    if len(text) >= 200:
                        break
        ok = len(text) >= 200 and word in text.lower()
        out[key] = {"label": label, "url": url, "read_on": day, "ok": ok, "text": text if ok else ""}
    return out


def parse_date(v):
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def main(ctx):
    idea, brain, board = ctx["idea"], ctx["brain"], ctx["board"] if isinstance(ctx["board"], dict) else {}
    today = dt.date.today()
    day = today.isoformat()
    md = k.read(ctx, "clear/entity-and-structure.md") or ""
    chosen = structure_of(board.get("structure") or board.get("entity") or board.get("chosen_structure") or "")
    recommended = structure_of(md.split("\n", 1)[0].replace("DECISION NEEDED:", "")) if md.startswith("DECISION NEEDED") else None
    structure = chosen or recommended or "hold off"
    why = []
    if not chosen:
        why.append(f"Charlie has not recorded a structure in board.json; assuming {structure} ({'the brief recommends it' if recommended else 'default'})")
    pages = read_pages(list(KEYS[structure]) + list(SOURCES_EXTRA) + (["paye"] if "employ" in brain.lower() else []))
    budget = ctx["budget"] if isinstance(ctx["budget"], dict) else {}
    revenue = num(budget.get("revenue")) or 0.0
    first = parse_date(budget.get("first_sale_date") or idea.get("first_sale_date"))
    ref = first or today
    ty_end = dt.date(ref.year + (0 if ref < dt.date(ref.year, 4, 6) else 1), 4, 5)
    if not first:
        why.append("first trading date not recorded: deadlines assume trading starts in the current tax year or are written as rules")
    facts = json.dumps({key: idea.get(key) for key in ("title", "kind", "money", "channels", "who")}, ensure_ascii=False)
    figs = lambda key: re.sub(r"\s+", " ", " ".join(s for s in re.split(r"(?<=[.!?])\s+|\n", pages[key]["text"]) if "£" in s or "20" in s))[:1500] if key in pages and pages[key]["ok"] else "not read"
    ans = k.ask("You extract UK tax thresholds for a solo founder. Not legal advice. Use only the extracts; a number only if stated, else null.\nReturn JSON only: {\"trading_allowance\": 0, \"vat_registration\": 0, \"vat_deregistration\": 0, "
                "\"mtd_phases\": [{\"from\": \"April 2026\", \"threshold\": 0}], \"merchant_of_record\": false, \"reason\": \"<one sentence>\"}\n\nVENTURE\n" + facts + "\n\n"
                + "\n".join(f"[{key}] {figs(key)}" for key in ("allow", "vat", "vatreg", "mtd")))
    ans = ans if isinstance(ans, dict) else {}
    alltext = " ".join(p["text"] for p in pages.values())
    th = {n: num(ans.get(n)) for n in ("trading_allowance", "vat_registration", "vat_deregistration")}
    th = {n: v for n, v in th.items() if ground(v, alltext)}
    phases = [(str(p.get("from", ""))[:30], num(p.get("threshold"))) for p in (ans.get("mtd_phases") if isinstance(ans.get("mtd_phases"), list) else []) if isinstance(p, dict)]
    phases = [(f, v) for f, v in phases if ground(v, pages["mtd"]["text"] if "mtd" in pages else "") and f.lower() in alltext.lower()]
    if not ans:
        why.append("no free model answered, so thresholds were not extracted")
    for n in ("vat_registration",) + (("trading_allowance",) if structure == "hold off" else ()):
        if n not in th:
            why.append(f"{n.replace('_', ' ')} not confirmed from a page read")
    flag = "clear"
    if "vat_registration" in th and revenue > th["vat_registration"]:
        flag = "stop"
        why.append(f"revenue {revenue:,.0f} is above the VAT threshold {th['vat_registration']:,.0f}: registration may be overdue")
    elif "vat_registration" in th and revenue >= 0.8 * th["vat_registration"]:
        why.append("VAT is within 20 percent of the threshold")
    if structure == "hold off" and "trading_allowance" in th and revenue > th["trading_allowance"]:
        flag = "stop"
        why.append(f"income {revenue:,.0f} is above the trading allowance {th['trading_allowance']:,.0f} but the structure is hold off: registration may be overdue")
    mor = ans.get("merchant_of_record") is True or bool(re.search(r"app store|apple|google play|paddle|lemon squeezy|fastspring", (facts + brain).lower()))
    if mor:
        why.append("merchant of record question is open: record who accounts for VAT and ask an accountant")
    rows = []  # what, due, where, repeats, page key, phrase the page must show
    if structure == "hold off":
        rows.append(("Revisit structure when income nears the trading allowance", "rule: when 12-month income reaches 80 percent of the allowance", "gov.uk", "monthly check", "allow", "trading allowance"))
    if structure == "sole trader":
        rows += [("Register for Self Assessment (UTR)", f"{ty_end.year}-10-05", "HMRC online", "once", "st", "5 october"),
                 ("Online Self Assessment return", f"{ty_end.year + 1}-01-31", "HMRC online", "yearly", "sa", "31 january"),
                 ("Balancing payment and first payment on account", f"{ty_end.year + 1}-01-31", "HMRC online", "yearly", "poa", "31 january"),
                 ("Second payment on account", f"{ty_end.year + 1}-07-31", "HMRC online", "yearly", "poa", "31 july")]
    if structure == "limited company":
        due = lambda n: add_months(first, n).isoformat() if first else f"rule: {n} months after the relevant date"
        rows += [("Corporation Tax registration", due(3), "HMRC online", "once", "ctreg", "3 months"), ("Annual accounts to Companies House", "rule: 9 months after the accounting year end (first accounts 21 months after incorporation)", "Companies House", "yearly", "ch", "9 months"),
                 ("Company Tax Return and Corporation Tax payment", "rule: return 12 months and payment 9 months and 1 day after the accounting period ends", "HMRC online", "yearly", "ctdead", "12 months"),
                 ("Confirmation statement", due(12), "Companies House", "yearly", "cs", "confirmation statement"), ("Director identity verification", "rule: before the first filing", "Companies House", "once", "idv", "identity")]
        if "paye" in pages:
            rows.append(("PAYE registration if directors or staff are paid", "rule: before the first payday", "HMRC online", "once", "paye", "employer"))
    rows += [("VAT registration check: rolling 12 months and 30 day look-ahead", f"rule: when taxable turnover passes {th['vat_registration']:,.0f}" if "vat_registration" in th else "rule: threshold not read", "HMRC online", "monthly check", "vatreg", "30 day"),
             ("ICO data protection fee, if the product holds customer data", "rule: before processing customer data in business", "ico.org.uk", "yearly", "ico", "fee")]
    table, cal = [], []
    for what, due_, where, rep, key, phrase in rows:
        ok = pages[key]["ok"] and phrase in pages[key]["text"].lower()
        table.append(f"| {what} | {due_} | {where} | {rep} | {'confirmed on ' + pages[key]['url'] if ok else 'NOT confirmed'} |")
        cal.append({"what": what, "due": due_, "where": where, "repeats": rep})
        if not ok:
            why.append(f"rule not confirmed: {what}")
    why = list(dict.fromkeys(why))
    if why:
        flag = "caution" if flag == "clear" else flag
    reason = "; ".join(why[:4]) + ("; more in open questions" if len(why) > 4 else "") if why else "All rules confirmed on pages read; no threshold close."
    mtd = [f"- From {f}: income over {v:,.0f}. Venture revenue {revenue:,.0f}: " + ("in scope on this venture alone" if revenue > v else "below on this venture alone; Charlie adds other self-employment and property income") for f, v in phases] or ["- Phases not confirmed from the page; check the MTD page below."]
    lines = [f"FLAG: {flag}", "", reason, "", NOTICE, "", f"## Registrations needed for {structure}", "| What | Due | Where | Repeats | Rule check |", "|---|---|---|---|---|", *table, "",
             "## VAT position", f"- Registration threshold: {th['vat_registration']:,.0f}; deregistration: {th.get('vat_deregistration', 0):,.0f}. Revenue to date {revenue:,.0f}." if "vat_registration" in th else "- Threshold not confirmed from a page read.",
             "- Digital sales to UK consumers are VAT-able at the standard rate once registered. EU and overseas sales need separate VAT checks.", "", "## Making Tax Digital for Income Tax", *mtd,
             "- Choose the lowest-cost HMRC-recognised software, free options first, from HMRC's software list.", "", "## Checklist for Charlie (the job never logs in)", *[f"- [ ] {x}" for x in LISTS[structure]], "- [ ] Government Gateway sign-in, created and held by Charlie", "",
             "## Open questions for an accountant", "- Who accounts for VAT on app store or provider sales?", "- Overseas sales, employees or anything unusual?", *[f"- {w}" for w in why], "",
             "## Sources read", *[f"- {p['label']}: {p['url']} (read {p['read_on']})" if p["ok"] else f"- NOT READ: {p['label']}, {p['url']} (tried {p['read_on']})" for p in pages.values()], "", f"Checked on {day}."]
    k.write(ctx, "clear/tax-registration.md", "\n".join(lines))
    k.write(ctx, "clear/tax-deadlines.json", cal)
    return {"summary": f"Tax registration ({structure}): {flag}. {reason}"[:300], "flag": flag}


if __name__ == "__main__":
    k.run(main)
