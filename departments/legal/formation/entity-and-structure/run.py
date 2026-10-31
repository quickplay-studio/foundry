"""Entity and Structure: GitHub implementation of departments/legal/formation/entity-and-structure/SKILL.md.

Reads rates and fees from gov.uk (dated), has the free model pull the figures out of the page text, checks each figure
appears on a page read, and does all the arithmetic in code. The brief recommends; Charlie chooses and registers.
Never registers, signs or pays. Not legal advice.
"""
import datetime as dt
import json
import re
from urllib.parse import urlparse

from foundry import jobkit as k

G = "https://www.gov.uk/"
PAGES = {  # label, url, search query, word the page must contain
    "income": ("Income Tax rates and Personal Allowances", G + "income-tax-rates", "gov.uk income tax rates and personal allowances", "personal allowance"),
    "ni4": ("Self-employed National Insurance rates", G + "self-employed-national-insurance-rates", "gov.uk self-employed national insurance class 4 rates", "class 4"),
    "ct": ("Corporation Tax rates", G + "corporation-tax-rates", "gov.uk corporation tax rates small profits", "corporation tax"),
    "div": ("Tax on dividends", G + "tax-on-dividends", "gov.uk tax on dividends allowance rates", "dividend"),
    "allow": ("Trading allowance", G + "guidance/tax-free-allowances-on-property-and-trading-income", "gov.uk trading allowance tax-free", "trading allowance"),
    "vat": ("VAT registration thresholds", G + "vat-registration-thresholds", "gov.uk VAT registration threshold", "threshold"),
    "fees": ("Companies House fees", G + "government/publications/companies-house-fees/companies-house-fees", "Companies House fees incorporation confirmation statement", "confirmation statement"),
    "st": ("Set up as a sole trader", G + "set-up-sole-trader", "gov.uk set up as a sole trader register self assessment", "self assessment"),
    "ltd": ("Set up a limited company", G + "set-up-limited-company", "gov.uk set up a limited company", "companies house"),
    "idv": ("Companies House identity verification", G + "guidance/verify-your-identity-for-companies-house", "Companies House director identity verification", "identity"),
    "name": ("Business name rules", "", "gov.uk choose a business name rules sensitive words", "business name"),
}
KEYS = {"personal_allowance": "pa", "basic_rate_pct": "basic", "higher_rate_pct": "higher", "basic_rate_upper": "basic_upper", "class4_lower": "c4l", "class4_upper": "c4u", "class4_main_pct": "c4m",
        "class4_upper_pct": "c4h", "ct_small_pct": "ct", "ct_small_limit": "ct_limit", "div_allowance": "da", "div_basic_pct": "div_basic", "div_higher_pct": "div_higher",
        "trading_allowance": "allow", "vat_threshold": "vat", "incorporation_fee": "inc_fee", "confirmation_fee": "conf_fee"}
NOTICE = "Not legal advice. Drafts are checked by Charlie or a solicitor before use."


def num(v):
    try:
        return float(str(v).replace(",", "").replace("£", "").replace("%", "")) if not isinstance(v, bool) and v not in (None, "") else None
    except ValueError:
        return None


def grounded(v, text, pct):
    forms = {f"{v:,.0f}", f"{v:.0f}", f"{v:g}", f"{v:,.2f}"}
    tail = r"\s?(%|per ?cent)" if pct else r"(?![\d])"
    return any(re.search(r"(?<![\d.,])" + re.escape(f) + tail, text, re.I) for f in forms)


def read_pages(sources):
    out, day = {}, dt.date.today().isoformat()
    for key, (label, url, query, word) in sources.items():
        text = k.fetch(url, 40000) if url else ""
        if len(text) < 200:
            for r in k.search(query, 3):
                u = r.get("url", "")
                if ("." + urlparse(u).netloc.lower()).endswith(".gov.uk"):
                    url, text = u, k.fetch(u, 40000)
                    if len(text) >= 200:
                        break
        ok = len(text) >= 200 and word in text.lower()
        out[key] = {"label": label, "url": url, "read_on": day, "ok": ok, "text": text if ok else ""}
    return out


def figures(text, n=1400):
    parts = re.split(r"(?<=[.!?])\s+|\n", text)
    return " ".join(p.strip() for p in parts if "£" in p or "%" in p)[:n]


def sole(p, r):
    ti, band = max(0.0, p - r["pa"]), max(0.0, r["basic_upper"] - r["pa"])
    tax = min(ti, band) * r["basic"] / 100 + max(0.0, ti - band) * r["higher"] / 100
    ni = max(0.0, min(p, r["c4u"]) - r["c4l"]) * r["c4m"] / 100 + max(0.0, p - r["c4u"]) * r["c4h"] / 100
    return p - tax - ni


def limited(p, r):
    net = p * (1 - r["ct"] / 100)
    after_pa = max(0.0, net - r["pa"])
    in_basic = min(after_pa, max(0.0, r["basic_upper"] - r["pa"]))
    tax = max(0.0, in_basic - r["da"]) * r["div_basic"] / 100 + (after_pa - in_basic) * r["div_higher"] / 100
    return net - tax - r["conf_fee"]


def money(v):
    return "not read" if v is None else (f"-£{abs(v):,.0f}" if v < 0 else f"£{v:,.0f}")


def main(ctx):
    idea, brain = ctx["idea"], ctx["brain"]
    day = dt.date.today().isoformat()
    facts = json.dumps({key: idea.get(key) for key in ("title", "kind", "problem", "who", "mvp", "money", "channels", "note")}, ensure_ascii=False)
    pages = read_pages(PAGES)
    alltext = " ".join(p["text"] for p in pages.values())
    ans = k.ask(
        "You extract UK tax figures for a solo founder. Not legal advice. Use only the page extracts below; give a number only if the extracts state it for the current tax year, else null. "
        "Percentages as plain numbers. Also read the venture for structure facts.\nReturn JSON only: {\"tax_year\": \"2026 to 2027\", \"rates\": {" + ", ".join(f'"{key}": 0' for key in KEYS)
        + "}, \"expected_revenue_gbp\": 0, \"b2b_contracts_need_company\": false, \"outside_investment\": false, \"liability_risk\": \"low|medium|high\", \"public_name_matters\": false, "
        "\"reason\": \"<one sentence>\"}\n\nVENTURE\n" + facts + "\n\nBRAIN\n" + brain[:2500] + "\n\nEXTRACTS\n"
        + "\n".join(f"[{key}] {figures(p['text'])}" for key, p in pages.items() if p["ok"]))
    ans = ans if isinstance(ans, dict) else {}
    raw = ans.get("rates") if isinstance(ans.get("rates"), dict) else {}
    r = {}
    for key, short in KEYS.items():
        v = num(raw.get(key))
        if v is not None and alltext and grounded(v, alltext, key.endswith("_pct")):
            r[short] = v
    tax_year = str(ans.get("tax_year", ""))
    tax_year = tax_year if tax_year and tax_year in alltext.replace("-", " to ") else "not confirmed from a page"
    need_sole, need_ltd = ("pa", "basic", "higher", "basic_upper", "c4l", "c4u", "c4m", "c4h"), ("ct", "da", "div_basic", "div_higher", "conf_fee", "ct_limit")
    can_compare = all(x in r for x in need_sole + need_ltd)
    why = []
    if not ans:
        why.append("no free model answered, so no figures were extracted")
    unread = [p["label"] for key, p in pages.items() if not p["ok"] and key in ("income", "ni4", "ct", "div", "allow", "vat", "fees", "st", "ltd")]
    if unread:
        why.append("pages not read: " + ", ".join(unread))
    if not can_compare:
        why.append("tax comparison incomplete: missing " + ", ".join(x for x in need_sole + need_ltd if x not in r))
    budget = ctx["budget"] if isinstance(ctx["budget"], dict) else {}
    actual = num(budget.get("revenue")) or 0.0
    expected = num(ans.get("expected_revenue_gbp"))
    expected = expected if expected and (grounded(expected, brain + facts, False)) else None
    rev = max(actual, expected or 0.0)
    rows, breakeven = [], None
    if can_compare:
        for p in (5000, 20000, 50000):
            if p <= r["ct_limit"]:
                s_, l_ = sole(p, r), limited(p, r)
                rows.append((p, s_, l_, l_ - s_))
        breakeven = next((p for p in range(1000, int(r["ct_limit"]) + 1, 500) if limited(p, r) > sole(p, r)), None)
    flags = {"liability": ans.get("liability_risk") == "high", "b2b": ans.get("b2b_contracts_need_company") is True, "investment": ans.get("outside_investment") is True}
    if rev <= 0:
        choice, because = "hold off", "no revenue yet: the venture stays a personal project until it earns"
    elif r.get("allow") is not None and rev <= r["allow"]:
        choice, because = "hold off", f"revenue {money(rev)} is within the trading allowance of {money(r['allow'])}"
    elif any(flags.values()):
        choice, because = "limited company", "a trigger applies: " + ", ".join(n for n, on in flags.items() if on)
    elif breakeven and rev >= breakeven:
        choice, because = "limited company", f"revenue {money(rev)} is above the computed break-even of {money(breakeven)}"
    else:
        choice, because = "sole trader", "lowest admin once income passes the trading allowance"
        if r.get("allow") is None:
            why.append("trading allowance not read, so hold off versus sole trader is unconfirmed")
    screen = k.read(ctx, "clear/regulatory-screen.json")
    sflag = str(screen.get("flag", "caution")) if isinstance(screen, dict) else "missing"
    if sflag != "clear":
        why.append(f"regulatory screen is {sflag}: do not register until Charlie has cleared it")
    flag = "caution" if why else "clear"
    lines = [f"DECISION NEEDED: {choice}", "", f"Recommendation: {choice}, because {because}. Source check: {flag}" + (f" ({'; '.join(why)})" if why else "") + ".", "", NOTICE, "",
             "## Facts that decide structure", f"- Revenue to date: {money(actual) if actual else 'none recorded'}. Expected first-year revenue: {money(expected) if expected else 'not in the brain'}.",
             f"- Liability risk: {ans.get('liability_risk', 'unknown') if ans else 'unknown'}. B2B contracts need a company: {flags['b2b']}. Outside investment: {flags['investment']}.",
             "- Charlie's other income, whether his name may be public, and any outside-interests clause in his employment contract are unknown and are questions below.", "",
             "## Options", "| | Hold off | Sole trader | Limited company |", "|---|---|---|---|",
             f"| Registration | None while trading income stays within the allowance ({money(r.get('allow'))}) | Self Assessment with HMRC by 5 October after the tax year trading began | Incorporate at Companies House; Corporation Tax registration within 3 months of starting |",
             f"| Cost | Nil | No registration fee; Class 4 NI on profits | Incorporation {money(r.get('inc_fee'))}; confirmation statement {money(r.get('conf_fee'))} a year; accountant not read |",
             "| Liability | Personal | Personal and unlimited | Limited to the company |", "| Public details | None | Name and address may show to customers and stores | Directors and persons with significant control are public; a registered office service can hide a home address |",
             "| Admin | None | Annual return by 31 January, payments on account | Accounts to Companies House and HMRC, Company Tax Return, director identity verification |", "",
             f"## Tax comparison (tax year {tax_year}, rates read {day})"]
    if rows:
        lines += ["| Profit | Sole trader take-home | Limited company take-home | Difference |", "|---|---|---|---|", *[f"| {money(p)} | {money(s_)} | {money(l_)} | {money(d)} |" for p, s_, l_, d in rows],
                  f"- Company route is cheaper from about {money(breakeven)} of profit." if breakeven else "- No break-even found up to the small profits limit.",
                  "- Assumes no other income, no salary, all post-tax profit paid as dividends, Companies House fees only (no accountant), Class 2 and employer NI not modelled, no allowance taper."]
    else:
        lines += ["- Not computed: a figure was missing or not found on a page read. Re-run."]
    lines += ["", "## Triggers to move up", f"- Profit above the break-even ({money(breakeven)}), a contract that needs a company, a liability Charlie will not carry, VAT approaching {money(r.get('vat'))}, or a partner or investor.", "",
              "## Practical effects", "- Payment providers and app stores ask for legal entity details; Apple organisation accounts need a legal entity, individual accounts show a personal name.",
              "- Trade mark and domain ownership should match the chosen owner; moving from sole trader to company needs a transfer of assets and contracts (cost, tax, time).", "",
              "## Open questions for Charlie", "- Other income this tax year?", "- Is a public name acceptable?", "- Does the employment contract restrict outside business interests?", "- Expected first-year revenue and profit?", "",
              "## Sources read", *[f"- {p['label']}: {p['url']} (read {p['read_on']})" if p["ok"] else f"- NOT READ: {p['label']}, {p['url'] or 'no page found'} (tried {p['read_on']})" for p in pages.values()], "", f"Checked on {day}."]
    k.write(ctx, "clear/entity-and-structure.md", "\n".join(lines))
    return {"summary": f"Entity and structure: {choice}. Source check {flag}." + (f" {why[0]}" if why else ""), "flag": flag}


if __name__ == "__main__":
    k.run(main)
