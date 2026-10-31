"""Expense Categorisation: GitHub implementation of departments/back-office/records/expense-categorisation/SKILL.md.

Rules first (longest match wins, Charlie's confirmed rows outrank them), then the free model in batches of 50
for what is left, then a keyword fallback that never invents a category. Weak rows go to review.md, not
guessed. Card and account numbers never reach a file or a model: any digit run of seven or more is removed.
The yearly check of the HMRC headings is not run here, so the headings below are starting values.
"""
import csv
import datetime as dt
import io
import re

from foundry import jobkit as k
from foundry import util

OFF = "../../office/"
SEED = [("advertising", "Advertising and business entertainment costs"), ("software and online services", "Phone, fax, stationery and other office costs"),
        ("domains and hosting", "Phone, fax, stationery and other office costs"), ("professional fees", "Accountancy, legal and other professional fees"),
        ("payment and bank fees", "Bank, credit card and other financial charges"), ("travel", "Car, van and travel expenses"), ("equipment", "Other business expenses"),
        ("other", "Other business expenses")]
WORDS = {"advertising": ("google ads", "meta ads", "facebook ads", "tiktok ads", "adwords", "advert"), "software and online services": ("openai", "anthropic", "github", "notion", "canva", "netlify", "vercel", "zapier", "software", "subscription"),
         "domains and hosting": ("namecheap", "godaddy", "domain", "hosting", "cloudflare", "hetzner"), "professional fees": ("accountant", "solicitor", "legal", "lawyer"),
         "payment and bank fees": ("stripe fee", "paypal fee", "bank fee", "transaction fee", "card fee"), "travel": ("trainline", "tfl", "uber", "airline", "hotel", "train"),
         "equipment": ("laptop", "monitor", "keyboard", "equipment")}
KIND = (("advert", "ad"), ("software", "tool"), ("domain", "domain"), ("fee", "fee"))
COLS = ["date", "venture", "merchant", "description", "category", "hmrc_heading", "amount", "currency", "receipt", "confirmed"]


def clean(text):
    return re.sub(r"\s+", " ", re.sub(r"\d{7,}", "", str(text or ""))).strip()[:120]


def table(text):
    return [{(h or "").strip().lower(): (v or "").strip() for h, v in r.items() if isinstance(h, str)} for r in csv.DictReader(io.StringIO(text or ""))]


def num(x):
    try:
        return float(re.sub(r"[^0-9.\-]", "", str(x)))
    except ValueError:
        return None


def jlist(ctx, rel):
    data = k.read(ctx, rel, [])
    return [r for r in (data if isinstance(data, list) else []) if isinstance(r, dict)]


def main(ctx):
    slug = ctx["slug"]
    cur = (ctx.get("budget") or {}).get("currency") or "GBP"
    today = util.today()
    cfg = k.read(ctx, OFF + "finance/categories.json", {})
    cfg = cfg if isinstance(cfg, dict) else {}
    cats = [(c, "") if isinstance(c, str) else (c.get("name"), c.get("hmrc_heading", "")) for c in cfg.get("categories", []) if isinstance(c, (str, dict)) and (isinstance(c, str) or c.get("name"))] or SEED
    heading = dict(cats)
    names = [c for c, _ in cats]
    rules = sorted([r for r in cfg.get("rules", []) if isinstance(r, dict) and r.get("match") and r.get("category") in names], key=lambda r: -len(str(r["match"])))
    confirmed = jlist(ctx, OFF + "finance/expenses-confirmed.json")
    by_key = {r.get("key"): r for r in confirmed if r.get("category") in names}
    by_merchant = {str(r.get("merchant", "")).lower(): r for r in confirmed if r.get("merchant") and r.get("category") in names}
    mine, office = jlist(ctx, "finance/expenses.json"), jlist(ctx, OFF + "finance/expenses.json")
    have = {r.get("key") for r in mine + office}
    slugs = [p.name for p in ctx["folder"].parent.iterdir() if p.is_dir()] if ctx["folder"].parent.is_dir() else []
    # 1. new rows only
    incoming, review = [], []
    fin = ctx["folder"] / "finance"
    sources = [(table(k.read(ctx, "finance/spend.csv", "")), slug), (table(k.read(ctx, OFF + "finance/spend-shared.csv", "")), "office")]
    for p in sorted(fin.glob("ads-*.csv")) if fin.is_dir() else []:
        per = {}
        for r in table(k.read(ctx, f"finance/{p.name}", "")):
            if r.get("date") and num(r.get("spend") or r.get("cost")) is not None:
                per[r["date"][:10]] = per.get(r["date"][:10], 0) + num(r.get("spend") or r.get("cost"))
        platform = re.split(r"[-_.]", p.stem[4:])[0] or "ads"
        sources.append(([{"date": d, "amount": f"{a:.2f}", "currency": cur, "merchant": platform, "description": "ads export", "kind": "ad"} for d, a in per.items()], slug))
    for rows, owner in sources:
        for r in rows:
            amt, merchant, desc = num(r.get("amount")), clean(r.get("merchant")), clean(r.get("description"))
            key = f"{r.get('date', '')[:10]}|{amt}|{merchant}|{desc}"
            if key in have:
                continue
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", r.get("date", "")[:10]) or amt is None:
                review.append({"key": key, "why": "no date or amount", "guess": ""})
                continue
            incoming.append({"key": key, "date": r["date"][:10], "amount": amt, "currency": (r.get("currency") or cur).upper(), "merchant": merchant, "description": desc,
                             "venture": owner, "owner": owner, "adsrow": r.get("description") == "ads export"})
    if not incoming and not review:
        return {"skipped": "no new spend rows"}
    # 2 and 3. rules, with Charlie's confirmed rows first
    todo = []
    for r in incoming:
        if r["adsrow"]:  # an ad platform export is advertising by definition
            r.update(category="advertising" if "advertising" in names else "other", confidence=1.0, needs_review=False, confirmed=False)
            continue
        hit = by_key.get(r["key"]) or by_merchant.get(r["merchant"].lower())
        if not hit:
            hit = next((x for f in (r["merchant"], r["description"]) for x in rules if str(x["match"]).lower() in f.lower()), None)
        if hit:
            r.update(category=hit["category"], venture=hit.get("venture") if hit.get("venture") in slugs + ["office"] else r["venture"], confidence=1.0, needs_review=False, confirmed=hit in confirmed)
        else:
            todo.append(r)
    # 4. the free model for the rest, 50 at a time; only categories on the list are accepted
    for lo in range(0, len(todo), 50):
        chunk = todo[lo:lo + 50]
        ans = k.ask("Categorise each spend row. category must be one of: " + ", ".join(names) + ". venture is one of: " + ", ".join(slugs + ["office"]) + ". Give confidence 0 to 1. "
                    'Return JSON only: {"results": [{"index": 0, "category": "advertising", "venture": "office", "confidence": 0.9}]}\n\nROWS\n'
                    + "\n".join(f"{i} | {r['date']} | {r['amount']} {r['currency']} | {r['merchant']} | {r['description']}" for i, r in enumerate(chunk)))
        got = {x.get("index"): x for x in (ans.get("results") if isinstance(ans, dict) and isinstance(ans.get("results"), list) else []) if isinstance(x, dict)}
        for i, r in enumerate(chunk):
            g = got.get(i)
            if g:
                ok = g.get("category") in names
                conf = num(g.get("confidence"))
                r.update(category=g["category"] if ok else "other", confidence=min(max(conf, 0.0), 1.0) if ok and conf is not None else 0.0,
                         venture=g.get("venture") if g.get("venture") in slugs + ["office"] else r["venture"])
            else:  # keyword fallback only: never invents a category
                blob = f"{r['merchant']} {r['description']}".lower()
                cat = next((c for c, words in WORDS.items() if c in names and any(w in blob for w in words)), "other")
                r.update(category=cat, confidence=0.0)
            r.update(needs_review=r["confidence"] < 0.7, confirmed=False)
    # 6. kind for budget-tracking, the receipt link by document index id
    docs = [d for d in jlist(ctx, OFF + "records/documents/index.json") if d.get("type") == "receipt"]
    for r in incoming:
        r["kind"] = next((v for w, v in KIND if w in r["category"]), "other")
        r["receipt"] = next((d.get("id") for d in docs if d.get("date") == r["date"] and util.slugify(r["merchant"])[:8] in util.slugify(str(d.get("counterparty", "")))), None)
        if r["needs_review"]:
            review.append({"key": r["key"], "why": f"{r['merchant']} {r['amount']} {r['currency']} on {r['date']}", "guess": f"{r['category']} ({r['confidence']:.1f})"})
    out_keys = ("key", "date", "amount", "currency", "merchant", "description", "category", "kind", "venture", "confidence", "needs_review", "receipt")
    rows = [{c: r.get(c) for c in out_keys} for r in incoming]
    fresh_ads = {(r["merchant"], r["date"]) for r in incoming if r["adsrow"]}
    replaced = lambda r: r.get("description") == "ads export" and (r.get("merchant"), r.get("date")) in fresh_ads  # a re-export replaces its day
    own = [r for r in mine if not replaced(r)] + [r for r in rows if r["venture"] == slug and r["key"] not in {x["key"] for x in mine}]
    own += [r for r in office if r.get("venture") == slug and r.get("key") not in {x.get("key") for x in own}]
    whole = [r for r in office if not replaced(r)] + rows
    k.write(ctx, "finance/expenses.json", sorted(own, key=lambda r: (str(r.get("date")), str(r.get("key")))))
    k.write(ctx, OFF + "finance/expenses.json", sorted({r.get("key"): r for r in whole}.values(), key=lambda r: (str(r.get("date")), str(r.get("key")))))
    # accountant export per month touched, and the review queue
    conf_keys = {r.get("key") for r in confirmed}
    for month in sorted({r["date"][:7] for r in rows}):
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(COLS)
        for r in sorted((x for x in whole if str(x.get("date"))[:7] == month), key=lambda x: str(x.get("date"))):
            w.writerow([r.get("date"), r.get("venture"), r.get("merchant"), r.get("description", ""), r.get("category"), heading.get(r.get("category"), ""), r.get("amount"), r.get("currency"), r.get("receipt") or "", "yes" if r.get("key") in conf_keys else "no"])
        k.write(ctx, OFF + f"finance/accountant/{month}.csv", buf.getvalue())
    top = sorted(review, key=lambda x: x["why"])[:10]
    k.write(ctx, OFF + "finance/review.md", "\n".join([f"# Spend to confirm, {today}", "", "Ten at most. Put your answers in `expenses-confirmed.json`; they become rules. The job categorises: it does not rule on what is allowable. HMRC headings are starting values, not yet checked.", "",
                                                         *[f"- {x['why']}. Best guess: {x['guess'] or 'none'}" for x in top], *([] if top else ["- nothing to confirm"]), ""]))
    return {"summary": f"{len(rows)} new rows categorised, {len(review)} for review.", "flag": "caution" if review else "ok"}


if __name__ == "__main__":
    k.run(main)
