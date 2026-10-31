"""Lookalike Modelling: GitHub implementation of departments/sales/targeting/lookalike-modelling/SKILL.md.

Plain counting, no machine learning: lift of each feature among customers against the market map,
then the top 200 unseen map companies by matching weight, written to sell/raw/lookalike.csv as
corporate rows (the map holds limited companies, PLCs and LLPs only). Idle below 5 customers, which is
the expected state for a new venture. Customers with good_fit of no (an optional column) are left out.
Customers with no accounts.csv row need account-enrichment first.
"""
import csv
import datetime as dt
import io
import re
from collections import Counter

from foundry import jobkit as k

COLS = ("company,company_number,domain,website,segment,subscriber_type,contact_name,role,email,email_basis,phone,linkedin_url,source,"
        "source_url,collected_on,notes").split(",")
PAGE = "https://find-and-update.company-information.service.gov.uk/company/"
DASH = re.compile(r"\s*[" + chr(0x2013) + chr(0x2014) + r"]\s*")  # model text never carries dashes into files


def b2b(ctx):
    audit = k.read(ctx, "audit.json", {}) or {}
    return "b2b" in (str(ctx["idea"].get("business_model", "")).lower(), str(audit.get("business_model", "")).lower())


def table(ctx, rel):
    return list(csv.DictReader(io.StringIO(k.read(ctx, rel, "") or "")))


def plain(text, n=160):
    return re.sub(r"\s+", " ", DASH.sub(", ", str(text or ""))).strip()[:n]


def age_band(born):
    try:
        yrs = (dt.date.today() - dt.date.fromisoformat(str(born))).days / 365.25
    except ValueError:
        return ""
    return "under3" if yrs < 3 else "3to10" if yrs <= 10 else "over10"


def features(sic, size, born, region, tech):
    sics = [s for s in re.split(r"[;,\s]+", str(sic)) if len(s) >= 3]
    out = {f"sic3:{s[:3]}" for s in sics}
    out |= {f"age:{age_band(born)}"} if age_band(born) else set()
    out |= {f"size:{size}"} if size else set()
    out |= {f"region:{region.lower()}"} if region else set()
    out |= {f"tech:{t}" for t in str(tech).split(";") if t}
    return out


def main(ctx):
    if not b2b(ctx):
        return {"skipped": "no business buyer"}
    customers = [c for c in table(ctx, "sell/customers.csv") if c.get("company_number") and str(c.get("good_fit", "yes")).lower() not in ("no", "n", "false", "0")]
    if len(customers) < 5:
        return {"skipped": "fewer than 5 customers"}
    mapped = table(ctx, "sell/market-map.csv")
    if not mapped:
        return {"skipped": "no sell/market-map.csv: run market-mapping first"}
    accounts = {a["company_number"]: a for a in table(ctx, "sell/accounts.csv") if a.get("company_number")}
    missing = [c["company_number"] for c in customers if c["company_number"] not in accounts]
    if missing:
        return {"skipped": f"{len(missing)} customers have no accounts.csv row: run account-enrichment first"}
    prev = k.read(ctx, "sell/lookalike-model.json", {}) or {}
    try:
        fresh = (dt.date.today() - dt.date.fromisoformat(prev.get("built_on", ""))).days < 30 and len(customers) - int(prev.get("customers", 0)) < 3
    except (ValueError, TypeError):
        fresh = False
    if fresh:
        return {"skipped": f"model is current: built {prev['built_on']} on {prev.get('customers')} customers (rebuild monthly or after 3 new customers)"}
    cust = [features(a["sic"], a["size_band"], a["incorporated_on"], a["region"], a["tech"]) for a in (accounts[c["company_number"]] for c in customers)]
    allmap = [(m, features(m.get("sic_codes", ""), "", m.get("incorporated_on", ""), m.get("region", ""), "")) for m in mapped]
    cc, mc = Counter(f for fs in cust for f in fs), Counter(f for _, fs in allmap for f in fs)
    weights = {}
    for f, n in cc.items():
        if n >= 3 and mc.get(f):
            lift = (n / len(cust)) / (mc[f] / len(allmap))
            if lift >= 1.5:
                weights[f] = round(lift, 2)
    if not weights:
        return {"skipped": "no feature reaches lift 1.5 with 3 customers behind it yet"}
    k.write(ctx, "sell/lookalike-model.json", {"built_on": dt.date.today().isoformat(), "customers": len(customers), "weights": weights})
    seen = {r["company_number"] for r in table(ctx, "sell/leads.csv")}  # suppressed leads stay in leads.csv, so they are covered
    seen |= {c["company_number"] for c in customers}
    total = sum(weights.values())
    scored = sorted(((sum(w for f, w in weights.items() if f in fs) / total, m, [f for f in weights if f in fs]) for m, fs in allmap if m["company_number"] not in seen),
                    key=lambda t: (-t[0], t[1]["company_number"]))
    top = [t for t in scored if t[0] > 0][:200]
    listing = "\n".join(f"{i}: {', '.join(t[2])}" for i, t in enumerate(top[:20]))
    answer = k.ask("For each numbered company write one short line of notes from its matching features only. Add no new facts. "
                   "Return JSON only: {\"notes\": [{\"i\": 0, \"note\": \"...\"}]}\n\n" + listing) if top else None
    notes = {}
    for n in (answer.get("notes") if isinstance(answer, dict) and isinstance(answer.get("notes"), list) else []):
        try:
            notes[int(n["i"])] = plain(n["note"])
        except (KeyError, TypeError, ValueError):
            continue
    out = io.StringIO()
    w = csv.DictWriter(out, COLS, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for i, (score, m, matched) in enumerate(top):
        base = f"lookalike score {score:.2f}; matches {', '.join(matched)}"
        w.writerow({"company": m["company"], "company_number": m["company_number"], "segment": m.get("segment", ""), "subscriber_type": "corporate",
                    "source": "lookalike", "source_url": PAGE + m["company_number"], "collected_on": dt.date.today().isoformat(),
                    "notes": base + (f"; {notes[i]}" if i in notes else "")})
    k.write(ctx, "sell/raw/lookalike.csv", out.getvalue())
    return {"summary": f"Lookalike model from {len(customers)} customers: {len(weights)} weighted features, {len(top)} new target rows.", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
