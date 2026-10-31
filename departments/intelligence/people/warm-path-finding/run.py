"""Warm-Path Finding: GitHub implementation of departments/intelligence/people/warm-path-finding/SKILL.md.

Reads network.json after Charlie has marked real edges `confirmed`, keeps only paths whose first hop is confirmed or comes from
his own contacts, ranks them in code, and has the model write the one-page brief from the graph and notes only. Code removes any
name or link in the brief that is not in network.json. Fetches nothing, sends nothing, messages no one and opens no pull request.
Refuses to run when no edge carries `confirmed`. Sell-stage: b2b ventures only.
"""
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import intelkit as I  # noqa: E402
from foundry import jobkit as k  # noqa: E402

ME, CONTACTS, MAX_WARM_HOPS = "Charlie", "from Charlie's contacts", 2


def warm_paths(net, problem):
    """Paths whose first hop is confirmed or from Charlie's contacts, ranked: fewest hops, strongest weakest edge, most recent, relevant middle role."""
    nodes = {n["id"]: n for n in map(I.dct, I.lst(net.get("nodes"))) if n.get("id")}
    ok = lambda e: e.get("confirmed") is True or e.get("origin") == CONTACTS  # noqa: E731
    out = []
    for p in map(I.dct, I.lst(net.get("paths"))):
        names = [str(n) for n in I.lst(p.get("nodes"))]
        if len(names) < 2:
            continue
        # edge list for this path from the full edge set
        used = []
        for a, b in zip(names, names[1:]):
            es = [e for e in map(I.dct, I.lst(net.get("edges"))) if {e.get("from"), e.get("to")} == {a, b}]
            used.append(max(es, key=lambda e: (ok(e), e.get("strength", 0))) if es else {})
        if not used or not ok(used[0]) or not all(used):
            continue
        mid = names[1] if len(names) > 2 else ""
        rel = len(set(I.keywords(nodes.get(mid, {}).get("role", ""), 8)) & set(I.keywords(problem, 20)))
        out.append({"nodes": names, "hops": len(used), "weakest": min(int(e.get("strength", 1)) for e in used), "recent": max(str(e.get("date", "")) for e in used), "relevant": rel,
                    "edges": used, "target": names[-1]})
    return sorted(out, key=lambda p: (p["hops"], -p["weakest"], "".join(chr(255 - ord(c)) for c in p["recent"]), -p["relevant"]))


def clean(text, known):
    """Drop a line that names someone outside the graph (a run of capitalised words with unknown words in it) or links to a URL not in network.json."""
    kept = []
    for line in str(text or "").splitlines():
        toks, runs, run = line.split(), [], []
        for i, t in enumerate(toks):
            w = re.sub(r"[^A-Za-z]", "", t)
            if len(w) > 1 and w[0].isupper() and w[1:].islower():
                run.append((w.lower(), i == 0 or toks[i - 1][-1] in ".!?:"))
                if t[-1] in ",;:.!?)":
                    runs, run = runs + [run], []
            else:
                runs, run = runs + [run], []
        runs.append(run)
        bad_name = any(len(r) >= 2 and (any(w not in known and not st for w, st in r) or sum(w not in known for w, _ in r) >= 2) for r in runs)
        bad_url = any(u.rstrip(".,)") not in known for u in re.findall(r"https?://\S+", line))
        if line.strip() and not bad_name and not bad_url:
            kept.append(line.strip())
    return kept


def main(ctx):
    if not I.is_b2b(ctx):
        return {"skipped": "no business buyer: sell-stage work runs only for b2b ventures"}
    nets = [f for f in sorted((ctx["folder"] / "sell" / "accounts").glob("*/network.json")) if not (f.parent / "warm-path.md").exists()]
    if not nets:
        return {"skipped": "no network.json without a warm-path.md yet: run network-mapping first"}
    f = nets[0]
    acct, net = f.parent.name, I.dct(k.read(ctx, f"sell/accounts/{f.parent.name}/network.json"))
    if not any(e.get("confirmed") is True for e in map(I.dct, I.lst(net.get("edges")))):
        return {"skipped": f"{acct}: no edge in network.json carries `confirmed`; Charlie marks real relationships in the pull request first"}
    problem = I.txt(ctx["idea"].get("problem"), 200)
    paths = warm_paths(net, problem)
    words = " ".join(str(n.get(x, "")) for n in map(I.dct, I.lst(net.get("nodes"))) for x in ("id", "name")) + f" {ME} {acct.replace('-', ' ')} {ctx['idea'].get('title', '')}"
    known = set(re.sub(r"[^a-z]", " ", words.lower()).split()) | {str(e.get("evidence_url")) for e in map(I.dct, I.lst(net.get("edges"))) if e.get("evidence_url")}
    best = paths[0] if paths and paths[0]["hops"] <= MAX_WARM_HOPS else None
    backup = next((p for p in paths[1:] if best and p["nodes"][1:-1] != best["nodes"][1:-1] and p["hops"] <= MAX_WARM_HOPS), None)
    today = dt.date.today().isoformat()
    chain = lambda p: " > ".join(p["nodes"])  # noqa: E731
    if not best:
        first = f"no warm path: nothing confirmed within {MAX_WARM_HOPS} hops of {acct}."
        md = [first, "", "Do not stretch a weak path. Options: cold outreach through the Sales jobs, or drop the account.", f"Reason: the nearest path that starts with a confirmed edge is {paths[0]['hops']} hops." if paths else "Reason: no path starts with a confirmed edge or one of Charlie's contacts.", "", f"Written {today}. Nothing sent."]
    else:
        facts = "\n".join(f"{chain(p)}: " + "; ".join(f"{e.get('type')} strength {e.get('strength')} {e.get('origin')} {e.get('evidence_url', '')}" for e in p["edges"]) for p in [best] + ([backup] if backup else []))
        a = I.dct(k.ask('Write a one-page warm-path brief using only these paths. Names and links may come only from the paths. A connection is not a relationship. Return JSON only: {"why_real": ["<one line per edge>"], "ask": "<what the intro-maker should be asked>", '
                        '"intro": ["<line 1 who Charlie is>", "<line 2 why this person>", "<line 3 one clear ask that is easy to forward>"], "risks": ["<stale edge, weak tie, conflict of interest>"]}. Venture: ' + problem + "\n\nPATHS\n" + facts))
        why, ask, intro, risks = (clean("\n".join(map(str, a[key] if isinstance(a.get(key), list) else [a.get(key) or ""])), known) for key in ("why_real", "ask", "intro", "risks"))
        if not why:
            why = [f"{e.get('type')} between {e.get('from')} and {e.get('to')}, strength {e.get('strength')}, {e.get('origin')} {e.get('evidence_url', '')}".strip() for e in best["edges"]]
        first = f"Recommended path: {chain(best)} ({best['hops']} hops, weakest tie {best['weakest']})."
        md = [first, "", "## Why it is real", *[f"- {x}" for x in why], "", "## Backup", chain(backup) if backup else "No second path that avoids the same middle person.", "", "## What to ask the intro-maker",
              " ".join(ask) or "Ask whether they would be happy to introduce you, and what they would want to know first.", "", "## Draft intro request (Charlie edits it; not sent)", *([f"> {x}" for x in intro[:3]] or ["> No draft: the model gave no usable text. Write three lines: who you are, why this person, one easy ask."]), "",
              "## Risks", *([f"- {x}" for x in risks] or ["- A connection is not a relationship: check the tie is still live before asking."]), "", f"Written {today}. This job sent nothing and messaged no one."]
    k.write(ctx, f"sell/accounts/{acct}/warm-path.md", I.cap_words("\n".join(md), 450))
    return {"summary": f"{acct}: " + (first if best else "no warm path, brief says so."), "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
