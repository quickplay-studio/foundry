"""Tech-Stack Detection: GitHub implementation of departments/intelligence/companies/tech-stack-detection/SKILL.md.

For each target account with a domain: one request per page (home, pricing, careers) after robots.txt, header, cookie and
page fingerprints from the table beside this file (no model), DNS over HTTPS, certificate-transparency subdomains,
tools named in job ads, public GitHub org languages. The model only lists gaps from the finished table. Sell-stage: b2b only.
"""
import datetime as dt
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import intelkit as I  # noqa: E402
from foundry import jobkit as k  # noqa: E402

MAX_ACCOUNTS, PAGES, VENDOR_SUBS = 5, ("/", "/pricing", "/careers"), ("support", "help", "status", "app", "go")


def scan(domain, skipped):
    """Fetch each page once if robots.txt allows. Returns header text, cookie names and the pooled page source."""
    headers, cookies, pages = "", [], ""
    for p in PAGES:
        url = f"https://{domain}{p}"
        if not I.allowed(url):
            skipped.append(f"{url}: robots.txt forbids it")
            continue
        r = I.get(url, timeout=25)
        if r is None or not r.ok:
            if p == "/":
                skipped.append(f"{url}: no readable answer")
            continue
        if p == "/":
            headers = "\n".join(f"{kk}: {v}" for kk, v in r.headers.items())
            cookies = [c.name for c in r.cookies]
        pages += "\n" + r.text[:200000]
    return headers, cookies, pages


def main(ctx):
    if not I.is_b2b(ctx):
        return {"skipped": "no business buyer: sell-stage account research runs only for b2b ventures"}
    accts = [a for a in I.accounts(ctx, 50, "sell/accounts/{slug}/tech-stack.json") if a["domain"]][:MAX_ACCOUNTS]
    if not accts:
        return {"skipped": "no unfinished target accounts with a domain in sell/accounts.csv (market-map.csv has no domains)"}
    today, names, done = dt.date.today().isoformat(), [], []
    for acct in accts:
        domain, skipped = acct["domain"], []
        headers, cookies, pages = scan(domain, skipped)
        mx, txt_records = I.dns(domain, "MX"), I.dns(domain, "TXT")
        cnames = {s: v[0] for s in VENDOR_SUBS if (v := I.dns(f"{s}.{domain}", "CNAME"))}
        table = [{**r, "url": f"https://{domain}/"} for r in I.detect_tools(headers, cookies, pages, mx, txt_records, cnames)]
        for r in table:
            if r["evidence"].startswith("dns"):
                r["url"] = f"https://dns.google/resolve?name={domain}"
        subs = I.subdomains(domain)
        if not subs:
            skipped.append("crt.sh: no answer after one retry")
        board, roles = I.jobs(acct["name"], domain)
        known = {r["tool"] for r in table}
        for f in I.fingerprints():
            t = f.get("tool", "")
            hit = next((j for j in roles if re.search(rf"\b{re.escape(t)}\b", j["text"], re.I)), None) if t and t not in known else None
            if hit:
                known.add(t)
                table.append({"category": f.get("category", ""), "tool": t, "evidence": f"job ad: {hit['title']}", "confidence": "medium", "url": hit["url"] or f"https://{domain}/careers"})
        org = domain.split(".")[0]
        langs = Counter(r.get("language") for r in I.lst(I.github(f"/orgs/{org}/repos", {"per_page": 30, "type": "public"})) if isinstance(r, dict) and r.get("language"))
        table += [{"category": "Language", "tool": lang, "evidence": f"public GitHub repos in {org}: {n}", "confidence": "medium", "url": f"https://github.com/{org}"} for lang, n in langs.most_common(3)]
        table = [r for r in table if r.get("evidence")]  # drop anything with no evidence
        a = I.dct(k.ask('Using only this table and the venture, list up to 5 gaps: a missing category, an outdated tool or a manual process implied by job ads. Return JSON only: {"gaps": [{"text": "<gap>", "rows": [0], "touches_venture": true}]}. '
                        "Each gap cites table row numbers. touches_venture is true if the venture's gap or MVP touches it.\n\nVENTURE GAP: " + I.txt(ctx["idea"].get("gap"), 200) + "\nMVP: " + str(ctx["idea"].get("mvp"))[:200] + "\nTABLE\n"
                        + "\n".join(f"{i}: {r['category']} / {r['tool']} ({r['evidence']})" for i, r in enumerate(table)))) if table else {}
        gaps = []
        for g in map(I.dct, I.lst(a.get("gaps"))[:5]):
            idx = [int(i) for i in I.lst(g.get("rows")) if str(i).isdigit() and int(i) < len(table)]
            if I.txt(g.get("text")) and idx:
                gaps.append({"text": I.txt(g["text"], 200), "rows": idx, "touches_venture": g.get("touches_venture") is True})
        base = f"sell/accounts/{acct['slug']}"
        k.write(ctx, f"{base}/tech-stack.json", {"domain": domain, "detected": table, "gaps": gaps, "subdomains": subs[:30], "job_board": board, "skipped": skipped, "checked": today})
        md = [f"# Tech stack: {acct['name']} ({domain})", "", *(I.table(["Category", "Tool", "Evidence", "Confidence"], [(r["category"], r["tool"], r["evidence"], r["confidence"]) for r in table[:25]]) if table else ["No tools detected with evidence."]), "", "## Gaps",
              *([f"- {g['text']} (rows {', '.join(map(str, g['rows']))}){' touches the venture' if g['touches_venture'] else ''}" for g in gaps] or ["- none listed"]), "",
              f"Detection is evidence, not proof: only high confidence rows may be stated as fact in outreach. Checked {today}.", *([f"Skipped: {s}" for s in skipped])]
        k.write(ctx, f"{base}/tech-stack.md", I.cap_words("\n".join(md), 295))
        done.append(f"{acct['name']} {len(table)} tools")
    return {"summary": "Tech stacks: " + "; ".join(done) + ".", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
