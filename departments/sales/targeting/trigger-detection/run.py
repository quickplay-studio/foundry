"""Trigger Detection: GitHub implementation of departments/sales/targeting/trigger-detection/SKILL.md.

Polls up to 300 watched companies (tier A and B leads, else the first slice of the market map) for
filings and officers (COMPANIES_HOUSE_API_KEY, skipped when missing), open roles that match the ICP
keywords, Google News RSS items that name the company, and tech stack changes for tier A. Every hit
carries an evidence_url the job fetched, or it is dropped. Strength: high, medium or low; expiry is 60
days after the event. Appends to sell/triggers.csv, deduped on company_number, trigger_type, evidence_url.
"""
import csv
import datetime as dt
import io
import json
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

import requests

from foundry import jobkit as k

CH = "https://api.company-information.service.gov.uk"
PUBLIC = "https://find-and-update.company-information.service.gov.uk/company/"
COLS = "date,company_number,domain,trigger_type,strength,evidence_url,summary,expires_on".split(",")
FILING = {"SH01": ("share-allotment", "high"), "MR01": ("new-charge", "medium"), "AD01": ("address-change", "medium")}
JOBWORD = re.compile(r"vacanc|apply|hiring|recruit|engineer|developer|manager|analyst|officer|executive|director|assistant", re.I)
CAP, WINDOW, BUDGET_S = 300, 60, 20 * 60
DASH = re.compile(r"\s*[" + chr(0x2013) + chr(0x2014) + r"]\s*")  # model text never carries dashes into files


def b2b(ctx):
    audit = k.read(ctx, "audit.json", {}) or {}
    return "b2b" in (str(ctx["idea"].get("business_model", "")).lower(), str(audit.get("business_model", "")).lower())


def table(ctx, rel):
    return list(csv.DictReader(io.StringIO(k.read(ctx, rel, "") or "")))


def ch_get(key, path):
    time.sleep(0.5)  # 600 requests per five minutes at last check
    try:
        r = requests.get(CH + path, auth=(key, ""), timeout=20)
        return r.json() if r.ok else {}
    except Exception:  # noqa: BLE001
        return {}


def recent(day, today):
    try:
        return 0 <= (today - dt.date.fromisoformat(str(day)[:10])).days <= WINDOW
    except ValueError:
        return False


def keywords(ctx):
    icp = k.read(ctx, "sell/icp.json", None)
    words = [w for s in (icp or {}).get("segments", []) if isinstance(s, dict) for w in (s.get("keywords") or []) if isinstance(w, str)] if isinstance(icp, dict) else []
    if not words:
        for block in re.findall(r"```json\s*(.*?)```", k.read(ctx, "sell/icp.md", "") or "", re.S):
            try:
                words += [w for s in json.loads(block).get("segments", []) for w in s.get("keywords", [])]
            except (ValueError, AttributeError, TypeError):
                continue
    return list(dict.fromkeys(w.lower() for w in words if isinstance(w, str)))


def main(ctx):
    if not b2b(ctx):
        return {"skipped": "no business buyer"}
    leads, mapped = table(ctx, "sell/leads.csv"), table(ctx, "sell/market-map.csv")
    watch = [{"num": r["company_number"], "dom": r["domain"], "name": r["company"], "tier": r["tier"]} for r in leads
             if r["tier"] in ("A", "B") and r["suppressed"] != "yes" and (r["company_number"] or r["domain"])]
    if not watch:
        watch = [{"num": m["company_number"], "dom": "", "name": m["company"], "tier": ""} for m in mapped[:200]]
    watch = list({w["num"] or w["dom"]: w for w in watch}.values())[:CAP]
    if not watch:
        return {"skipped": "nothing to watch: no tier A or B leads and no sell/market-map.csv"}
    today, key, words = dt.date.today(), k.secret("COMPANIES_HOUSE_API_KEY"), keywords(ctx)
    state = k.read(ctx, "sell/triggers-state.json", {}) or {}
    old = table(ctx, "sell/triggers.csv")
    seen = {(t["company_number"], t["trigger_type"], t["evidence_url"]) for t in old}
    accounts = {a["domain"]: a for a in table(ctx, "sell/accounts.csv") if a.get("domain")}
    try:
        rules = json.loads((Path(__file__).resolve().parents[2] / "enrichment" / "account-enrichment" / "tech-fingerprints.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        rules = {}
    new, started = [], time.monotonic()

    def hit(w, kind, strength, url, summary, day):
        ident = (w["num"], kind, url)
        fetched = bool(url) and (url.startswith("https://news.google.com/rss") or bool(k.fetch(url, 500)))  # the feed itself counts for news
        if ident in seen:
            return True
        if not fetched:
            return False  # no fetched evidence, no trigger
        seen.add(ident)
        expiry = (dt.date.fromisoformat(day[:10]) + dt.timedelta(days=WINDOW)).isoformat()
        new.append({"date": day[:10], "company_number": w["num"], "domain": w["dom"], "trigger_type": kind, "strength": strength, "evidence_url": url,
                    "summary": " ".join(DASH.sub(", ", summary).split()[:20]), "expires_on": expiry})
        return True

    for w in watch:
        if time.monotonic() - started > BUDGET_S:
            break
        st = state.setdefault(w["num"] or w["dom"], {})
        if key and w["num"]:
            known_o, known_f = set(st.get("officers", [])), set(st.get("filings", []))
            for o in (ch_get(key, f"/company/{w['num']}/officers").get("items") or []):
                oid = f"{o.get('name', '')}|{o.get('appointed_on', '')}"
                fresh = o.get("officer_role") == "director" and not o.get("resigned_on") and recent(o.get("appointed_on"), today) and oid not in known_o
                if not fresh or hit(w, "new-director", "high", f"{PUBLIC}{w['num']}/officers#{quote(oid)}", f"New director appointed on {o.get('appointed_on')}.", o["appointed_on"]):
                    known_o.add(oid)  # a hit without fetched evidence stays unknown and is retried next run
            for f in (ch_get(key, f"/company/{w['num']}/filing-history").get("items") or []):
                fresh = f.get("type") in FILING and recent(f.get("date"), today) and f.get("transaction_id") not in known_f
                if not fresh or hit(w, *FILING[f["type"]], f"{PUBLIC}{w['num']}/filing-history#{f['transaction_id']}", f"Filing {f['type']}: {f.get('description', 'filing')}", f["date"]):
                    known_f.add(f.get("transaction_id"))
            st["officers"], st["filings"] = sorted(known_o), sorted(x for x in known_f if x)
        step = 7 if w["tier"] == "A" else 14
        try:
            due = (today - dt.date.fromisoformat(st.get("hiring_checked", ""))).days >= step
        except ValueError:
            due = True
        if w["dom"] and words and due:
            st["hiring_checked"] = today.isoformat()
            for path in ("careers", "jobs"):
                url = f"https://{w['dom']}/{path}"
                text = k.fetch(url, 8000)
                found = [m.group(0) for m in (re.search(r".{0,50}\b" + re.escape(x) + r"\b.{0,50}", text, re.I) for x in words) if m and JOBWORD.search(m.group(0))]
                if found:
                    hit(w, "hiring", "high", url, "Open role matching ICP keyword: " + found[0], today.isoformat())
                    break
        if w["name"]:
            stem = re.sub(r"\b(limited|ltd|plc|llp)\b\.?\s*$", "", w["name"].lower()).strip()
            feed = f"https://news.google.com/rss/search?q={quote(chr(34) + w['name'] + chr(34) + ' (raises OR hires OR appoints OR launches OR acquires)')}&hl=en-GB&gl=GB&ceid=GB:en"
            try:
                items = ET.fromstring(requests.get(feed, timeout=20).content).findall(".//item") if len(stem) >= 4 else []
            except Exception:  # noqa: BLE001
                items = []
            for it in items[:5]:
                title, link = (it.findtext("title") or ""), (it.findtext("link") or "")
                try:
                    day = dt.datetime.strptime((it.findtext("pubDate") or "")[:16], "%a, %d %b %Y").date().isoformat()
                except ValueError:
                    continue
                if stem in title.lower() and recent(day, today):
                    big = re.search(r"rais|funding|invest|appoint|new (ceo|md|chief)", title, re.I)
                    hit(w, "funding-news" if big and re.search(r"rais|funding|invest", title, re.I) else "leadership-news" if big else "news", "high" if big else "medium", link, title, day)
        if w["tier"] == "A" and w["dom"] in accounts and accounts[w["dom"]]["tech"] and rules:
            try:
                html = requests.get(f"https://{w['dom']}/", timeout=20, headers={"User-Agent": "Mozilla/5.0 (Foundry research bot)"})
                body = (html.text[:200000] + "\n" + "\n".join(f"{a}: {b}" for a, b in html.headers.items())).lower() if html.ok else ""
            except Exception:  # noqa: BLE001
                body = ""
            had = set(accounts[w["dom"]]["tech"].split(";"))
            now = {t for t, pats in rules.items() if any(p in body for p in pats)}
            if body and now and (now - had or (had & set(rules)) - now):
                hit(w, "stack-change", "low", f"https://{w['dom']}/", f"Stack tags changed: added {sorted(now - had)}, removed {sorted((had & set(rules)) - now)}.", today.isoformat())
    out = io.StringIO()
    wr = csv.DictWriter(out, COLS, lineterminator="\n", extrasaction="ignore")
    wr.writeheader()
    wr.writerows(old + new)
    k.write(ctx, "sell/triggers.csv", out.getvalue())
    k.write(ctx, "sell/triggers-state.json", state)
    note = "" if key else " Filings step skipped: COMPANIES_HOUSE_API_KEY missing."
    return {"summary": f"Triggers: {len(new)} new hits across {len(watch)} watched companies ({sum(1 for t in new if t['strength'] == 'high')} high).{note}", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
