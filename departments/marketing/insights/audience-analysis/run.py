"""Audience Analysis: GitHub implementation of departments/marketing/insights/audience-analysis/SKILL.md.

Collects public comments (YouTube with a key, Hacker News, Apify actors Charlie configures) and the DMs
Charlie pastes, strips personal data in code before any model sees the text, clusters questions and
objections, builds the language bank and writes audience.md and audience.json. Raw text is never written.
"""
import html
import re
from collections import Counter, defaultdict

from foundry import jobkit as k

STOP = set("a an the and or but of to in on for with is are was were be it its this that i you we they he she my your our at as by from not no so if do does did have has had can will would should just about what how why when which who".split())
SPAM = re.compile(r"(subscribe|check out my|click here|whatsapp|telegram|dm me|promo ?code|giveaway|http\S+\s+http\S+)", re.I)
REGULATED = re.compile(r"\b(loan|invest|crypto|pension|mortgage|insurance|diagnos|symptom|medic|therapy|child|kids|bet|casino|gambl)", re.I)
KINDS = ("question", "objection", "desired outcome", "other")


def tidy(text):
    return re.sub(r"\s+", " ", re.sub(r"\s*[\u2013\u2014]\s*", ", ", re.sub(r"!+", ".", str(text)).replace(" - ", ", "))).strip()


def strip_personal(text):
    """Remove handles, emails, phone numbers, links and names after 'my name is'."""
    text = html.unescape(re.sub(r"<[^>]+>", " ", str(text)))
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", " ", text)
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"(?<!\w)@\w+", " ", text)
    text = re.sub(r"(?<!\d)(?:\+?\d[\d\s().-]{8,}\d)", " ", text)
    text = re.sub(r"(?i)\b(my name is|i am called|i'm called)\s+[A-Z][\w'-]*(?:\s+[A-Z][\w'-]*)?", r"\1 someone", text)
    return re.sub(r"\s+", " ", text).strip()


def clean(items):
    seen, out = set(), []
    for source, text in items:
        t = strip_personal(text)
        key = re.sub(r"\W+", " ", t.lower()).strip()
        if len(t.split()) >= 5 and not SPAM.search(t) and key not in seen:
            seen.add(key)
            out.append((source, t[:600]))
    return out


def get_json(url, params, skipped, why):
    try:
        r = k.requests.get(url, params=params, timeout=20)
        if r.ok:
            return r.json()
        skipped.append(f"{why}: HTTP {r.status_code}")
    except Exception as exc:  # noqa: BLE001
        skipped.append(f"{why}: {type(exc).__name__}")
    return None


def terms_for(idea, brain):
    answer = k.ask('Return JSON only: {"terms": ["..."]}. Five to ten short search terms (2 to 5 words) the people with this problem would type or say.\n\nBRAIN\n' + brain[:2500])
    rows = answer.get("terms") if isinstance(answer, dict) else None
    out = [tidy(t)[:60] for t in rows if isinstance(t, str) and t.strip()] if isinstance(rows, list) else []
    for f in ("problem", "who", "title"):
        words = re.sub(r"[^\w\s']", " ", str(idea.get(f, ""))).split()
        if len(out) < 5 and words:
            out.append(" ".join(words[:5]))
    return list(dict.fromkeys(out))[:10]


def youtube_comments(video_ids, key, skipped, cap=500):
    out = []
    for vid in video_ids:
        data = get_json("https://www.googleapis.com/youtube/v3/commentThreads", {"part": "snippet", "videoId": vid, "maxResults": 100, "textFormat": "plainText", "key": key}, skipped, "youtube comments")
        out += [("youtube", i["snippet"]["topLevelComment"]["snippet"]["textDisplay"]) for i in (data or {}).get("items", [])]
        if len(out) >= cap:
            break
    return out[:cap]


def collect(ctx, terms, skipped):
    items, key = [], k.secret("YOUTUBE_API_KEY")
    for t in terms[:6]:  # Hacker News comments, free
        data = get_json("https://hn.algolia.com/api/v1/search", {"query": t, "tags": "comment", "hitsPerPage": 50}, skipped, "hacker news")
        if data is None:
            break
        items += [("hn", h.get("comment_text") or "") for h in data.get("hits", [])]
    if key:
        vids = []
        for t in terms[:3]:
            data = get_json("https://www.googleapis.com/youtube/v3/search", {"part": "id", "q": t, "type": "video", "order": "viewCount", "maxResults": 2, "key": key}, skipped, "youtube search")
            vids += [r["id"]["videoId"] for r in (data or {}).get("items", []) if r.get("id", {}).get("videoId")]
        items += youtube_comments(list(dict.fromkeys(vids)), key, skipped)
        log = k.read(ctx, "launch/publish-log.json", [])  # our own videos, after launch
        rows = log.get("log", []) if isinstance(log, dict) else log
        own = [m.group(1) for r in rows if isinstance(r, dict) for m in [re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", str(r.get("url", "")))] if m]
        items += youtube_comments(own[:10], key, skipped)
        if k.secret("META_ACCESS_TOKEN"):
            skipped.append("meta comments: not read by this job yet")
    else:
        skipped.append("youtube: YOUTUBE_API_KEY missing")
    plan, token = k.read(ctx, "launch/inputs/apify.json", []), k.secret("APIFY_TOKEN")
    if not token:
        skipped.append("apify: APIFY_TOKEN missing")
    elif not isinstance(plan, list) or not plan:
        skipped.append("apify: no actors listed in launch/inputs/apify.json")
    for a in plan if token and isinstance(plan, list) else []:
        try:
            r = k.requests.post(f"https://api.apify.com/v2/acts/{a['actor']}/run-sync-get-dataset-items", params={"token": token, "timeout": 120}, json=a.get("input", {}), timeout=150)
            rows = r.json() if r.ok else []
            skipped += [] if r.ok else [f"apify {a['actor']}: HTTP {r.status_code}"]
            items += [(str(a.get("source", "apify")), next((str(row[f]) for f in ("text", "body", "content", "reviewText", "comment", "review") if row.get(f)), "")) for row in rows[:500] if isinstance(row, dict)]
        except Exception as exc:  # noqa: BLE001
            skipped.append(f"apify {a.get('actor', '?') if isinstance(a, dict) else '?'}: {type(exc).__name__}")
    dms = k.read(ctx, "launch/inputs/dms.txt", "")  # only what Charlie pastes
    items += [("dms", d) for d in re.split(r"\n\s*\n|\n", dms or "") if d.strip()]
    return items


def theme_key(theme):
    return " ".join(sorted(w.rstrip("s") for w in re.findall(r"[a-z']+", theme.lower()) if w not in STOP))


def label(items):
    out = []
    for i in range(0, min(len(items), 300), 50):
        batch = items[i:i + 50]
        answer = k.ask('Return JSON only: {"labels": [{"i": 0, "kind": "question", "theme": "pricing too high"}, {"i": 1, "kind": "other", "theme": "off topic"}]}, one entry per numbered comment below, in order. '
                       'kind is exactly one of question, objection, desired outcome, other. theme is 2 to 4 words of your own naming what the comment is about.\n\n'
                       + "\n".join(f"{j}: {t[:300]}" for j, (_, t) in enumerate(batch)))
        rows = answer.get("labels") if isinstance(answer, dict) and isinstance(answer.get("labels"), list) else []
        for pos, r in enumerate(rows):
            if not isinstance(r, dict):
                continue
            try:
                i = int(r.get("i", pos))
            except (TypeError, ValueError):
                i = pos
            kind = next((x for x in KINDS if x in str(r.get("kind", "")).lower()), None)
            theme = tidy(r.get("theme", ""))
            if 0 <= i < len(batch) and kind and theme and theme.lower() not in ("2 to 4 words", "pricing too high", "off topic"):
                out.append((kind, theme[:40], batch[i][1]))
    return out


def merge_themes(labels, idea):
    """Comments get a theme each, so nothing clusters: one model call folds the themes into at most ten per kind,
    and drops the ones off the venture's topic. Falls back to the raw labels when the model gives nothing usable."""
    themes = sorted({t for kind, t, _ in labels if kind in ("question", "objection")})
    if len(themes) < 4:
        return labels
    answer = k.ask('Return JSON only: {"groups": [{"theme": "3 word group name", "members": ["theme as given", "theme as given"]}], "off_topic": ["theme as given"]}. '
                   'Fold these comment themes into at most 10 groups per kind that someone marketing this venture would act on; themes unrelated to the venture go in off_topic.\n\nVENTURE: '
                   + tidy(f"{idea.get('title', '')}. {idea.get('problem', '')}")[:300] + "\n\nTHEMES\n" + "\n".join(f"- {t}" for t in themes[:300]))
    groups = answer.get("groups") if isinstance(answer, dict) and isinstance(answer.get("groups"), list) else []
    off = {theme_key(tidy(t)) for t in (answer.get("off_topic") if isinstance(answer, dict) and isinstance(answer.get("off_topic"), list) else []) if isinstance(t, str)}
    into = {}
    for g in groups:
        name = tidy(g.get("theme", "")) if isinstance(g, dict) else ""
        for m in (g.get("members") if isinstance(g, dict) and isinstance(g.get("members"), list) else []):
            if name and isinstance(m, str) and name.lower() != "3 word group name":
                into[theme_key(tidy(m))] = name[:40]
    if not into:
        return labels
    out = []
    for kind, theme, text in labels:
        key = theme_key(theme)
        if key in off:
            continue
        out.append((kind, into.get(key, theme), text))
    return out


def language_bank(texts):
    seen = defaultdict(set)
    for n, t in enumerate(texts):
        words = re.findall(r"[a-z0-9£']+", t.lower())
        for size in range(2, 6):
            for i in range(len(words) - size + 1):
                g = words[i:i + size]
                if g[0] not in STOP and g[-1] not in STOP:
                    seen[" ".join(g)].add(n)
    ranked = sorted((g for g, ids in seen.items() if len(ids) > 1), key=lambda g: (-len(seen[g]), -len(g.split())))
    out = []
    for g in ranked:
        if not any(g in o for o in out):
            out.append(g)
    return out[:25]


def quote(text, words=20):
    return " ".join(text.split()[:words])


def main(ctx):
    idea, brain, skipped = ctx["idea"], ctx["brain"], []
    terms = terms_for(idea, brain)
    items = clean(collect(ctx, terms, skipped))
    if not items:
        return {"skipped": "no public text collected: " + "; ".join(skipped)[:150]}
    texts = [t for _, t in items]
    bank = language_bank(texts)
    labels = merge_themes(label(items), idea)
    groups = {"question": {}, "objection": {}}
    for kind, theme, text in labels:
        if kind in groups:
            row = groups[kind].setdefault(theme_key(theme) or theme.lower(), {"theme": theme, "count": 0, "texts": []})
            row["count"] += 1
            row["texts"].append(text)
    def top(kind, n):
        rows = sorted(groups[kind].values(), key=lambda r: -r["count"])[:n]
        return [{"theme": r["theme"], "count": r["count"], "quotes": [quote(t) for t in sorted(r["texts"], key=lambda t: (len(t.split()) > 20, len(t)))[:2]]} for r in rows]
    questions, objections = top("question", 10), top("objection", 8)
    if objections:
        answer = k.ask('Return JSON only: {"answers": [{"theme": "...", "answer": "one line"}]}. Answer each objection in one line using only facts in the brain. If the brain has no fact, answer exactly: no answer yet.\n\nOBJECTIONS\n'
                       + "\n".join(f"- {o['theme']}" for o in objections) + "\n\nBRAIN\n" + brain[:3000])
        by = {tidy(a.get("theme", "")).lower(): tidy(a.get("answer", "")) for a in (answer.get("answers") if isinstance(answer, dict) and isinstance(answer.get("answers"), list) else []) if isinstance(a, dict)}
        for o in objections:
            a = by.get(o["theme"].lower(), "")
            numbers_ok = all(n in brain for n in re.findall(r"\d+(?:[.,]\d+)*", a))
            o["answer"] = a if a and numbers_ok and "no answer" not in a.lower() else "no answer yet"
    ideas = []
    if questions or objections:
        answer = k.ask('Return JSON only: {"ideas": [{"idea": "a post or video idea", "answers": "the question or objection theme it answers"}]}. Ten ideas.\n\n'
                       + "\n".join(f"- {r['theme']}" for r in questions + objections))
        ideas = [{"idea": tidy(i.get("idea", "")), "answers": tidy(i.get("answers", ""))} for i in (answer.get("ideas") if isinstance(answer, dict) and isinstance(answer.get("ideas"), list) else []) if isinstance(i, dict) and i.get("idea")][:10]
        if not ideas:
            ideas = [{"idea": f"Answer plainly: {r['theme']}", "answers": r["theme"]} for r in (questions + objections)[:10]]
    data = {"questions": questions, "objections": objections, "language_bank": bank, "content_ideas": ideas}
    raw = Counter(w for t in texts for w in re.findall(r"[a-z']{4,}", t.lower()) if w not in STOP).most_common(15)
    lines = [f"# Audience: {tidy(idea.get('title', ctx['slug']))}", f"{len(items)} items after cleaning, from {len({s for s, _ in items})} sources. Personal data stripped before any model; raw text not stored.", ""]
    if not labels:
        lines += ["Questions and objections: needs model (none answered). Raw term counts: " + ", ".join(f"{w} {c}" for w, c in raw), ""]
    lines += ["## Questions"] + [f"- {r['theme']} ({r['count']}){' REVIEW: regulated area' if REGULATED.search(r['theme']) else ''}: " + " / ".join(f'"{q}"' for q in r["quotes"]) for r in questions]
    lines += ["", "## Objections"] + [f"- {r['theme']} ({r['count']}). Answer: {r['answer']}{' REVIEW: regulated area' if REGULATED.search(r['theme']) else ''}" for r in objections]
    lines += ["", "## Language bank"] + [f"- {p}" for p in bank]
    lines += ["", "## Content ideas"] + [f"{n}. {i['idea']} (answers: {i['answers']})" for n, i in enumerate(ideas, 1)]
    if skipped:
        lines += ["", "## Skipped sources"] + [f"- {s}" for s in skipped]
    k.write(ctx, "launch/insights/audience.md", "\n".join(lines))
    k.write(ctx, "launch/insights/audience.json", data)
    return {"summary": f"{len(items)} items, {len(questions)} question themes, {len(objections)} objection themes, {len(bank)} language bank phrases. Skipped sources: {len(skipped)}.", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
