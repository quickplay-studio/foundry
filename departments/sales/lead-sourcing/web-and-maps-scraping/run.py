"""Web and Maps Scraping: GitHub implementation of departments/sales/lead-sourcing/web-and-maps-scraping/SKILL.md.

Collects local businesses from the Apify Google Maps actor (APIFY_TOKEN, stops at 80 percent of the
free monthly credit) and from directories Charlie has approved in sell/directories.txt (robots.txt
checked first). Business facts only. A Companies House match (optional key) makes a row corporate;
no match means individual, which is never emailed. Credit and skip logs go in sell/raw/maps-state.json.
"""
import csv
import datetime as dt
import io
import json
import re
import urllib.robotparser
from urllib.parse import urlparse

import requests

from foundry import jobkit as k

CH = "https://api.company-information.service.gov.uk"
APIFY = "https://api.apify.com/v2"
ACTOR = "compass~crawler-google-places"
COLS = "company,company_number,domain,website,segment,subscriber_type,contact_name,role,email,email_basis,phone,linkedin_url,source,source_url,collected_on".split(",")
RUNS_PER_JOB = 3


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


def phone44(p):
    d = re.sub(r"\D", "", str(p or ""))
    return "+44" + d[1:] if d.startswith("0") else "+" + d if d.startswith("44") else ""


def host_of(url):
    return re.sub(r"^www\.", "", urlparse(str(url or "")).netloc.lower())


def stem(name):
    return re.sub(r"\b(limited|ltd|plc|llp)\b\.?\s*$", "", re.sub(r"[^a-z0-9 ]", "", str(name).lower())).strip()


def ch_match(key, name, postcode):
    """Companies House match by name and postcode: (number, True) or ("", False)."""
    if not key or not name:
        return "", False
    try:
        r = requests.get(CH + "/search/companies", params={"q": name, "items_per_page": 5}, auth=(key, ""), timeout=20)
        items = r.json().get("items", []) if r.ok else []
    except Exception:  # noqa: BLE001
        return "", False
    pc = re.sub(r"\s", "", str(postcode)).upper()
    for it in items:
        ipc = re.sub(r"\s", "", str((it.get("address") or {}).get("postal_code", ""))).upper()
        if stem(it.get("title")) == stem(name) and pc and ipc == pc and str(it.get("company_type", "")).startswith(("ltd", "plc", "llp", "private-limited")):
            return str(it.get("company_number", "")), True
    return "", False


def apify_usage(token):
    try:
        d = requests.get(f"{APIFY}/users/me/limits", params={"token": token}, timeout=20).json().get("data", {})
        cap = float(d.get("limits", {}).get("maxMonthlyUsageUsd") or 0)
        return float(d.get("current", {}).get("monthlyUsageUsd") or 0) / cap if cap else 1.0
    except Exception:  # noqa: BLE001
        return 1.0  # unknown credit: do not spend


def main(ctx):
    if not b2b(ctx):
        return {"skipped": "no business buyer"}
    icp = get_icp(ctx)
    if not icp:
        return {"skipped": "no ICP yet (sell/icp.md): run icp-definition first"}
    token, ch_key = k.secret("APIFY_TOKEN"), k.secret("COMPANIES_HOUSE_API_KEY")
    directories = [d.strip() for d in (k.read(ctx, "sell/directories.txt", "") or "").splitlines() if d.strip().startswith("http")]
    if not token and not directories:
        return {"skipped": "APIFY_TOKEN missing and no sell/directories.txt (Charlie approves each directory after the terms check)"}
    today = dt.date.today().isoformat()
    state = k.read(ctx, "sell/raw/maps-state.json", {}) or {}
    state.setdefault("runs", [])
    state["skipped"] = []
    segs = [s for s in icp["segments"] if isinstance(s, dict) and s.get("name")]
    rows = {}
    for r in csv.DictReader(io.StringIO(k.read(ctx, "sell/raw/maps.csv", "") or "")):
        rows[(r["domain"] or r["phone"] or r["company"])] = r
    added = 0

    def keep(seg, name, addr, phone, site, source, url, postcode=""):
        nonlocal added
        name = str(name or "").strip()
        if not name:
            return
        dom, ph = host_of(site), phone44(phone)
        ident = dom or ph or name.lower()
        if ident in rows or (ph and any(r["phone"] == ph for r in rows.values())):
            return
        num, corp = ch_match(ch_key, name, postcode)
        rows[ident] = {"company": name, "company_number": num, "domain": dom, "website": site if dom else "", "segment": seg,
                       "subscriber_type": "corporate" if corp else "individual", "contact_name": "", "role": "", "email": "",
                       "email_basis": "", "phone": ph, "linkedin_url": "", "source": source, "source_url": url, "collected_on": today}
        added += 1

    if not token:
        state["skipped"].append("Google Maps step: APIFY_TOKEN missing")
    else:
        for seg in segs:
            pairs = [(kw, reg) for reg in (aslist(seg.get("regions")) or ["UK"]) for kw in aslist(seg.get("keywords"))[:8]]
            for reg in list(dict.fromkeys(reg for _, reg in pairs))[:RUNS_PER_JOB]:
                if len(state["runs"]) >= 200 or sum(1 for r in state["runs"] if r.get("date") == today) >= RUNS_PER_JOB:
                    break
                if f"{seg['name']}|{reg}" in {r.get("key") for r in state["runs"]}:
                    continue
                used = apify_usage(token)
                if used >= 0.8:
                    state["skipped"].append(f"Apify credit at {used:.0%}: stopped at 80 percent")
                    break
                body = {"searchStringsArray": [f"{kw} in {reg}" for kw, r2 in pairs if r2 == reg][:10], "locationQuery": f"{reg}, UK",
                        "maxCrawledPlacesPerSearch": 50 if not state["runs"] else 100, "language": "en"}
                try:
                    items = requests.post(f"{APIFY}/acts/{ACTOR}/run-sync-get-dataset-items", params={"token": token}, json=body, timeout=600).json()
                except Exception as exc:  # noqa: BLE001
                    items = []
                    state["skipped"].append(f"Maps run for {reg} failed: {type(exc).__name__}")
                for it in items if isinstance(items, list) else []:
                    if isinstance(it, dict):  # business facts only: no reviews, no reviewer names
                        keep(seg["name"], it.get("title"), it.get("address"), it.get("phone"), it.get("website"), "google-maps", it.get("url", ""), it.get("postalCode", ""))
                state["runs"].append({"key": f"{seg['name']}|{reg}", "date": today, "credit_used_before": round(used, 3), "places": len(items) if isinstance(items, list) else 0})
        state["terms_read"] = {"url": "https://apify.com/compass/crawler-google-places", "note": "actor terms and credit limit to be checked by Charlie on first run", "date": today}
    for url in directories:
        root = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        rp = urllib.robotparser.RobotFileParser()
        try:
            rp.parse(requests.get(root + "/robots.txt", timeout=15).text.splitlines())
            allowed = rp.can_fetch("*", url)
        except Exception:  # noqa: BLE001
            allowed = False  # cannot read robots.txt: treat as not allowed
        if not allowed:
            state["skipped"].append(f"{host_of(url)}: robots.txt forbids or could not be read")
            continue
        text = k.fetch(url, 12000)
        answer = k.ask("List the businesses on this member-list page. Business facts only, no people. Return JSON only: "
                       "{\"businesses\": [{\"name\": \"...\", \"address\": \"...\", \"phone\": \"...\", \"website\": \"...\", \"postcode\": \"...\"}]}\n\nPAGE\n" + text) if text else None
        for b in (answer.get("businesses") if isinstance(answer, dict) and isinstance(answer.get("businesses"), list) else []):
            if isinstance(b, dict):
                keep(segs[0]["name"] if segs else "", b.get("name"), b.get("address"), b.get("phone"), b.get("website"), host_of(url), url, b.get("postcode", ""))
    if not directories:
        found = [h for h in k.search("trade body member directory UK " + " ".join(aslist(segs[0].get("keywords"))[:2]), 4) if h.get("url")] if segs else []
        if found:
            k.write(ctx, "sell/directories-proposed.txt", "\n".join(h["url"] for h in found) + "\n")
    if not rows and not state["skipped"]:
        return {"skipped": "no places or directory entries found"}
    buf = io.StringIO()
    w = csv.DictWriter(buf, COLS, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(rows.values())
    k.write(ctx, "sell/raw/maps.csv", buf.getvalue())
    k.write(ctx, "sell/raw/maps-state.json", state)
    solo = sum(1 for r in rows.values() if r["subscriber_type"] == "individual")
    return {"summary": f"Maps and directories: {added} new rows ({len(rows)} total, {solo} individual, never emailed). Skipped: {'; '.join(state['skipped'])[:150] or 'none'}.", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
