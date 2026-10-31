"""Trend Monitoring: GitHub implementation of departments/marketing/insights/trend-monitoring/SKILL.md.

Searches Hacker News, YouTube (with a key) and the web for the venture's niche, scores each topic
out of 100 (recency, engagement, fit), finds rising video formats and writes the weekly brief.
"""
import datetime as dt
import json
import re

from foundry import jobkit as k

SENSITIVE = re.compile(r"\b(election|war|shooting|murder|killed|dies|died|dead|terror|attack|trump|biden|protest|abortion|suicide|tragedy|casualt)", re.I)
PATTERNS = {"number": lambda t: bool(re.match(r"\s*\d", t)), "question": lambda t: t.strip().endswith("?") or bool(re.match(r"\s*(why|what|how|is|can|do|does|should)\b", t, re.I)),
            "how to": lambda t: "how to" in t.lower(), "vs": lambda t: bool(re.search(r"\bvs\.?\b", t, re.I))}


def tidy(text):
    return re.sub(r"\s+", " ", re.sub(r"\s*[\u2013\u2014]\s*", ", ", re.sub(r"!+", ".", str(text)).replace(" - ", ", "))).strip()


def cell(text):
    return tidy(text).replace("|", "/")[:90]


def get_json(url, params, skipped, why):
    try:
        r = k.requests.get(url, params=params, timeout=20)
        if r.ok:
            return r.json()
        skipped.append(f"{why}: HTTP {r.status_code}")
    except Exception as exc:  # noqa: BLE001
        skipped.append(f"{why}: {type(exc).__name__}")
    return None


def build_phrases(idea, brain):
    answer = k.ask('Return JSON only: {"phrases": ["..."]}. Five to eight short search phrases (2 to 5 words each) a reader of this niche would type: '
                   "the problem in their words, the category, the who. No brand names.\n\nBRAIN\n" + brain[:3000])
    rows = answer.get("phrases") if isinstance(answer, dict) else None
    out = [tidy(p)[:60] for p in rows if isinstance(p, str) and p.strip()] if isinstance(rows, list) else []
    if len(out) < 5:  # heuristic top-up from the idea fields
        for key in ("title", "category", "problem", "who", "gap"):
            words = re.sub(r"[^\w\s']", " ", str(idea.get(key, ""))).split()
            if words:
                out.append(" ".join(words[:5]))
        out += [str(m)[:50] for m in idea.get("mvp", [])[:2]] if isinstance(idea.get("mvp"), list) else []
    seen, res = set(), []
    for p in out:
        if p.lower() not in seen and len(p) > 2:
            seen.add(p.lower())
            res.append(p)
    return res[:8]


def duration_s(iso):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    return int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0) if m else 0


def collect(phrases, since, skipped):
    items = []
    for p in phrases:  # Hacker News, free, no key
        data = get_json("https://hn.algolia.com/api/v1/search_by_date", {"query": p, "tags": "story", "numericFilters": f"created_at_i>{int(since.timestamp())}", "hitsPerPage": 15}, skipped, "hacker news")
        if data is None:
            break
        for h in data.get("hits", []):
            title = h.get("title") or ""
            if title:
                items.append({"title": title, "source": "hn", "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                              "date": h.get("created_at", "")[:10], "engagement": h.get("points") or 0, "phrase": p})
    key = k.secret("YOUTUBE_API_KEY")
    if key:
        ids = {}
        for p in phrases[:8]:
            data = get_json("https://www.googleapis.com/youtube/v3/search", {"part": "id", "q": p, "type": "video", "order": "viewCount", "maxResults": 8, "publishedAfter": since.strftime("%Y-%m-%dT%H:%M:%SZ"), "key": key}, skipped, "youtube search")
            if data is None:
                break
            for row in data.get("items", []):
                ids[row.get("id", {}).get("videoId", "")] = p
        ids.pop("", None)
        pairs = list(ids)
        for i in range(0, len(pairs), 50):  # videos.list, 1 unit per 50 ids
            data = get_json("https://www.googleapis.com/youtube/v3/videos", {"part": "snippet,statistics,contentDetails", "id": ",".join(pairs[i:i + 50]), "key": key}, skipped, "youtube videos")
            for v in (data or {}).get("items", []):
                items.append({"title": v["snippet"]["title"], "source": "youtube", "url": f"https://www.youtube.com/watch?v={v['id']}", "date": v["snippet"]["publishedAt"][:10],
                              "engagement": int(v.get("statistics", {}).get("viewCount", 0)), "duration_s": duration_s(v.get("contentDetails", {}).get("duration")), "phrase": ids.get(v["id"], "")})
    else:
        skipped.append("youtube: YOUTUBE_API_KEY missing")
    for p in phrases[:3]:  # web news through the router or Firecrawl, if either is up
        for r in k.search(p + " news this week", 4, "news"):
            if r.get("url") and r.get("title"):
                items.append({"title": r["title"], "source": "web", "url": r["url"], "date": "", "engagement": None, "phrase": p})
    seen, out = set(), []
    for it in items:
        if it["url"] not in seen and not SENSITIVE.search(it["title"]):
            seen.add(it["url"])
            out.append(it)
    return out


def score(items, today):
    for it in items:
        try:
            age = (today - dt.date.fromisoformat(it["date"])).days if it["date"] else 3.5
        except ValueError:
            age = 3.5
        it["recency"] = round(40 * max(0.0, 1 - age / 7), 1)
        peers = [x["engagement"] for x in items if x["source"] == it["source"] and x["engagement"] is not None]
        e = it["engagement"]
        below, equal = sum(1 for v in peers if e is not None and v < e), sum(1 for v in peers if e is not None and v == e)
        it["engagement_pts"] = round(40 * (below + 0.5 * (equal - 1)) / max(len(peers) - 1, 1), 1) if e is not None and len(peers) > 1 else 0
        it["fit"], it["reason"] = 0, ""
    return items


def add_fit(items, brain):
    ranked = sorted(items, key=lambda x: -(x["recency"] + x["engagement_pts"]))[:30]
    if not ranked:
        return False
    listing = "\n".join(f"{i}: {it['title']}" for i, it in enumerate(ranked))
    answer = k.ask('Return JSON only: {"fits": [{"i": 0, "fit": "yes or no", "reason": "one line"}]}. For each topic say whether it touches the problem or the reader of this venture, with a one-line reason.\n\nBRAIN\n'
                   + brain[:2500] + "\n\nTOPICS\n" + listing)
    rows = answer.get("fits") if isinstance(answer, dict) else None
    if not isinstance(rows, list):
        return False
    for r in rows:
        if isinstance(r, dict) and isinstance(r.get("i"), int) and 0 <= r["i"] < len(ranked) and str(r.get("fit", "")).lower().startswith("y") and str(r.get("reason", "")).strip():
            ranked[r["i"]]["fit"], ranked[r["i"]]["reason"] = 20, cell(r["reason"])
    return True


def formats(items):
    vids = sorted([x for x in items if x["source"] == "youtube"], key=lambda x: -x["engagement"])[:25]
    if not vids:
        return {}
    def share(counter):
        return {n: round(100 * c / len(vids), 1) for n, c in counter.items() if c}
    dur = {"under 60 seconds": sum(v["duration_s"] < 60 for v in vids), "1 to 10 minutes": sum(60 <= v["duration_s"] <= 600 for v in vids), "over 10 minutes": sum(v["duration_s"] > 600 for v in vids)}
    pat = {n: sum(f(v["title"]) for v in vids) for n, f in PATTERNS.items()}
    return {"duration": share(dur), "title": share(pat)}


def main(ctx):
    idea, brain, today = ctx["idea"], ctx["brain"], dt.date.today()
    skipped, since = [], dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)
    phrases = build_phrases(idea, brain)
    items = score(collect(phrases, since, skipped), today)
    if not items:
        return {"skipped": "no topics collected: " + "; ".join(skipped)[:150]}
    had_model = add_fit(items, brain)
    for it in items:
        it["score"] = round(it["recency"] + it["engagement_pts"] + it["fit"], 1)
    items.sort(key=lambda x: -x["score"])
    fmt = formats(items)
    prev_files = sorted(p for p in (ctx["folder"] / "launch/insights").glob("trends-*.json") if p.stem != f"trends-{today.isoformat()}")
    prev = json.loads(prev_files[-1].read_text(encoding="utf-8")).get("formats", {}) if prev_files else {}
    rising = sorted([(g + ": " + n, s, prev.get(g, {}).get(n, 0)) for g, d in fmt.items() for n, s in d.items() if prev.get(g) is not None and s - prev[g].get(n, 0) >= 10], key=lambda r: r[1] - r[2], reverse=True)[:3]
    top = items[:10]
    angles = k.ask('Return JSON only: {"angles": [{"topic": "...", "hook_angle": "...", "format": "..."}]}. Three post angles for this week from the top topics: each a topic, a hook angle and a format. Plain, no hype.\n\nTOPICS\n'
                   + "\n".join(f"- {t['title']} (score {t['score']})" for t in top[:6]) + "\n\nBRAIN\n" + brain[:1500])
    rows = [a for a in (angles.get("angles") if isinstance(angles, dict) and isinstance(angles.get("angles"), list) else []) if isinstance(a, dict) and a.get("topic")][:3]
    if not rows:
        fmt_name = rising[0][0] if rising else "short video under 60 seconds"
        rows = [{"topic": t["title"], "hook_angle": h, "format": fmt_name} for t, h in zip(top, ("curiosity gap", "pain call-out", "number list"))]
    lines = [f"# Trends: {tidy(idea.get('title', ctx['slug']))}", f"Week to {today.isoformat()}. Phrases: " + "; ".join(phrases), ""]
    if not had_model:
        lines += ["No model answered, so fit is set to 0 and scores use recency and engagement only.", ""]
    lines += ["## Top 10 topics", "| Score | Topic | Source | URL | Why it fits |", "|---|---|---|---|---|"]
    lines += [f"| {t['score']} | {cell(t['title'])} | {t['source']} | {t['url']} | {t['reason'] or 'not scored'} |" for t in top]
    lines += ["", "## Rising formats"]
    lines += [f"- {n}: {s}% of the top 25 (was {p}%)" for n, s, p in rising] or ["- none: " + ("no earlier run to compare with" if not prev else "no bucket is up 10 points") if fmt else "- none: needs YOUTUBE_API_KEY"]
    lines += ["", "## This week"] + [f"{i}. {cell(a.get('topic'))}. Hook angle: {cell(a.get('hook_angle', ''))}. Format: {cell(a.get('format', ''))}." for i, a in enumerate(rows, 1)]
    if skipped:
        lines += ["", "## Skipped sources"] + [f"- {s}" for s in skipped]
    k.write(ctx, "launch/insights/trends.md", "\n".join(lines))
    k.write(ctx, f"launch/insights/trends-{today.isoformat()}.json", {"date": today.isoformat(), "phrases": phrases, "items": items, "formats": fmt,
                                                                       "rising": [r[0] for r in rising], "angles": rows, "fit_scored": had_model, "skipped": skipped})
    return {"summary": f"{len(items)} topics from {len({i['source'] for i in items})} sources; top: {cell(top[0]['title'])[:60]}. Skipped: {len(skipped)}.", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
