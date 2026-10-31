"""TAM / Market Sizing: GitHub implementation of departments/intelligence/markets/tam-market-sizing/SKILL.md.

Official counts (ONS, World Bank, Companies House through the vertical analysis, Nomis) give the top-down buyer
count, rating counts give a bottom-up cross-check, and every sum and the signal are plain functions below.
The model only defines the buyer and proposes the reach ratios, which are written as labelled assumptions.
"""
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import intelkit as I  # noqa: E402
from foundry import jobkit as k  # noqa: E402

WB = "https://api.worldbank.org/v2/country/{c}/indicator/{i}"
ONS_POP = "https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates/timeseries/ukpop/pop"
AGE = {"0-14": "SP.POP.0014.TO.ZS", "15-64": "SP.POP.1564.TO.ZS", "65+": "SP.POP.65UP.TO.ZS"}
CONVERSION = {"low": 0.003, "base": 0.01, "high": 0.03}  # of those reached; free-to-paid starting values
RETENTION, MULTIPLES, DEFAULT_FLOOR = 0.6, {"low": 30, "base": 100, "high": 300}, 6000


def funnel(buyers, revenue, sam_share, reach, conv=CONVERSION):
    """TAM = buyers x annual revenue; SAM = TAM x channel share; SOM = SAM x year-one reach x conversion."""
    tam = buyers * revenue
    sam = tam * sam_share
    return {"tam": round(tam), "sam": round(sam), "som": {c: round(sam * reach * v) for c, v in conv.items()}}


def signal(som_base, floor, ratio):
    if som_base < floor:
        return "fail", f"Base year-one revenue of £{som_base:,} is below the £{floor:,} floor."
    if som_base < 2 * floor or ratio > 5:
        return "warn", f"Base year-one revenue of £{som_base:,} is {som_base / floor:.1f} times the £{floor:,} floor" + ("; the two methods differ by more than 5 times." if ratio > 5 else ".")
    return "pass", f"Base year-one revenue of £{som_base:,} is {som_base / floor:.1f} times the £{floor:,} floor."


def floor_from(money):
    for m in re.finditer(r"£\s?(\d[\d,]*(?:\.\d+)?)\s*(k\b)?\s*(?:/|per|a|each)?\s*(month|mo\b|year)?", str(money), re.I):
        v = float(m.group(1).replace(",", "")) * (1000 if m.group(2) else 1)
        if (m.group(3) or "").lower().startswith("m") and v >= 50:
            return round(v * 12), False
        if v >= 500:
            return round(v), False
    return DEFAULT_FLOOR, True


def ratio(x, lo, hi, default):
    v = I.num(x)
    return min(max(v, lo), hi) if v is not None else default


def wb(country, indicator):
    d = I.get_json(WB.format(c=country, i=indicator), {"format": "json", "mrnev": 1, "per_page": 10})
    return [r for r in I.lst(d[1]) if isinstance(r, dict) and r.get("value")] if isinstance(d, list) and len(d) > 1 else []


def main(ctx):
    vert = k.read(ctx, "validate/vertical-analysis.json")
    if not isinstance(vert, dict):
        return {"skipped": "validate/vertical-analysis.json missing: run vertical-analysis first"}
    idea, skipped, sources, counts, assumptions = ctx["idea"], [], [], [], []
    price_in = k.read(ctx, "validate/pricing-research.json", {})
    a = I.dct(k.ask('Return JSON only: {"buyer": "<one sentence>", "filters": {"country": "UK", "age_band": "", "household_type": "", "business_size": "", "sector": ""}, "base": "people or businesses", '
                    '"age_group": "0-14 or 15-64 or 65+ or all", "extra_filters": [{"name": "<share of the base that has the problem>", "ratio": 0.0, "basis": "<why>"}], "sam_share": {"ratio": 0.0, "reason": "<share reachable through the channels the who implies>"}, '
                    '"reach_share": {"ratio": 0.0, "reason": "<share of that reached in year one>"}}\n\nWHO: ' + I.txt(idea.get("who"), 200) + "\nPROBLEM: " + I.txt(idea.get("problem"), 250) + "\nCHANNELS: " + str(idea.get("channels")) + "\nVERTICAL: " + I.txt(vert.get("vertical"), 200)))
    year = lambda r: str(r.get("date", "")) or "latest"  # noqa: E731
    # top-down count
    base_kind = "businesses" if str(a.get("base")).startswith("business") or I.is_b2b(ctx) else "people"
    base = None
    if base_kind == "businesses" and int(I.dct(vert.get("evidence")).get("companies") or 0) > 0:
        base = int(vert["evidence"]["companies"])
        counts.append({"name": "UK active companies in the sector", "value": base, "year": "current register", "source": "https://find-and-update.company-information.service.gov.uk/advanced-search"})
    elif base_kind == "businesses":
        d = I.dct(I.get_json("https://www.nomisweb.co.uk/api/v01/dataset/NM_141_1.data.json", {"geography": "2092957697", "industry": "37748736", "employment_sizeband": 0, "legal_status": 0, "measures": 20100, "time": "latest", "select": "obs_value"}))
        ov = I.dct(I.lst(d.get("obs"))[0] if I.lst(d.get("obs")) else {}).get("obs_value")
        v = I.num(I.dct(ov).get("value") if isinstance(ov, dict) else ov)
        if v:
            base = int(v)
            counts.append({"name": "UK VAT or PAYE registered businesses, all sectors", "value": base, "year": "latest", "source": "https://www.nomisweb.co.uk/query/construct/summary.asp?mode=construct&version=0&dataset=141"})
        else:
            skipped.append("nomis: no business count returned")
    else:
        pop = I.lst(I.dct(I.get_json(ONS_POP + "/data")).get("years"))
        if pop and I.num(pop[-1].get("value")):
            base = int(I.num(pop[-1]["value"]))
            counts.append({"name": "UK population (ONS mid-year estimate)", "value": base, "year": str(pop[-1].get("date") or pop[-1].get("year")), "source": ONS_POP})
        else:
            rows = wb("GBR", "SP.POP.TOTL")
            if rows:
                base = int(rows[0]["value"])
                counts.append({"name": "UK population (World Bank)", "value": base, "year": year(rows[0]), "source": "https://data.worldbank.org/indicator/SP.POP.TOTL?locations=GB"})
            else:
                skipped.append("ons and world bank: no population returned")
    if base is None:
        return {"skipped": "no official count could be fetched (ONS, World Bank, Nomis, Companies House): " + "; ".join(skipped)}
    buyers, filters = float(base), []
    grp = str(a.get("age_group", "all"))
    if base_kind == "people" and grp in AGE and (rows := wb("GBR", AGE[grp])):
        r = rows[0]["value"] / 100
        buyers *= r
        counts.append({"name": f"Share of UK population aged {grp}", "value": round(r, 4), "year": year(rows[0]), "source": f"https://data.worldbank.org/indicator/{AGE[grp]}?locations=GB"})
    for f in [f for f in map(I.dct, I.lst(a.get("extra_filters")))][:3]:
        r = ratio(f.get("ratio"), 0.001, 1, None)
        if r is not None and I.txt(f.get("name")):
            buyers *= r
            filters.append(f)
            assumptions.append({"name": I.txt(f["name"], 80), "value": r, "basis": I.txt(f.get("basis"), 160) or "model estimate", "low": r * 0.5, "high": min(r * 2, 1)})
    if not filters:
        skipped.append("no share-of-base filter proposed: the buyer count is the whole base, an upper bound")
    second = [r for r in wb("US;CA;AU;IE;NZ", "SP.POP.TOTL")] if base_kind == "people" else []
    if second:
        counts.append({"name": "Second market population (US, CA, AU, IE, NZ), not in the funnel", "value": int(sum(r["value"] for r in second)), "year": year(second[0]), "source": "https://data.worldbank.org/indicator/SP.POP.TOTL?locations=US-CA-AU-IE-NZ"})
    counts = [c for c in counts if str(c.get("source", "")).startswith("http")]  # a figure with no source link is rejected
    # price and model
    band, model = I.dct(price_in).get("band") or {}, ""
    if I.num(band.get("base")):
        monthly, model, factor, price_src = I.num(band["base"]), str(band.get("model", "")), 1.0 if "one-off" in str(band.get("model", "")) else RETENTION, "pricing band base"
    elif I.lst(vert.get("paid_prices")):
        paid = sorted(vert["paid_prices"])
        monthly, factor, price_src = paid[len(paid) // 2] / 12, 1.0, "median paid app price, one purchase a year"
    else:
        hoped = I.unit_price(idea.get("money"))
        if not hoped:
            return {"skipped": "no price: no pricing band, no paid prices in the vertical analysis and no unit price in the money line"}
        monthly, factor, price_src = hoped, RETENTION, "money line price"
    revenue = monthly * 12 * factor
    assumptions.append({"name": "Revenue per buyer a year", "value": round(revenue, 2), "basis": f"{price_src}: £{monthly:.2f} x 12 x {factor} ({'purchases a year' if factor == 1.0 else 'retention factor, assumed'})", "low": revenue * 0.7, "high": revenue * 1.3})
    sam_s, reach = I.dct(a.get("sam_share")), I.dct(a.get("reach_share"))
    sam_share, reach_share = ratio(sam_s.get("ratio"), 0.01, 1, 0.15), ratio(reach.get("ratio"), 0.001, 0.5, 0.05)
    assumptions += [{"name": "SAM share of TAM", "value": sam_share, "basis": I.txt(sam_s.get("reason"), 160) or "default 0.15, no model answer", "low": sam_share * 0.5, "high": min(sam_share * 2, 1)},
                    {"name": "Year-one reach share of SAM", "value": reach_share, "basis": I.txt(reach.get("reason"), 160) or "default 0.05, no model answer", "low": reach_share * 0.5, "high": min(reach_share * 2, 0.5)},
                    {"name": "Conversion of those reached", "value": CONVERSION["base"], "basis": "starting value for free-to-paid, 0.3 percent low and 3 percent high", "low": CONVERSION["low"], "high": CONVERSION["high"]}]
    out = funnel(buyers, revenue, sam_share, reach_share)
    # bottom-up cross-check
    rated = [I.dct(c).get("rating_count") for c in I.lst(I.dct(k.read(ctx, "validate/competitor-teardown.json", {})).get("competitors"))] or [I.dct(r).get("rating_count") for r in I.lst(I.dct(I.dct(vert.get("evidence")).get("app_store")).get("top"))]
    total_ratings = sum(int(I.num(x, 0) or 0) for x in rated)
    bottom = {c: total_ratings * m for c, m in MULTIPLES.items()}
    sizes = [x for x in (buyers, bottom["base"]) if x > 0]
    gap = max(sizes) / min(sizes) if len(sizes) == 2 else 1.0
    lower = "top-down" if len(filters) > 1 else "bottom-up"
    floor, floor_default = floor_from(idea.get("money"))
    sig, reason = signal(out["som"]["base"], floor, gap)
    confidence = "high" if len(counts) >= 2 and total_ratings and filters else "medium" if filters or total_ratings else "low"
    assumptions.append({"name": "Users per rating (bottom-up only)", "value": MULTIPLES["base"], "basis": "assumption: 100 users per App Store rating, bounds 30 and 300", "low": 30, "high": 300})
    biggest = max(assumptions, key=lambda x: x["high"] / max(x["low"], 1e-9))["name"]
    today = dt.date.today().isoformat()
    md = [f"# TAM and market sizing: {I.txt(idea.get('title'), 80)}", "", f"Signal: {sig}. {reason} Confidence: {confidence}.", "", f"Buyer: {I.txt(a.get('buyer'), 250) or I.txt(idea.get('who'), 200)} Filters: {I.txt(a.get('filters'), 200)}", "",
          *I.table(["Stage", "GBP a year"], [("TAM", f"{out['tam']:,}"), ("SAM", f"{out['sam']:,}"), ("SOM low", f"{out['som']['low']:,}"), ("SOM base", f"{out['som']['base']:,}"), ("SOM high", f"{out['som']['high']:,}")]), "",
          "## Counts", *[f"- {c['name']}: {c['value']:,} ({c['year']}) {c['source']}" if isinstance(c["value"], int) else f"- {c['name']}: {c['value']} ({c['year']}) {c['source']}" for c in counts], f"- Buyers after filters: {int(buyers):,}", "", "## Assumptions",
          *[f"- {x['name']}: {x['value']:.4g}. {x['basis']}" for x in assumptions], "", "## Cross-check",
          f"Bottom-up from {total_ratings:,} ratings at {MULTIPLES['low']}, {MULTIPLES['base']} and {MULTIPLES['high']} users each gives {bottom['low']:,} to {bottom['high']:,} users, against {int(buyers):,} buyers top-down: a {gap:.1f} times gap." + (f" The {lower} figure is the lower-confidence one." if gap > 5 else ""),
          "", f"Moves the number most: {biggest}.", f"Floor: £{floor:,}" + (" (default, the money line gave none)." if floor_default else " from the money line."), *([f"- {s}" for s in skipped]), "", f"Checked on {today}."]
    k.write(ctx, "validate/tam-market-sizing.md", I.cap_words("\n".join(md), 395))
    k.write(ctx, "validate/tam-market-sizing.json", {
        "job": "tam-market-sizing", "signal": sig, "confidence": confidence, "reason": reason, "sources": [c["source"] for c in counts], "buyer": {"definition": I.txt(a.get("buyer"), 250), "filters": a.get("filters") if isinstance(a.get("filters"), dict) else {}, "base": base_kind},
        "counts": counts, "tam": out["tam"], "sam": out["sam"], "som": out["som"], "floor": floor, "floor_is_default": floor_default, "assumptions": assumptions,
        "inputs": {"buyers": round(buyers), "revenue_per_buyer": round(revenue, 2), "sam_share": sam_share, "reach_share": reach_share, "conversion": CONVERSION},
        "bottom_up": {"ratings": total_ratings, "users": bottom, "gap": round(gap, 2), "lower_confidence": lower if gap > 5 else None}, "skipped": skipped, "checked_on": today})
    return {"summary": f"TAM and sizing: {sig}. {reason}", "flag": "clear" if sig == "pass" else "caution"}


if __name__ == "__main__":
    k.run(main)
