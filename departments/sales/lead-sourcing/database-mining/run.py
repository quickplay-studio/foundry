"""Database Mining: GitHub implementation of departments/sales/lead-sourcing/database-mining/SKILL.md.

Pulls active directors and secretaries of mapped limited companies from Companies House into
sell/raw/database.csv. No dates of birth, no correspondence addresses, no emails. Needs
COMPANIES_HOUSE_API_KEY. Other registers need Charlie's terms check, so they are logged as skipped.
"""
import csv
import datetime as dt
import io
import re
import time
from urllib.parse import urlparse

import requests

from foundry import jobkit as k

CH = "https://api.company-information.service.gov.uk"
PAGE = "https://find-and-update.company-information.service.gov.uk/company/"
COLS = "company,company_number,domain,website,segment,subscriber_type,contact_name,role,email,email_basis,phone,linkedin_url,source,source_url,collected_on".split(",")
CORPORATE = ("ltd", "plc", "llp", "private-limited", "old-public-company")
BAD_HOSTS = ("companieshouse", "gov.uk", "linkedin", "facebook", "twitter", "instagram", "endole", "checkcompany", "opencorporates",
             "yell.com", "dnb.com", "companiesintheuk", "northdata", "duedil", "bizdb")
BATCH, WEB_CAP, BUDGET_S = 60, 40, 15 * 60


def b2b(ctx):
    audit = k.read(ctx, "audit.json", {}) or {}
    return "b2b" in (str(ctx["idea"].get("business_model", "")).lower(), str(audit.get("business_model", "")).lower())


def table(ctx, rel):
    return list(csv.DictReader(io.StringIO(k.read(ctx, rel, "") or "")))


def has_icp(ctx):
    return bool(k.read(ctx, "sell/icp.json", None)) or "```json" in (k.read(ctx, "sell/icp.md", "") or "")


def ch_get(key, path, **params):
    try:
        r = requests.get(CH + path, params=params, auth=(key, ""), timeout=20)
        return r.json() if r.ok else {}
    except Exception:  # noqa: BLE001
        return {}


def person(raw):
    last, _, first = str(raw).partition(",")
    return (f"{first.strip()} {last.strip()}" if first else last.strip()).title()


def website(name, number, town):
    """A domain only when the page text holds the company name (less its legal suffix) or number."""
    stem = re.sub(r"\b(limited|ltd|plc|llp)\b\.?\s*$", "", name.lower()).strip()
    for hit in k.search(f'"{name}" {town}', 4):
        url = str(hit.get("url", ""))
        host = re.sub(r"^www\.", "", urlparse(url).netloc.lower())
        if not host or any(b in host for b in BAD_HOSTS):
            continue
        text = (str(hit.get("content", "")) + " " + k.fetch(url, 6000)).lower()
        if (len(stem) >= 4 and stem in text) or number in text:
            return host, "https://" + host
    return "", ""


def main(ctx):
    if not b2b(ctx):
        return {"skipped": "no business buyer"}
    if not has_icp(ctx):
        return {"skipped": "no ICP yet (sell/icp.md): run icp-definition first"}
    key = k.secret("COMPANIES_HOUSE_API_KEY")
    if not key:
        return {"skipped": "COMPANIES_HOUSE_API_KEY missing: Charlie registers the free key and adds it as a GitHub secret"}
    today = dt.date.today().isoformat()
    state = k.read(ctx, "sell/raw/database-state.json", {}) or {}
    done = set(state.get("done", [])) if isinstance(state.get("done"), list) else set()
    mapped = table(ctx, "sell/market-map.csv")[:200]
    if not mapped:  # no map yet: query the register inline for the first segment
        icp = k.read(ctx, "sell/icp.json", {}) or {}
        seg = (icp.get("segments") or [{}])[0] if isinstance(icp, dict) else {}
        prefix = re.sub(r"\D", "", str((seg.get("sic_prefixes") or [""])[0]))[:5]
        if prefix:
            n = 5 - len(prefix)
            codes = [prefix] if n <= 0 else [prefix + str(i).zfill(n) for i in range(10 ** n)][:100]
            data = ch_get(key, "/advanced-search/companies", sic_codes=",".join(codes), company_status="active", size=60)
            mapped = [{"company_number": i.get("company_number", ""), "company": i.get("company_name", ""), "segment": seg.get("name", "")}
                      for i in (data.get("items", []) if isinstance(data, dict) else [])]
    todo = [m for m in mapped if m.get("company_number") and m["company_number"] not in done][:BATCH]
    if not todo:
        return {"skipped": "nothing new to pull: no market-map.csv rows left, or the register returned no hits"}
    rows = {(r["company_number"], r["contact_name"]): r for r in table(ctx, "sell/raw/database.csv")}
    started, webs, pulled = time.monotonic(), 0, 0
    for m in todo:
        if time.monotonic() - started > BUDGET_S:
            break
        num = m["company_number"]
        co = ch_get(key, f"/company/{num}")
        officers = ch_get(key, f"/company/{num}/officers")
        done.add(num)
        if not isinstance(co, dict) or str(co.get("company_status", "")) != "active":
            continue
        subscriber = "corporate" if str(co.get("type", "")).startswith(CORPORATE) else "individual"
        town = str((co.get("registered_office_address") or {}).get("locality", ""))
        name = str(co.get("company_name") or m.get("company", ""))
        dom, site = ("", "")
        if webs < WEB_CAP:
            dom, site = website(name, num, town)
            webs += 1
        people = [o for o in (officers.get("items", []) if isinstance(officers, dict) else [])
                  if isinstance(o, dict) and not o.get("resigned_on") and str(o.get("officer_role", "")) in ("director", "secretary")]
        people.sort(key=lambda o: o.get("officer_role") != "director")
        for o in people[:3]:
            who = person(o.get("name", ""))
            rows[(num, who)] = {"company": name, "company_number": num, "domain": dom, "website": site, "segment": m.get("segment", ""),
                                "subscriber_type": subscriber, "contact_name": who, "role": str(o["officer_role"]).title(), "email": "",
                                "email_basis": "", "phone": "", "linkedin_url": "", "source": "companies-house", "source_url": PAGE + num,
                                "collected_on": today}
        pulled += 1
    buf = io.StringIO()
    w = csv.DictWriter(buf, COLS, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(rows.values())
    k.write(ctx, "sell/raw/database.csv", buf.getvalue())
    k.write(ctx, "sell/raw/database-state.json", {"done": sorted(done), "updated": today,
                                                  "skipped": ["other open registers (Charity Commission, FCA, FSA, Contracts Finder): need Charlie's terms check per register"]})
    return {"summary": f"Database mining: {pulled} companies read, {len(rows)} officer rows in raw/database.csv, {webs} website lookups. Other registers not run (need Charlie's terms approval).", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
