"""Contact Enrichment: GitHub implementation of departments/sales/enrichment/contact-enrichment/SKILL.md.

Pass 1, published only: addresses and main business numbers that appear on a lead's own homepage,
/contact, /about and /team (role address or named address, never a guessed pattern). Pass 2, Hunter
free plan (HUNTER_API_KEY) on tier A then B, accepting confidence 80 or more and stopping at 80 percent
of the month's credits. Director names come from Companies House (COMPANIES_HOUSE_API_KEY), never a
date of birth. Only corporate, unsuppressed leads with a blank email are touched; non-blank cells are
never overwritten. LinkedIn is a todo list for Charlie, never scraped.
"""
import csv
import datetime as dt
import io
import re
import time
from urllib.parse import quote

import requests

from foundry import jobkit as k

LEAD_COLS = ("id,company,company_number,domain,website,segment,subscriber_type,contact_name,role,email,email_basis,phone,linkedin_url,"
             "source,source_url,collected_on,email_status,verified_on,fit_score,tier,fit_reason,suppressed,notes").split(",")
ROLE = {"info", "hello", "sales", "contact", "enquiries", "enquiry", "office", "admin", "team", "support", "mail", "hi", "general"}
PAGES = ("", "contact", "about", "team")
PHONE = re.compile(r"(?:\+44\s?\(?0?\)?\s?|\b0)(?:\d[\s-]?){9,10}\b")
CAP, BUDGET_S = 40, 15 * 60


def b2b(ctx):
    audit = k.read(ctx, "audit.json", {}) or {}
    return "b2b" in (str(ctx["idea"].get("business_model", "")).lower(), str(audit.get("business_model", "")).lower())


def table(ctx, rel):
    return list(csv.DictReader(io.StringIO(k.read(ctx, rel, "") or "")))


def jget(url, **kw):
    try:
        r = requests.get(url, timeout=20, **kw)
        return r.json() if r.ok else {}
    except Exception:  # noqa: BLE001
        return {}


def hunter_room(key):
    d = (jget("https://api.hunter.io/v2/account", params={"api_key": key}).get("data") or {}).get("requests", {}).get("searches", {})
    used, avail = d.get("used"), d.get("available")
    return isinstance(used, int) and isinstance(avail, int) and avail > 0 and used / avail < 0.8


def published(dom, name):
    """First published business address and phone on the lead's own pages: (email, basis, phone, url)."""
    found = {}
    for path in PAGES:
        url = f"https://{dom}/{path}"
        text = re.sub(r"\s*[\[(]\s*at\s*[\])]\s*", "@", k.fetch(url, 12000), flags=re.I)
        for em in re.findall(r"[\w.+-]+@" + re.escape(dom) + r"\b", text.lower()):
            local, tokens = em.split("@")[0], [t for t in re.split(r"\W+", name.lower()) if len(t) > 1]
            if local in ROLE:
                found.setdefault("role", (em, url))
            elif tokens and any(t in local for t in tokens):
                found.setdefault("named", (em, url))
        for ph in PHONE.findall(text):
            digits = re.sub(r"\D", "", ph)
            rest = (digits[2:] if digits.startswith("44") else digits[1:]).lstrip("0")
            if not rest.startswith("7"):  # no personal mobiles
                found.setdefault("phone", ("+44" + rest, url))
        if "named" in found and "phone" in found:
            break
    pick = found.get("named") or found.get("role")
    em, url = pick if pick else ("", "")
    ph, phurl = found.get("phone") or ("", "")
    return em, "named" if "named" in found else "role" if pick else "", ph, url or phurl


def main(ctx):
    if not b2b(ctx):
        return {"skipped": "no business buyer"}
    leads = table(ctx, "sell/leads.csv")
    if not leads:
        return {"skipped": "no sell/leads.csv rows yet: run list-building first"}
    today, ch, hunter = dt.date.today().isoformat(), k.secret("COMPANIES_HOUSE_API_KEY"), k.secret("HUNTER_API_KEY")
    changed, started, looked, found_n, hunted = 0, time.monotonic(), 0, 0, 0
    for r in table(ctx, "sell/inbox/linkedin-urls.csv"):  # Charlie's paste: id,linkedin_url
        for lead in leads:
            if lead["id"] == r.get("id", "").strip() and not lead["linkedin_url"] and re.match(r"https://([a-z]+\.)?linkedin\.com/in/", r.get("linkedin_url", "").strip()):
                lead["linkedin_url"], changed = r["linkedin_url"].strip(), changed + 1
    taken = {r["email"] for r in leads if r["email"]}
    names = {(r["company_number"], r["contact_name"].lower()) for r in leads if r["contact_name"]}
    todo = [r for r in leads if r["subscriber_type"] == "corporate" and r["suppressed"] != "yes" and not r["email"]]
    todo.sort(key=lambda r: (r["tier"] not in ("A", "B"), r["tier"]))
    for r in todo:
        if looked >= CAP or time.monotonic() - started > BUDGET_S:
            break
        if ch and r["company_number"] and not r["contact_name"]:  # active director name only, no DOB or address
            offs = jget(f"https://api.company-information.service.gov.uk/company/{r['company_number']}/officers", auth=(ch, "")).get("items") or []
            offs_names = [o.get("name", "") for o in offs if isinstance(o, dict) and o.get("officer_role") == "director" and not o.get("resigned_on")]
            if offs_names:
                last, _, first = offs_names[0].partition(",")
                who = f"{first.strip()} {last.strip()}".title() if first else last.title()
                if (r["company_number"], who.lower()) not in names:  # do not create a duplicate of another lead
                    r["contact_name"], r["role"], changed = who, r["role"] or "Director", changed + 1
                    names.add((r["company_number"], who.lower()))
        if not r["domain"]:
            continue
        looked += 1
        em, basis, phone, url = published(r["domain"], r["contact_name"])
        if em in taken:
            em = ""  # one lead per address: a second lead never gets the same role address
        if em:
            taken.add(em)
            r["email"], r["email_basis"], found_n = em, basis, found_n + 1
            r["notes"] = (r["notes"] + f"; email published at {url} on {today}").strip("; ")  # source and date for UK GDPR
            r["source_url"] = r["source_url"] or url
        if phone and not r["phone"]:
            r["phone"] = phone
        changed += bool(em or phone)
        if not em and hunter and r["tier"] in ("A", "B") and r["contact_name"] and hunter_room(hunter):
            first, _, last = r["contact_name"].partition(" ")
            d = jget("https://api.hunter.io/v2/email-finder", params={"domain": r["domain"], "first_name": first, "last_name": last.split(" ")[-1], "api_key": hunter}).get("data") or {}
            hunted += 1
            if d.get("email") and isinstance(d.get("score"), (int, float)) and d["score"] >= 80 and str(d["email"]).lower() not in taken:  # a found address, never a pattern guess
                taken.add(str(d["email"]).lower())
                r["email"], r["email_basis"], changed = str(d["email"]).lower(), "named", changed + 1
                r["notes"] = (r["notes"] + f"; hunter finder confidence {d['score']} on {today}").strip("; ")
    queue = [r for r in leads if r["tier"] == "A" and not r["linkedin_url"] and r["contact_name"] and r["suppressed"] != "yes"]
    lines = ["# LinkedIn todo", "", "Charlie opens each search from his own account and pastes the profile URL into `sell/inbox/linkedin-urls.csv` as `id,linkedin_url`. The next run copies it in. No scraping, no automation.", ""]
    lines += [f"- [ ] {r['id']} {r['contact_name']}, {r['company']}: https://www.linkedin.com/search/results/people/?keywords={quote(r['contact_name'] + ' ' + r['company'])}" for r in queue]
    if not queue:
        lines.append("No tier A lead is waiting for a profile yet (fit-scoring sets tiers; re-run after it).")
    k.write(ctx, "sell/linkedin-todo.md", "\n".join(lines))
    out = io.StringIO()
    w = csv.DictWriter(out, LEAD_COLS, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(leads)
    k.write(ctx, "sell/leads.csv", out.getvalue())
    miss = [n for n, v in (("COMPANIES_HOUSE_API_KEY", ch), ("HUNTER_API_KEY", hunter)) if not v]
    return {"summary": f"Contacts: {looked} leads read, {found_n} published addresses found, {hunted} Hunter lookups, {len(queue)} LinkedIn lookups queued."
            + (f" Skipped steps without {', '.join(miss)}." if miss else ""), "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
