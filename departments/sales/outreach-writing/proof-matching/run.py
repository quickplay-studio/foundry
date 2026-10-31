"""Proof Matching: GitHub implementation of departments/sales/outreach-writing/proof-matching/SKILL.md.

Inventories only true proof, each item with a source, ranked: (a) a customer result Charlie confirmed
in writing (a note in proof/ that says so), (b) a pilot or trial note, (c) a working demo link,
(d) public demand evidence (the venture's own proof links), (e) a stated price. Customers.csv gives an
unnamed customer count. Lines are 25 words or fewer and are checked in code against their source: a
number that is not in the source drops the model's wording for the plain line. Never invents a
customer, logo, quote, number or "trusted by". A new venture gets honest demand and price lines.
"""
import csv
import datetime as dt
import io
import json
import re

from foundry import jobkit as k

RANK = {"customer-result": 0, "pilot": 1, "customers": 1, "demo": 2, "demand": 3, "price": 4}
DASH = re.compile(r"\s*[" + chr(0x2013) + chr(0x2014) + r"]\s*")  # model text never carries dashes into files


def b2b(ctx):
    audit = k.read(ctx, "audit.json", {}) or {}
    return "b2b" in (str(ctx["idea"].get("business_model", "")).lower(), str(audit.get("business_model", "")).lower())


def table(ctx, rel):
    return list(csv.DictReader(io.StringIO(k.read(ctx, rel, "") or "")))


def plain(text, n=300):
    return re.sub(r"\s+", " ", DASH.sub(", ", str(text or ""))).strip()[:n]


def segment_names(ctx):
    icp = k.read(ctx, "sell/icp.json", None)
    if not isinstance(icp, dict):
        icp = None
        for block in reversed(re.findall(r"```json\s*(.*?)```", k.read(ctx, "sell/icp.md", "") or "", re.S)):
            try:
                icp = json.loads(block)
                break
            except ValueError:
                continue
    return [str(s["name"]) for s in (icp or {}).get("segments", []) if isinstance(s, dict) and s.get("name")]


def check(line, source_text):
    """Code check: at most 25 words, no 'trusted by', every number appears in the source."""
    nums = re.findall(r"\d[\d,.]*", line)
    return 0 < len(line.split()) <= 25 and "trusted by" not in line.lower() and all(n.strip(".,") in source_text for n in nums)


def keeps(old, new, source):
    """A rephrase must keep every number and most of the content words, and add no number the source lacks."""
    nums = lambda t: {n.strip(".,") for n in re.findall(r"\d[\d,.]*", t)}  # noqa: E731
    words = lambda t: set(re.findall(r"[a-z]{4,}", t.lower()))  # noqa: E731
    return nums(old) <= nums(new) <= nums(source) | nums(old) and len(words(old) & words(new)) * 2 >= len(words(old))


def main(ctx):
    if not b2b(ctx):
        return {"skipped": "no business buyer"}
    segs = segment_names(ctx)
    if not segs:
        return {"skipped": "no ICP segments yet (sell/icp.md): run icp-definition first"}
    today, idea, items = dt.date.today().isoformat(), ctx["idea"], []
    notes = ctx["folder"] / "proof"
    for path in sorted(notes.glob("*.*")) if notes.is_dir() else []:  # Charlie's own notes; only a written confirmation makes a customer result
        text = path.read_text(encoding="utf-8", errors="ignore")[:3000]
        kind = "customer-result" if re.search(r"confirmed in writing", text, re.I) else "pilot" if re.search(r"\b(pilot|trial)\b", text, re.I) else ""
        sentence = next((s.strip() for s in re.split("(?<=[.?" + chr(33) + "])\\s+|\\n", text) if re.search(r"\d", s) and len(s.split()) <= 25), "")
        if kind and sentence and not re.search(r"customer name|logo", sentence, re.I):
            items.append({"type": kind, "line": plain(sentence), "source": f"proof/{path.name}", "text": text})
    n = len(table(ctx, "sell/customers.csv"))
    if n:
        items.append({"type": "customers", "line": f"{n} businesses now pay for {idea.get('title', 'this')}.", "source": "sell/customers.csv", "text": str(n)})
    demo = next((str(u) for u in re.findall(r"https?://\S+", json.dumps(idea) + " " + ctx["brain"]) if "demo" in u.lower()), "")
    demo = demo.rstrip(".,)\"")
    if demo:
        items.append({"type": "demo", "line": f"A working demo is live: {demo}", "source": demo, "text": demo})
    who = str(idea.get("who", "people in this field")).strip().rstrip(".")
    for p in idea.get("proof", []) if isinstance(idea.get("proof"), list) else []:
        if isinstance(p, dict) and str(p.get("url", "")).startswith("http"):
            items.append({"type": "demand", "line": f"{who[:60]} keep asking for this: see the {p.get('source', 'public')} thread.", "source": p["url"], "text": str(p["url"])})
    if idea.get("money"):
        items.append({"type": "price", "line": plain(f"How it is priced: {idea['money']}", 200), "source": "brain.md money", "text": str(idea["money"])})
    items = [i for i in items if check(i["line"], i["text"] if i["type"] in ("customer-result", "pilot") else i["text"] + i["line"])]
    if not items:
        return {"skipped": "no true proof found yet (no notes in proof/, no customers, no proof links, no stated price)"}
    items.sort(key=lambda i: RANK[i["type"]])
    ans = k.ask("Rephrase each numbered proof line in 25 words or fewer. Keep every fact and number exactly; add nothing; no hype. "
                "Return JSON only: {\"lines\": [{\"i\": 0, \"line\": \"...\"}]}\n\n" + "\n".join(f"{i}: {it['line']}" for i, it in enumerate(items)))
    for row in (ans.get("lines") if isinstance(ans, dict) and isinstance(ans.get("lines"), list) else []):
        try:
            it, line = items[int(row["i"])], plain(row["line"])
        except (KeyError, TypeError, ValueError, IndexError):
            continue
        src = it["text"] if it["type"] in ("customer-result", "pilot") else it["text"] + it["line"]
        if check(line, src) and keeps(it["line"], line, src) and set(re.findall(r"https?://\S+", line)) <= set(re.findall(r"https?://\S+", it["line"])):
            it["line"] = line
    def entry(it):
        return {"type": it["type"], "line": it["line"], "source": it["source"], "verified": today}

    segments = {s: {"primary": entry(items[0]), **({"fallback": entry(items[1])} if len(items) > 1 else {})} for s in segs}
    leads = {}
    for r in table(ctx, "sell/leads.csv"):  # a closer match: the dossier's proof hint names another segment
        hint = re.search(r"## Proof hint\s*\n(.+)", k.read(ctx, f"sell/dossiers/{r['id']}.md", "") or "")
        if r["tier"] == "A" and hint and hint.group(1).strip() in segments and hint.group(1).strip() != r["segment"]:
            leads[r["id"]] = hint.group(1).strip()
    k.write(ctx, "sell/proof.json", {"segments": segments, "leads": leads})
    types = ", ".join(sorted({i["type"] for i in items}))
    return {"summary": f"Proof for {len(segs)} segments from {len(items)} verified items ({types}). No invented customers or numbers.", "flag": "ok" if items[0]["type"] != "price" else "caution"}


if __name__ == "__main__":
    k.run(main)
