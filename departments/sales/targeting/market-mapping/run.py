"""Market Mapping: GitHub implementation of departments/sales/targeting/market-mapping/SKILL.md.

Lists active limited companies, PLCs and LLPs that fit the ICP from the Companies House register,
so the map starts on lawful ground (corporate subscribers). Needs COMPANIES_HOUSE_API_KEY; without
it the job skips and says so. The first 200 rows of market-map.csv are the recommended first slice.
"""
import csv
import datetime as dt
import io
import json
import re
from collections import Counter

import requests

from foundry import jobkit as k

CH = "https://api.company-information.service.gov.uk"
COLS = "company_number,company,segment,sic_codes,incorporated_on,postcode,region,company_type,source,collected_on".split(",")
OK_TYPES = ("ltd", "plc", "llp", "private-limited", "old-public-company")
SOLO_HEAVY = ("43", "96", "81", "47", "56", "49", "95", "93", "86", "88")  # mostly sole traders: the register under-covers them
NATIONAL = ("", "uk", "united kingdom", "england", "gb", "great britain", "national", "nationwide")
CAP = 30  # requests per run, well under 600 per five minutes


def b2b(ctx):
    audit = k.read(ctx, "audit.json", {}) or {}
    return "b2b" in (str(ctx["idea"].get("business_model", "")).lower(), str(audit.get("business_model", "")).lower())


def aslist(x):
    if isinstance(x, str):
        x = re.split(r"[;,]", x)
    return [str(i).strip() for i in x if str(i).strip()] if isinstance(x, (list, tuple)) else []


def get_icp(ctx):
    data = k.read(ctx, "sell/icp.json", None)
    if not isinstance(data, dict):
        data = None
        for block in reversed(re.findall(r"```json\s*(.*?)```", k.read(ctx, "sell/icp.md", "") or "", re.S)):
            try:
                data = json.loads(block)
                break
            except ValueError:
                continue
    return data if isinstance(data, dict) and isinstance(data.get("segments"), list) else None


def codes(prefix):
    prefix = re.sub(r"\D", "", prefix)[:5]
    n = 5 - len(prefix)
    return [prefix] if n <= 0 else [prefix + str(i).zfill(n) for i in range(10 ** n)]


def table(ctx, rel):
    return list(csv.DictReader(io.StringIO(k.read(ctx, rel, "") or "")))


def ch_search(key, params):
    try:
        r = requests.get(CH + "/advanced-search/companies", params=params, auth=(key, ""), timeout=25)
        return r.json() if r.ok else {}
    except Exception:  # noqa: BLE001
        return {}


def main(ctx):
    if not b2b(ctx):
        return {"skipped": "no business buyer"}
    icp = get_icp(ctx)
    if not icp:
        return {"skipped": "no ICP yet (sell/icp.json or the icp block in sell/icp.md): run icp-definition first"}
    key = k.secret("COMPANIES_HOUSE_API_KEY")
    if not key:
        return {"skipped": "COMPANIES_HOUSE_API_KEY missing: Charlie registers the free key and adds it as a GitHub secret"}
    today = dt.date.today()
    state = k.read(ctx, "sell/market-map-state.json", {}) or {}
    cursor = state.get("cursor", {}) if isinstance(state.get("cursor"), dict) else {}
    rows = {r["company_number"]: r for r in table(ctx, "sell/market-map.csv") if r.get("company_number")}
    segs = [s for s in icp["segments"] if isinstance(s, dict) and s.get("name")]
    calls, new, covered = 0, 0, {}
    for seg in segs:
        name, prefixes = str(seg["name"]), aslist(seg.get("sic_prefixes"))
        covered[name] = not (prefixes and all(p[:2] in SOLO_HEAVY for p in prefixes)) and seg.get("register_covered") != "no"
        excl = [e.lower() for e in aslist(seg.get("exclusions"))]
        tasks = [(region, chunk) for region in (aslist(seg.get("regions")) or [""]) for p in prefixes
                 for chunk in [codes(p)[i:i + 100] for i in range(0, len(codes(p)), 100)]]
        for region, chunk in tasks:
            tkey = f"{name}|{region}|{chunk[0]}"
            while cursor.get(tkey, 0) >= 0 and calls < CAP:
                params = {"sic_codes": ",".join(chunk), "company_status": "active", "size": 100, "start_index": cursor.get(tkey, 0)}
                if region.lower() not in NATIONAL:
                    params["location"] = region
                if not seg.get("new_companies"):
                    params["incorporated_to"] = (today - dt.timedelta(days=365)).isoformat()
                data, calls = ch_search(key, params), calls + 1
                items = data.get("items", []) if isinstance(data, dict) else []
                for it in items:
                    num, ctype = str(it.get("company_number", "")), str(it.get("company_type", ""))
                    cname = str(it.get("company_name", "")).strip()
                    if not num or num in rows or not ctype.startswith(OK_TYPES) or str(it.get("company_status", "active")) != "active":
                        continue
                    sics = [str(s) for s in it.get("sic_codes", []) or []]
                    if any(e in cname.lower() or any(s.startswith(e) for s in sics) for e in excl):
                        continue
                    addr = it.get("registered_office_address", {}) or {}
                    rows[num] = {"company_number": num, "company": cname, "segment": name, "sic_codes": ";".join(sics),
                                 "incorporated_on": it.get("date_of_creation", ""), "postcode": addr.get("postal_code", ""),
                                 "region": region if region.lower() not in NATIONAL else addr.get("region") or addr.get("locality", ""),
                                 "company_type": ctype, "source": "companies-house-advanced-search", "collected_on": today.isoformat()}
                    new += 1
                nxt = cursor.get(tkey, 0) + 100
                cursor[tkey] = nxt if len(items) >= 100 else -1
    if not calls and not rows:
        return {"skipped": "nothing to map: every ICP segment lacks SIC prefixes"}
    allrows = list(rows.values())
    counts = Counter(r["segment"] for r in allrows)
    lead = max((s for s in counts if covered.get(s, True)), key=counts.get, default=None)
    reg = Counter(r["region"] for r in allrows if r["segment"] == lead and r["region"]).most_common(1)
    first = [r for r in allrows if r["segment"] == lead and (not reg or r["region"] == reg[0][0])][:200]
    ordered = first + [r for r in allrows if r not in first]
    buf = io.StringIO()
    w = csv.DictWriter(buf, COLS, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(ordered)
    k.write(ctx, "sell/market-map.csv", buf.getvalue())
    pending = sum(1 for v in cursor.values() if v >= 0)
    k.write(ctx, "sell/market-map-state.json", {"cursor": cursor, "pulled_on": today.isoformat(), "requests_last_run": calls})
    answer = k.ask("Write two plain sentences on how well the Companies House register covers these ICP segments and what gaps remain. "
                   "Add no facts beyond the counts. Return JSON only: {\"coverage\": \"...\"}\nCOUNTS " + json.dumps(counts)
                   + "\nREGISTER_COVERED " + json.dumps(covered))
    para = str(answer.get("coverage", ""))[:600] if isinstance(answer, dict) and isinstance(answer.get("coverage"), str) else ""
    lines = ["# Market map", "", f"Register pull date: {today.isoformat()}. Source: Companies House advanced search, active limited companies, PLCs and LLPs only (corporate subscribers under PECR).",
             f"Companies mapped: {len(allrows)} ({new} new this run). Requests used: {calls} of {CAP}." + (f" {pending} search windows still to page; the next run resumes." if pending else ""), "",
             "## Count per segment", "| Segment | Companies | register_covered |", "|---|---|---|",
             *[f"| {s} | {counts.get(s, 0)} | {'yes' if covered.get(s, True) else 'no'} |" for s in covered],
             "", "## Website coverage", "The register holds no website, so 0 percent of rows have one. database-mining finds domains from company name and town.", "",
             "## Gaps", para or "Coverage note not written: no free model answered.",
             *[f"- {s}: register_covered: no. Mostly sole traders, so leave it to web-and-maps-scraping." for s, c in covered.items() if not c], "",
             "## First slice", (f"The first {len(first)} rows of market-map.csv: segment {lead}" + (f", region {reg[0][0]}" if reg else "") + ". Charlie approves it before the first campaign.") if lead else "No covered segment has rows yet."]
    k.write(ctx, "sell/market-map.md", "\n".join(lines))
    return {"summary": f"Market map: {len(allrows)} companies ({new} new), {calls} register requests, {pending} windows pending.", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
