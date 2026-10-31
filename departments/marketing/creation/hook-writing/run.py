"""Hook Writing: GitHub implementation of departments/marketing/creation/hook-writing/SKILL.md.

Asks the free model for hooks per platform, rejects and scores them in code, keeps the top five per
platform and kind (30 at most) and writes hooks.json and hooks.md. With no model, hooks are filled from
templates and the language bank. Charlie can set a hook to rejected; reruns keep that status and the id.
"""
import re

from foundry import jobkit as k

BASE = ["curiosity gap", "number list", "contradiction", "pain call-out", "how-to promise", "before and after", "direct offer"]
LIMITS = {"spoken": ("words", 12), "title": ("chars", 60), "cover": ("words", 7)}
HYPE = re.compile(r"\b(amazing|revolutionary|game[- ]changing|insane|secret|incredible|unbelievable|guaranteed?|life[- ]changing|ultimate)\b", re.I)
PROMISE = re.compile(r"\b(earn|income|get rich|rich quick|passive|lose weight|cure|heal|save you|make money)\b", re.I)
SUPER = re.compile(r"(\bbest\b|\bgreatest\b|\bfastest\b|\bcheapest\b|\bnumber one\b|#1|\bperfect\b)", re.I)
DEFAULTS = {"pain call-out": "Tired of {pain}?", "how-to promise": "How to stop {pain}", "curiosity gap": "The {pain} problem nobody checks",
            "direct offer": "{product} for {reader}", "contradiction": "{pain} is not the real problem", "before and after": "From {pain} to a hard cap"}
STOP = set("a an the and or of to in on for with is are was be it this that you your we our at as by from not no so if do can will".split())


def tidy(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def kinds_for(platform):
    return ["spoken", "title", "cover"] if platform == "youtube" else ["spoken", "cover"]


def toks(text):
    return {w.rstrip("s") for w in re.findall(r"[a-z0-9£']+", text.lower()) if w not in STOP and len(w) > 2}


def within(text, kind):
    unit, limit = LIMITS[kind]
    return (len(text) if unit == "chars" else len(text.split())) <= limit


def rejected(text, kind, allowed_numbers):
    if re.search(r"[\u2013\u2014!]| - ", text) or HYPE.search(text) or PROMISE.search(text) or SUPER.search(text) or not within(text, kind):
        return True
    return any(n not in allowed_numbers for n in re.findall(r"\d+(?:[.,]\d+)*", text))


def score(h, ctx_words, bank, winners, names, mvp_words, vidiq):
    t = h["text"].lower()
    pts = 2 if within(h["text"], h["kind"]) else 0
    pts += 2 if toks(t) & ctx_words else 0
    pts += 2 if re.search(r"\d", t) or toks(t) & mvp_words else 0
    pts += 2 if h["pattern"] in winners or h["pattern"] in names else 0
    pts += 2 if any(b in t for b in bank) else 0
    return pts, vidiq.get(t, 0)


def template_hooks(platform, patterns, pain, reader, product, phrase):
    out = []
    for p in patterns:
        tpl = DEFAULTS.get(p["pattern"]) or str(p.get("template", ""))
        if "<" in tpl:
            tpl = re.sub(r"<[^>]+>", phrase or pain, tpl)
        text = tidy(tpl.format(pain=pain, reader=reader, product=product, phrase=phrase or pain) if "{" in tpl else tpl)
        for kind in kinds_for(platform):
            out.append({"kind": kind, "text": text, "pattern": p["pattern"], "theme": pain})
    return out


def main(ctx):
    audience = k.read(ctx, "launch/insights/audience.json")
    if not isinstance(audience, dict):
        return {"skipped": "launch/insights/audience.json missing: run audience-analysis first"}
    idea, brain = ctx["idea"], ctx["brain"]
    channels = k.read(ctx, "launch/channels.json", {}) or {}
    platforms = [str(p).lower() for p in channels.get("platforms", [])] if isinstance(channels, dict) and channels.get("platforms") else ["tiktok", "instagram", "youtube"]
    found = k.read(ctx, "launch/insights/hook-patterns.json", []) or []
    names = {r["pattern"] for r in found if isinstance(r, dict) and r.get("pattern")}
    perf = k.read(ctx, "launch/insights/performance.json", {}) or {}
    rows = [r for r in perf.get("patterns", []) if isinstance(r, dict) and r.get("by") == "hook_pattern"] if isinstance(perf, dict) else []
    winners = [r["group"] for r in sorted(rows, key=lambda r: (-(r.get("median_signups") or 0), -(r.get("median_views") or 0)))[:2]]
    patterns = [{"pattern": p} for p in winners + [p for p in BASE if p not in winners] + sorted(names - set(BASE) - set(winners))]
    patterns += [{"pattern": r["pattern"], "template": r.get("template", "")} for r in found if isinstance(r, dict) and r.get("pattern") in BASE and r.get("template")]
    bank = [b.lower() for b in audience.get("language_bank", []) if isinstance(b, str)]
    themes = [x.get("theme", "") for key in ("questions", "objections") for x in audience.get(key, []) if isinstance(x, dict) and x.get("theme")]
    allowed = set(re.findall(r"\d+(?:[.,]\d+)*", brain)) | {str(x.get("count")) for key in ("questions", "objections") for x in audience.get(key, []) if isinstance(x, dict) and x.get("count") is not None}
    ctx_words = toks(" ".join([str(idea.get("problem", "")), str(idea.get("who", "")), *themes]))
    mvp = idea.get("mvp") if isinstance(idea.get("mvp"), list) else []
    mvp_words = toks(" ".join(map(str, mvp)) + " " + str(idea.get("title", "")))
    vid = k.read(ctx, "launch/inputs/vidiq-titles.json", []) or []
    vidiq = {str(r.get("title") or r.get("text", "")).lower(): r.get("score", 0) for r in vid if isinstance(r, dict)}
    prev = (k.read(ctx, "launch/hooks.json", {}) or {}).get("hooks", [])
    prev = [h for h in prev if isinstance(h, dict) and h.get("text")]
    old = {(h["platform"], h["text"].lower()): h for h in prev if h.get("platform")}
    next_id = max([int(h["id"][2:]) for h in prev if re.match(r"h-\d+$", str(h.get("id", "")))] + [0]) + 1
    pain = (themes[0] if themes else " ".join(str(idea.get("problem", "")).split()[:6])).lower()
    kept, used_model = [], False
    for platform in platforms:
        kinds = kinds_for(platform)
        answer = k.ask('Return JSON only: {"hooks": [{"kind": "spoken, title or cover", "text": "...", "pattern": "...", "theme": "..."}]}. Write 12 hooks of each kind for ' + platform
                       + ": spoken (first three seconds, under 12 words), title (YouTube, up to 60 characters), cover (on-image text, up to 7 words). Kinds wanted: " + ", ".join(kinds)
                       + ". Each hook uses one theme and one language-bank phrase. Patterns: " + ", ".join(p["pattern"] for p in patterns[:10])
                       + ". Claim only what the brain says. No dashes, no exclamation marks, no hype, no invented numbers.\n\nBRAIN\n" + brain[:2500] + "\n\nTHEMES\n" + "; ".join(themes[:10]) + "\nLANGUAGE BANK\n" + "; ".join(bank[:15]))
        raw = [h for h in (answer.get("hooks") if isinstance(answer, dict) and isinstance(answer.get("hooks"), list) else []) if isinstance(h, dict) and h.get("kind") in kinds and tidy(h.get("text", ""))]
        used_model = used_model or bool(raw)
        if not raw:
            raw = template_hooks(platform, patterns[:6], pain, tidy(idea.get("who", "")).split(",")[0][:40].lower(), tidy(idea.get("title", "")), bank[0] if bank else "")
        seen = set()
        for order, h in enumerate(raw):
            text = tidy(h["text"])
            if text.lower() in seen or rejected(text, h["kind"], allowed):
                continue
            seen.add(text.lower())
            item = {"platform": platform, "kind": h["kind"], "text": text, "pattern": tidy(h.get("pattern", "")) or "curiosity gap", "theme": tidy(h.get("theme", "")) or pain}
            s, v = score(item, ctx_words, bank, winners, names, mvp_words, vidiq)
            item["score"], item["_tie"] = s, (v, -order)
            kept.append(item)
    per = 5
    while True:
        chosen = []
        for platform in platforms:
            for kind in kinds_for(platform):
                combo = sorted((h for h in kept if h["platform"] == platform and h["kind"] == kind), key=lambda h: (-h["score"], [-x for x in h["_tie"]]))
                chosen += combo[:per]
        if len(chosen) <= 30 or per == 1:
            break
        per -= 1
    chosen = chosen[:30]
    if not chosen:
        return {"skipped": "no hook passed the checks"}
    hooks = []
    for h in chosen:
        before = old.get((h["platform"], h["text"].lower()))
        hid, status = (before["id"], before.get("status", "candidate")) if before else (f"h-{next_id:03d}", "candidate")
        next_id += 0 if before else 1
        hooks.append({"id": hid, "platform": h["platform"], "kind": h["kind"], "text": h["text"], "pattern": h["pattern"], "theme": h["theme"], "score": h["score"], "status": status})
    ids = {h["id"] for h in hooks}
    hooks += [h for h in prev if h.get("id") not in ids and h.get("status", "candidate") != "candidate"]
    k.write(ctx, "launch/hooks.json", {"hooks": hooks})
    md = [f"# Hooks: {tidy(idea.get('title', ctx['slug']))}", "" if used_model else "Template hooks: no model answered.", ""]
    for platform in platforms:
        md += [f"## {platform}", "| Id | Kind | Score | Hook | Pattern | Theme | Status |", "|---|---|---|---|---|---|---|"]
        md += [f"| {h['id']} | {h['kind']} | {h['score']} | {h['text'].replace('|', '/')} | {h['pattern']} | {h['theme']} | {h['status']} |" for h in sorted((x for x in hooks if x["platform"] == platform), key=lambda x: -x["score"])]
        md.append("")
    k.write(ctx, "launch/hooks.md", "\n".join(md))
    return {"summary": f"{len(hooks)} hooks across {len(platforms)} platforms ({'model' if used_model else 'template'} written); top score {max(h['score'] for h in hooks)}.", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
