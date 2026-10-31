"""Sample and Quality Check: GitHub implementation of departments/commerce/sourcing/sample-and-quality-check/SKILL.md.

Writes the sample order sheet, inspection checklist, tests and pass rules before the sample arrives. It never
orders, pays, messages a supplier or gives a verdict: those stay with Charlie.
"""
import datetime as dt

from foundry import jobkit as k

COMMERCE = ("shop", "tiktok-shop", "dropshipping")
BASE = [
    ("Build quality", "Pass: solid, no loose parts. Caution: minor cosmetic flaw. Fail: breaks, sharp edges or loose parts."),
    ("Materials and smell", "Pass: matches the listing, no strong odour. Caution: faint odour that fades in a day. Fail: chemical smell or wrong material."),
    ("Dimensions against the listing", "Pass: within 3 per cent. Caution: 3 to 8 per cent out. Fail: more than 8 per cent out."),
    ("Weight", "Pass: within 5 per cent of the stated weight. Caution: 5 to 10 per cent out. Fail: more than 10 per cent out."),
    ("Finish", "Pass: even finish. Caution: small blemish on one unit. Fail: visible defects on every unit."),
    ("Function over repeated use", "Pass: works every time over 20 uses. Caution: fails once and recovers. Fail: fails twice or stops."),
    ("Packaging damage", "Pass: undamaged. Caution: outer box damaged, product fine. Fail: product damaged by packaging."),
    ("Labelling: name, address, batch, warnings, required markings", "Pass: all present and legible. Caution: legible but incomplete on non-safety items. Fail: any missing required marking (automatic fail)."),
    ("Instructions in English", "Pass: clear English instructions. Caution: poor English but usable. Fail: none or unreadable."),
    ("Fit with the supplier photos", "Pass: matches. Caution: colour or finish differs slightly. Fail: a different product."),
]
TESTS = [("Seven-day use test", "Use it as the buyer would for seven days and note any fault.", "Pass: no fault. Fail: any safety fault or loss of function."),
         ("Wash or wipe test", "Clean it as the instructions say, three times.", "Pass: no damage or colour loss. Fail: damage, peeling or colour run."),
         ("Drop or stress test", "Drop it from table height onto a hard floor twice.", "Pass: no damage. Caution: cosmetic mark. Fail: breaks or becomes unsafe."),
         ("Photograph test", "Photograph it in daylight and under a phone torch.", "Pass: as good as the listing in both. Fail: noticeably worse than the listing.")]


def num(x):
    try:
        return float(str(x).replace("£", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def lst(x):
    return x if isinstance(x, list) else []


def txt(x, n=8):
    return x.strip() if isinstance(x, str) and len(x.strip()) >= n else ""


def main(ctx):
    idea, brain = ctx["idea"], ctx["brain"]
    kind = str(idea.get("kind", "")).lower()
    if kind not in COMMERCE:
        return {"skipped": "not a commerce venture"}
    sup = k.read(ctx, "commerce/suppliers.json") or {}
    byid = {s.get("id"): s for s in lst(sup.get("suppliers")) if isinstance(s, dict)}
    ranked = [byid[i] for i in lst(sup.get("ranking")) if i in byid]
    if not ranked:
        return {"skipped": "no ranked suppliers: needs commerce/suppliers.json from supplier-research"}
    comp_md = k.read(ctx, "commerce/compliance.md") or ""
    if comp_md.strip().upper().startswith("FLAG: STOP"):
        return {"skipped": "marketplace-compliance flag is stop: no sample until it is lifted"}
    shortlist = k.read(ctx, "commerce/shortlist.json") or {}
    prods = [p for p in lst(shortlist.get("products")) if isinstance(p, dict)]
    prod = next((p for p in prods if p.get("id") == shortlist.get("pick")), prods[0] if prods else {})
    budget = ctx.get("budget") or {}
    cap = num(budget.get("sample_cap_gbp") or budget.get("sample_budget_gbp"))
    cap_note = "cap from budget.json"
    if cap is None:
        cap, cap_note = round(0.2 * (num(budget.get("ad_budget")) or num(idea.get("budget_gbp")) or 0), 2), "no sample cap in budget.json: 20 per cent of the ad budget proposed, Charlie approves"

    def cost(s):
        return (s["sample_price_gbp"] if isinstance(s.get("sample_price_gbp"), (int, float)) else 0) + (s["delivery_cost_gbp"] if isinstance(s.get("delivery_cost_gbp"), (int, float)) else 0)
    chosen = ranked[:1]
    if len(ranked) > 1 and cost(ranked[0]) + cost(ranked[1]) <= cap:
        chosen = ranked[:2]
    total = round(sum(cost(s) for s in chosen), 2)
    docs = [str(d) for d in lst(sup.get("documents_to_request"))]
    comp = k.read(ctx, "commerce/compliance.json") or {}
    docs += [str(d) for d in lst(comp.get("documents_to_request"))]
    themes = [str(t) for t in lst(prod.get("complaint_themes"))]
    ans = k.ask("You prepare a sample inspection for a UK online shop. From the complaint themes and compliance notes write product-specific checks and the exact sample variant to order. "
                "Return JSON only: {\"variant\": \"size, colour and quantity (one to three units)\", \"packaging\": \"retail packaging to request\", "
                "\"checks\": [{\"check\": \"...\", \"pass_rule\": \"Pass: ... Caution: ... Fail: ...\"}]}\n"
                f"PRODUCT {prod.get('name', '')}\nTHEMES {themes}\nCOMPLIANCE\n{comp_md[:2500]}\nBUYER\n{brain[:1200]}") or {}
    variant = txt(ans.get("variant")) or "name the exact variant, size and colour from the supplier page before ordering (one to three units)"
    extra = [(str(c.get("check"))[:120], str(c.get("pass_rule"))[:240]) for c in lst(ans.get("checks")) if isinstance(c, dict) and c.get("check") and c.get("pass_rule")][:6]
    extra += [(f"Complaint theme: {t}", "Pass: the sample shows no sign of it. Caution: a minor sign. Fail: the sample shows the complaint clearly.") for t in themes[:3]]
    checks = [{"id": f"c{i}", "check": c, "pass_rule": r, "result": None, "photo": None} for i, (c, r) in enumerate(BASE + extra, 1)]
    checks += [{"id": f"t{i}", "check": f"Test: {n}", "pass_rule": f"{how} {r}", "result": None, "photo": None} for i, (n, how, r) in enumerate(TESTS, 1)]
    today = dt.date.today().isoformat()
    lines = [f"# Sample brief: {prod.get('name', idea.get('title', ctx['slug']))}", "", f"Prepared {today}. Charlie places and pays for every order and gives every verdict. Nothing has been ordered or sent.", "",
             "## 1. Order sheet", f"Sample cap: {cap} GBP ({cap_note}). Total for the order below: {total} GBP.", ""]
    for s in chosen:
        lines += [f"- Supplier: {s.get('name')} ({s.get('url')}), {s.get('country')}", f"  - Variant and quantity: {variant}",
                  f"  - Sample price {s.get('sample_price_gbp')} GBP, delivery {s.get('delivery_cost_gbp')} GBP, delivery time {s.get('delivery_days')} days",
                  f"  - Ask for with it: certificate copies, UK responsible person or importer, retail packaging ({txt(ans.get('packaging')) or 'as sold to the customer'}), barcode"]
    if len(ranked) > 1 and len(chosen) == 1:
        lines.append(f"- Second-ranked supplier {ranked[1].get('name')} is left out: both samples together exceed the cap.")
    if docs:
        lines += ["", "Documents to request:", *[f"- {d}" for d in dict.fromkeys(docs)]]
    if kind == "dropshipping":
        lines += ["", "Dropshipping: the sample is the only way to see the packaging customers receive, so it is never skipped."]
    lines += ["", "## 2. Inspection checklist", "Photograph every unit on arrival: front, back, labels, packaging.", "", "| Id | Check | Pass rule | Result |", "|---|---|---|---|"]
    lines += [f"| {c['id']} | {c['check']} | {c['pass_rule']} | |" for c in checks]
    lines += ["", "## 3. Pass rules", "Written before the sample arrives and not edited afterwards. A missing required marking or an unsafe finding is an automatic fail.",
              "", "Verdict: pass / pass with changes / fail", "Notes:", ""]
    if not comp_md:
        lines.append("compliance.md is missing: run marketplace-compliance and add its required markings to the labelling check before the sample arrives.")
    k.write(ctx, "commerce/sample-brief.md", "\n".join(lines))
    notes = f"Also sampling {chosen[1].get('id')} ({chosen[1].get('name')})." if len(chosen) > 1 else ""
    k.write(ctx, "commerce/sample-results.json", {"product_id": prod.get("id"), "supplier_id": chosen[0].get("id"), "ordered_by": "charlie", "date_ordered": None,
                                                   "date_received": None, "checks": checks, "verdict": None, "notes": notes})
    return {"summary": f"Sample brief for {len(chosen)} supplier(s), {len(checks)} checks, order total {total} GBP. Charlie orders and judges.", "flag": "ok" if comp_md else "caution"}


if __name__ == "__main__":
    k.run(main)
