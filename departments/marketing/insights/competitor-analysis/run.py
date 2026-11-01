"""Competitor Analysis: GitHub implementation of departments/marketing/insights/competitor-analysis/SKILL.md.

Builds or reads the competitor list, reads each home and pricing page (robots.txt respected), lists
YouTube titles with a key, labels hook patterns and finds gaps backed by a quoted line. No video or
audio is ever downloaded; transcripts come only from files Charlie supplies.
"""
import re
import statistics
import urllib.robotparser
from urllib.parse import urlparse

from foundry import jobkit as k

PATTERNS = ["curiosity gap", "number list", "contradiction", "pain call-out", "how-to promise", "before and after", "authority", "direct offer"]
PRICE = re.compile(r"(?:£|\$|€)\s?\d[\d,]*(?:\.\d{1,2})?(?:\s?(?:/|per|a)\s?(?:month|mo|year|yr|week))?", re.I)


def tidy(text):
    return re.sub(r"\s+", " ", re.sub(r"\s*[\u2013\u2014]\s*", ", ", re.sub(r"!+", ".", str(text)).replace(" - ", ", "))).strip()


def cell(text, n=90):
    return tidy(text).replace("|", "/")[:n]


def short_quote(text, words=15):
    return " ".join(tidy(text).split()[:words])


def allowed(url):
    """robots.txt check for our user agent. Returns (ok, reason)."""
    p = urlparse(url)
    try:
        r = k.requests.get(f"{p.scheme}://{p.netloc}/robots.txt", timeout=15)
        if not r.ok:
            return True, ""
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(r.text.splitlines())
        return (True, "") if rp.can_fetch("*", url) else (False, "robots.txt forbids it")
    except Exception:  # noqa: BLE001
        return True, ""


def find_competitors(idea, skipped):
    seen, out = set(), []
    for r in k.known_competitors(idea, 5):  # what the model already knows, then the web
        host = urlparse(r["url"]).netloc.lower().removeprefix("www.")
        if host and host not in seen:
            seen.add(host)
            out.append({"name": r["name"], "url": r["url"], "youtube": "", "instagram": "", "tiktok": ""})
    phrases = [str(idea.get("problem", ""))[:90], str(idea.get("gap", ""))[:90], f"{idea.get('title', '')} alternatives"]
    for q in phrases:
        for r in k.search(q.strip() + " tool OR app OR service", 6):
            host = urlparse(r.get("url", "")).netloc.lower().removeprefix("www.")
            if host and host not in seen and len(out) < 5 and not re.search(r"reddit|youtube|wikipedia|quora|facebook|linkedin", host):
                seen.add(host)
                out.append({"name": re.split(r"\s[|:]\s|\s-\s", r.get("title") or host)[0][:50], "url": r["url"], "youtube": "", "instagram": "", "tiktok": ""})
    if not out:
        skipped.append("competitor search: no results from the model, the router, Firecrawl or the keyless engines")
    return out


def read_site(comp, skipped):
    row = {"name": comp.get("name", ""), "url": comp.get("url", ""), "headline": "", "price": "", "promise": "", "text": ""}
    if not row["url"]:
        return row
    ok, why = allowed(row["url"])
    if not ok:
        skipped.append(f"{row['name']}: {why}")
        return row
    pages = [row["url"], row["url"].rstrip("/") + "/pricing"]
    row["text"] = " ".join(k.fetch(u, 6000) for u in pages)[:9000]
    if not row["text"].strip():
        skipped.append(f"{row['name']}: page could not be read")
        return row
    answer = k.ask('Return JSON only: {"headline": "...", "price": "...", "promise": "..."}. From this competitor page text give the main headline, the cheapest price shown (or empty) and its promise in one line.\n\n' + row["text"][:5000])
    if isinstance(answer, dict):
        row["headline"], row["price"], row["promise"] = (tidy(answer.get(f, ""))[:160] for f in ("headline", "price", "promise"))
    found = PRICE.search(row["text"])
    row["price"] = row["price"] or (found.group(0) if found else "not shown")
    return row


def youtube_titles(comp, key, skipped):
    ref = str(comp.get("youtube", "")).strip()
    if not ref:
        return []
    if not key:
        skipped.append("youtube: YOUTUBE_API_KEY missing")
        return []
    base = "https://www.googleapis.com/youtube/v3/"
    try:
        m = re.search(r"(UC[\w-]{20,})", ref)
        handle = re.search(r"@([\w.-]+)", ref) or (None if m else re.match(r"^([\w.-]+)$", ref))
        if m:
            cid = m.group(1)
        else:
            r = k.requests.get(base + "channels", params={"part": "id", "forHandle": handle.group(1), "key": key}, timeout=20).json()
            cid = r["items"][0]["id"]
        pl = k.requests.get(base + "playlistItems", params={"part": "contentDetails", "playlistId": "UU" + cid[2:], "maxResults": 30, "key": key}, timeout=20).json()
        ids = ",".join(i["contentDetails"]["videoId"] for i in pl.get("items", []))
        vids = k.requests.get(base + "videos", params={"part": "snippet,statistics,contentDetails", "id": ids, "key": key}, timeout=20).json().get("items", [])
        return [{"title": v["snippet"]["title"], "url": f"https://www.youtube.com/watch?v={v['id']}", "views": int(v.get("statistics", {}).get("viewCount", 0)), "date": v["snippet"]["publishedAt"][:10],
                 "description": v["snippet"].get("description", "")[:200], "id": v["id"], "platform": "youtube", "competitor": comp.get("name", "")} for v in vids]
    except Exception as exc:  # noqa: BLE001
        skipped.append(f"youtube {comp.get('name', '')}: {type(exc).__name__}")
        return []


def label(items):
    """Pattern and template for each hook text, in batches. Returns count labelled."""
    done = 0
    for i in range(0, len(items), 25):
        batch = items[i:i + 25]
        answer = k.ask('Return JSON only: {"labels": [{"i": 0, "pattern": "one of: ' + ", ".join(PATTERNS) + '", "template": "the text with specifics replaced by slots such as <number> or <pain>"}]}\n\n'
                       + "\n".join(f"{j}: {b['text']}" for j, b in enumerate(batch)))
        rows = answer.get("labels") if isinstance(answer, dict) else None
        for r in rows if isinstance(rows, list) else []:
            if isinstance(r, dict) and isinstance(r.get("i"), int) and 0 <= r["i"] < len(batch) and r.get("pattern") in PATTERNS:
                batch[r["i"]]["pattern"], batch[r["i"]]["template"] = r["pattern"], tidy(r.get("template", ""))[:160]
                done += 1
    return done


def main(ctx):
    idea, brain, skipped = ctx["idea"], ctx["brain"], []
    comps = k.read(ctx, "launch/inputs/competitors.json")
    if not isinstance(comps, list) or not comps:
        comps = find_competitors(idea, skipped)
        if comps:
            k.write(ctx, "launch/inputs/competitors.json", comps)
    if not comps:
        return {"skipped": "no competitor list and no search available: " + "; ".join(skipped)[:150]}
    rows = [read_site(c, skipped) for c in comps if isinstance(c, dict)][:8]
    key, titles = k.secret("YOUTUBE_API_KEY"), []
    for c in comps:
        titles += youtube_titles(c, key, skipped) if isinstance(c, dict) else []
    hooks = [{"text": t["title"], "url": t["url"], "views": t["views"], "platform": "youtube"} for t in titles]
    for r in rows:
        if r["headline"]:
            hooks.append({"text": r["headline"], "url": r["url"], "views": None, "platform": "web"})
    transcripts = ctx["folder"] / "launch/inputs/transcripts"
    for t in titles:  # transcripts only from files Charlie supplies; first 15 seconds is about 38 words
        f = transcripts / f"{t['id']}.txt"
        if f.exists():
            hooks.append({"text": " ".join(f.read_text(encoding="utf-8", errors="ignore").split()[:38]), "url": t["url"], "views": t["views"], "platform": "youtube"})
    labelled = label(hooks) if hooks else 0
    groups = {}
    for h in hooks:
        if h.get("pattern"):
            groups.setdefault((h["pattern"], h["platform"]), []).append(h)
    patterns = []
    for (pattern, platform), hs in sorted(groups.items(), key=lambda g: -len(g[1])):
        views = [h["views"] for h in hs if h["views"] is not None]
        best = max(hs, key=lambda h: h["views"] or 0)
        patterns.append({"pattern": pattern, "template": best.get("template", ""), "platform": platform, "count": len(hs), "median_views": int(statistics.median(views)) if views else 0,
                         "examples": [{"url": best["url"], "text": short_quote(best["text"])}]})
    corpus = " ".join(r["text"] for r in rows) + " " + " ".join(h["text"] for h in hooks)
    gaps = []
    if corpus.strip():
        answer = k.ask('Return JSON only: {"gaps": [{"gap": "what our gap says that no competitor says", "quote": "a line copied exactly from the competitor text that shows what they say instead"}]}. Up to five.\n\nOUR GAP\n'
                       + str(idea.get("gap", "")) + "\n\nBRAIN\n" + brain[:1500] + "\n\nCOMPETITOR TEXT\n" + corpus[:6000])
        for g in (answer.get("gaps") if isinstance(answer, dict) and isinstance(answer.get("gaps"), list) else []):
            if isinstance(g, dict) and g.get("quote") and re.sub(r"\s+", " ", str(g["quote"])).lower().strip(" .") in re.sub(r"\s+", " ", corpus).lower():
                gaps.append({"gap": tidy(g.get("gap", ""))[:200], "quote": short_quote(g["quote"])})
    lines = [f"# Competitors: {tidy(idea.get('title', ctx['slug']))}", "", "## Competitors", "| Name | Promise | Price | Channels |", "|---|---|---|---|"]
    for r in rows:
        src = next((c for c in comps if isinstance(c, dict) and c.get("name") == r["name"]), {})
        chans = [n for n, c in (("web", r["url"]), ("youtube", src.get("youtube")), ("instagram", src.get("instagram")), ("tiktok", src.get("tiktok"))) if c]
        lines.append(f"| {cell(r['name'], 40)} | {cell(r['promise'] or r['headline'] or 'not read', 100)} | {cell(r['price'], 30)} | {', '.join(chans)} |")
    lines += ["", "## Hook patterns"]
    if patterns:
        lines += ["| Pattern | Platform | Count | Median views | Example |", "|---|---|---|---|---|"] + [f"| {p['pattern']} | {p['platform']} | {p['count']} | {p['median_views']} | {cell(p['examples'][0]['text'], 100)} {p['examples'][0]['url']} |" for p in patterns]
    else:
        lines.append("No hook patterns: " + ("no model answered, so patterns were not labelled." if hooks else "no titles or headlines were collected."))
    lines += ["", "## Gaps"] + ([f"- {g['gap']} Competitors say: \"{g['quote']}\"" for g in gaps[:5]] or ["- none found with a quoted line"])
    lines += ["", "Terms of each site are not checked by code; Charlie confirms the list and anything that breaks a site's terms."]
    if skipped:
        lines += ["", "## Skipped"] + [f"- {s}" for s in skipped]
    k.write(ctx, "launch/insights/competitors.md", "\n".join(lines))
    k.write(ctx, "launch/insights/hook-patterns.json", patterns)
    return {"summary": f"{len(rows)} competitors read, {len(hooks)} hooks collected, {labelled} labelled, {len(gaps)} gaps with quotes. Skipped: {len(skipped)}.", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
