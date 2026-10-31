"""Network Mapping: GitHub implementation of departments/intelligence/people/network-mapping/SKILL.md.

For an account with person sheets (one account per run): adds Charlie and, if he supplied sell/network/my-contacts.csv, his
contacts as first-degree edges (origin: from Charlie's contacts), adds public edges (Companies House appointments, funding.json
investors, co-appearance in capped searches), scores edge strength in code, runs breadth-first search up to 3 hops and ranks the
paths. The model writes one line per top path from the edge evidence, and code drops any line naming someone not in the graph.
Not run: Hacker News reply threads and GitHub co-contribution, which need handles the person sheets do not hold.
Writes nothing unless the folder is in the private data checkout. Sell-stage: b2b only.
"""
import datetime as dt
import re
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import intelkit as I  # noqa: E402
from foundry import jobkit as k  # noqa: E402

MAX_HOPS, TOP, CREDIT_CAP = 3, 5, 15
ME, CONTACTS = "Charlie", "from Charlie's contacts"


def strength(kind, started, ended, today, dissolved=False):
    """3 for a current shared role or direct reply thread, 2 for a past role or event in the last 3 years, 1 for the same group or
    conference; an edge older than 5 years drops one point; a dissolved shared company counts as 1."""
    if dissolved:
        return 1
    def age(d):
        try:
            return (today - dt.date.fromisoformat(str(d)[:10])).days
        except ValueError:
            return None

    last = ended or ""
    base = 3 if kind in ("role", "reply") and not last else 2 if last and (age(last) or 9999) <= 3 * 365 else 1
    ref = age(last or started or "")
    return max(1, base - (1 if ref is not None and ref > 5 * 365 else 0))


def find_paths(edges, start, target, max_hops=MAX_HOPS):
    """Breadth-first search over simple paths, at most max_hops edges. Ranked by fewest hops, then strongest weakest edge, then recency."""
    adj = {}
    for e in edges:
        adj.setdefault(e["from"], []).append((e["to"], e))
        adj.setdefault(e["to"], []).append((e["from"], e))
    out, queue = [], deque([([start], [])])
    while queue:
        nodes, used = queue.popleft()
        if nodes[-1] == target and used:
            out.append({"nodes": nodes, "hops": len(used), "weakest_edge": min(e["strength"] for e in used), "recency": max((e.get("date") or "") for e in used), "edges": used})
            continue
        if len(used) < max_hops:
            for nxt, e in adj.get(nodes[-1], []):
                if nxt not in nodes:
                    queue.append((nodes + [nxt], used + [e]))
    return sorted(out, key=lambda p: (p["hops"], -p["weakest_edge"], "".join(chr(255 - ord(c)) for c in p["recency"])))[:20]


def main(ctx):
    if not I.is_b2b(ctx):
        return {"skipped": "no business buyer: sell-stage research runs only for b2b ventures"}
    if not I.private_repo(ctx):
        return {"skipped": "venture folder is not in the private data checkout: contact data never goes to a public repo"}
    accts = [f.parent.parent.name for f in sorted((ctx["folder"] / "sell" / "accounts").glob("*/people/*.json")) if not (f.parent.parent / "network.json").exists()]
    if not accts:
        return {"skipped": "no account with person sheets and no network.json yet: run person-research first"}
    acct, today = accts[0], dt.date.today()
    base = f"sell/accounts/{acct}"
    sheets = [I.dct(k.read(ctx, f"{base}/people/{p.name}")) for p in sorted((ctx["folder"] / base / "people").glob("*.json"))]
    committee = I.dct(k.read(ctx, f"{base}/committee.json"))
    company = I.txt(I.dct(I.dct(k.read(ctx, f"{base}/deep-dive.json")).get("entity")).get("name"), 100) or acct.replace("-", " ").title()
    nodes, edges = {ME: {"type": "person", "name": ME}, company: {"type": "company", "name": company}}, []

    def edge(a, b, kind, strength_, date, url, origin="public"):
        nodes.setdefault(a, {"type": "person", "name": a})
        nodes.setdefault(b, {"type": "person", "name": b})
        edges.append({"from": a, "to": b, "type": kind, "strength": strength_, "date": date or "", "evidence_url": url, "origin": origin})

    targets = []
    for s in sheets + [dict(p, name=p.get("name")) for p in map(I.dct, I.lst(committee.get("people")))]:
        n = I.txt(s.get("name"), 80)
        if n and n not in targets and s.get("identity_confidence", "confirmed") == "confirmed":
            targets.append(n)
            nodes[n] = {"type": "person", "name": n, "role": I.txt(s.get("role") or s.get("title"), 60)}
            edge(n, company, "role", 3, "", (I.lst(s.get("sources")) or [I.txt(s.get("source") or s.get("url"))])[0] or "")
    skipped = ["hacker news replies and github co-contribution: no handles on the person sheets"]
    # Charlie's own contacts, supplied by him and never fetched
    for r in I.read_csv(ctx, "sell/network/my-contacts.csv"):
        r = {kk.strip().lower(): v for kk, v in r.items()}
        n = (I.txt(r.get("first name")) + " " + I.txt(r.get("last name"))).strip()
        if n:
            edge(ME, n, "contact", 3, "", "", CONTACTS)
            if I.company_key(r.get("company", "")) and I.company_key(r.get("company", "")) == I.company_key(company):
                edge(n, company, "role", 3, "", "", CONTACTS)
            elif I.txt(r.get("company")):
                nodes.setdefault(I.txt(r["company"]), {"type": "company", "name": I.txt(r["company"])})
                edge(n, I.txt(r["company"]), "role", 3, "", "", CONTACTS)
    # public edges: Companies House appointments, funding investors
    if k.secret("COMPANIES_HOUSE_API_KEY"):
        for t in targets[:6]:
            for o in map(I.dct, I.lst(I.dct(I.ch_get("/search/officers", {"q": t, "items_per_page": 2})).get("items"))[:1]):
                link = I.dct(o.get("links")).get("self", "")
                for ap in map(I.dct, I.lst(I.dct(I.ch_get(link)).get("items") if link else [])[:15]):
                    co = I.txt(I.dct(ap.get("appointed_to")).get("company_name"), 100)
                    if co and I.company_key(o.get("title", "")) == I.company_key(t):
                        nodes.setdefault(co, {"type": "company", "name": co})
                        edge(t, co, "role", strength("role", ap.get("appointed_on"), ap.get("resigned_on"), today, I.dct(ap.get("appointed_to")).get("company_status") == "dissolved"), ap.get("resigned_on") or ap.get("appointed_on"),
                             "https://find-and-update.company-information.service.gov.uk" + link)
    else:
        skipped.append("companies house appointments: no key")
    for r in map(I.dct, I.lst(I.dct(k.read(ctx, f"{base}/funding.json")).get("rounds"))):
        for inv in I.lst(r.get("investors"))[:6]:
            nodes.setdefault(I.txt(inv, 60), {"type": "company", "name": I.txt(inv, 60)})
            edge(company, I.txt(inv, 60), "investor", 2, r.get("date"), (I.lst(r.get("sources")) or [""])[0])
    credits, people = I.Credits(CREDIT_CAP), [n for n, v in nodes.items() if v["type"] == "person" and n != ME]
    for t in targets[:5]:
        for res in credits.search(f'"{t}" {company} speaker OR podcast OR panel', 4)[:3]:
            text = res.get("title", "") + " " + res.get("content", "")
            for other in [p for p in people if p != t and I.contains(text, p)]:
                ev = f"event: {I.txt(res.get('title'), 50)}"
                nodes.setdefault(ev, {"type": "event", "name": ev})
                edge(t, ev, "co-appearance", 1, "", res.get("url", ""))
                edge(other, ev, "co-appearance", 1, "", res.get("url", ""))
    paths = []
    for t in targets:
        for p in find_paths(edges, ME, t)[:TOP]:
            paths.append({**p, "target": t})
    paths = sorted(paths, key=lambda p: (p["hops"], -p["weakest_edge"]))[:TOP]
    a = I.dct(k.ask('Write one line per path saying why it might open a door, from the edge evidence only. A connection is not a relationship: say so where the tie is weak. Return JSON only: {"reasons": [{"path": 0, "reason": "<one line>"}]}\n\n'
                    + "\n".join(f"{i}: " + " > ".join(p["nodes"]) + " | " + "; ".join(f"{e['type']} strength {e['strength']} {e['origin']}" for e in p["edges"]) for i, p in enumerate(paths)))) if paths else {}
    reasons = {int(I.num(r.get("path"), -1)): I.txt(r.get("reason"), 200) for r in map(I.dct, I.lst(a.get("reasons")))}
    low = {n.lower() for n in nodes}
    for i, p in enumerate(paths):
        r = reasons.get(i, "")
        names = re.findall(r"[A-Z][a-z]+(?: [A-Z][a-z]+)+", r)
        p["reason"] = r if r and all(n.lower() in " ".join(low) for n in names) else "Path " + " > ".join(p["nodes"]) + f", {p['hops']} hops, weakest tie strength {p['weakest_edge']}."
    out_paths = [{"nodes": p["nodes"], "hops": p["hops"], "weakest_edge": p["weakest_edge"], "reason": p["reason"]} for p in paths]
    k.write(ctx, f"{base}/network.json", {"nodes": [{"id": n, **v} for n, v in nodes.items()], "edges": edges, "paths": out_paths, "skipped": skipped, "built": today.isoformat()})
    md = [f"# Network paths into {company}", "", "A connection is not a relationship. Edges marked `from Charlie's contacts` are his own; the rest are public.", "",
          *(sum(([f"{i}. {' > '.join(p['nodes'])} ({p['hops']} hops, weakest tie {p['weakest_edge']})", f"   {p['reason']}", "   " + " ".join(e["evidence_url"] for e in p["edges"] if e["evidence_url"])] for i, p in enumerate(paths, 1)), []) or [f"No path within {MAX_HOPS} hops."]),
          "", "## Not run", *[f"- {s}" for s in skipped], "", f"Built {today.isoformat()}. Charlie marks each real edge `confirmed` in the pull request before warm-path-finding runs."]
    k.write(ctx, f"{base}/network.md", I.cap_words("\n".join(md), 450))
    return {"summary": f"Network for one account: {len(nodes)} nodes, {len(edges)} edges, {len(paths)} paths within {MAX_HOPS} hops.", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
