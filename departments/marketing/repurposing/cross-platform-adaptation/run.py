"""Cross-Platform Adaptation: GitHub implementation of departments/marketing/repurposing/cross-platform-adaptation/SKILL.md.

One master script becomes a native variant for each platform Charlie has a handle for: vertical video to TikTok,
Reels, Shorts and Facebook Reels; a carousel to Instagram and a LinkedIn document; the key point as an X thread and
a LinkedIn post. Changes the first line, call to action, link and hashtags, never the claims. Nothing is uploaded.
"""
import json
import re

from foundry import jobkit as k

# Limits in characters (as of Oct 2026, check the limit); the same table as caption-writing.
LIMITS = {"youtube": 5000, "x": 280, "linkedin": 3000, "instagram": 2200, "tiktok": 2200, "facebook": 2200}
BIO = ("instagram", "tiktok")
HASHTAGS = {"instagram": 5, "tiktok": 5, "x": 1, "linkedin": 1, "youtube": 3, "facebook": 3}
VIDEO = {"tiktok": "video", "instagram": "reel", "youtube": "short", "facebook": "reel"}
HYPE = re.compile(r"\b(amazing|revolutionary|game[- ]changing|insane|secret|incredible|unbelievable|guaranteed?|life[- ]changing|ultimate)\b", re.I)


def tidy(text):
    return re.sub(r"[ \t]+", " ", re.sub(r"\s*[\u2013\u2014]\s*", ", ", re.sub(r"!+", ".", str(text)).replace(" - ", ", "))).strip()


def retarget(link, platform):
    return re.sub(r"utm_source=[^&]+", f"utm_source={platform}", link) if link else ""


def body_of(caption):
    keep = [l for l in str(caption).splitlines() if not re.match(r"\s*(Link in bio|Sign up:)", l) and not re.fullmatch(r"(\s*#\w+)+\s*", l)]
    return "\n".join(keep).strip()


def build(platform, body, tags, link):
    """Caption with the call to action in the right place, trimmed at a line end to fit the limit."""
    limit = LIMITS.get(platform, 2200)
    cta = "Link in bio" if platform in BIO else (f"Sign up: {link}" if link else "Sign up on the site")
    tag_line = " ".join(tags[:HASHTAGS.get(platform, 3)])
    lines = body.splitlines() or [""]
    while True:
        text = "\n".join(([lines[0], cta] + lines[1:] + ([""] + [tag_line] if tag_line else [])) if platform == "youtube" else (lines + ([""] + [tag_line] if tag_line else []) + ["", cta])).strip()
        if len(text) <= limit or len(lines) == 1:
            return text[:limit] if len(text) > limit else text, cta
        lines.pop()


def thread(text, link):
    posts = [tidy(p) for p in re.split(r"\n\s*\n", str(text)) if tidy(p)][:6] or [""]
    posts = [p if len(p) <= 280 else p[:280].rsplit(" ", 1)[0] for p in posts]
    if link and len(posts[-1]) + len(link) + 1 <= 280:
        posts[-1] += " " + link
    return "\n\n".join(posts), max(len(p) for p in posts)


def main(ctx):
    folder = ctx["folder"]
    masters = []
    for p in sorted((folder / "launch/scripts").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8")) if p.name != "index.json" else None
        if isinstance(d, dict) and d.get("post_id") and not (folder / "launch/adapted" / f"{d['post_id']}.json").exists():
            masters.append(d)
    if not masters:
        return {"skipped": "no master script without an adapted file"}
    channels = k.read(ctx, "launch/channels.json", {}) or {}
    chan = channels if isinstance(channels, dict) else {}
    platforms = [str(p).lower() for p in chan.get("platforms", [])] if chan.get("platforms") else ["tiktok", "instagram", "youtube"]
    platforms = [p for p in platforms if not chan.get("platforms") or (isinstance(chan.get(p), dict) and chan[p].get("handle"))]
    if not platforms:
        return {"skipped": "no platform has a handle in launch/channels.json"}
    caps = k.read(ctx, "launch/captions.json", {}) or {}
    rows = [r for r in (caps.get("captions", []) if isinstance(caps, dict) else caps) if isinstance(r, dict)]
    videos = {r.get("post_id"): r for r in (k.read(ctx, "launch/video/index.json", []) or []) if isinstance(r, dict)}
    cars = {r.get("hook_id"): r for r in (k.read(ctx, "launch/carousels/index.json", []) or []) if isinstance(r, dict)}
    done = 0
    for m in masters:
        pid, mine = m["post_id"], [r for r in rows if r.get("post_id") == m["post_id"]]
        if not mine:
            continue
        master_text = " ".join(str(l.get("voiceover", "")) for l in m.get("lines", []) if isinstance(l, dict)) + " " + " ".join(str(r.get("caption", "")) for r in mine)
        first = next((r for r in mine if r.get("platform") == m.get("platform")), mine[0])
        base_body, tags, link0 = body_of(first.get("caption", "")), first.get("hashtags") or [], first.get("link") or next((r.get("link") for r in mine if r.get("link")), "")
        vfile = (videos.get(pid) or {}).get("file") or (f"launch/video/{pid}.mp4" if (folder / "launch/video" / f"{pid}.mp4").exists() else "")
        car = cars.get(m.get("hook_id"))
        plan = [(p, VIDEO[p], vfile) for p in platforms if p in VIDEO]
        if car and "instagram" in platforms:
            plan.append(("instagram", "carousel", f"launch/carousels/{car['carousel_id']}"))
        if car and "linkedin" in platforms:
            plan.append(("linkedin", "document", car.get("pdf") or f"launch/carousels/{car['carousel_id']}/carousel.pdf"))
        out = []
        for p, fmt, media in plan:
            body = body_of(next((r.get("caption", "") for r in mine if r.get("platform") == p), "")) or base_body
            link = "" if p in BIO else retarget(link0, p)
            text, _ = build(p, body, tags, link)
            out.append({"platform": p, "format": fmt, "text": text, "media": media, "link": link})
        text_platforms = [p for p in ("x", "linkedin") if p in platforms]
        answer = k.ask('Return JSON only: {"variants": [{"platform": "x or linkedin", "format": "thread or text post", "text": "..."}]}. Turn the key point of this script into: ' + ", ".join("an X thread of up to six posts of 280 characters or fewer, posts separated by a blank line" if p == "x" else "a LinkedIn post, slightly more explanatory" for p in text_platforms)
                       + ". Add no claim that is not in the master. Do not include a link. Plain UK English, no hype, no dashes, no exclamation marks.\n\nMASTER\n" + master_text[:2500]) if text_platforms else {}
        by = {str(v.get("platform", "")).lower(): v for v in (answer.get("variants") if isinstance(answer, dict) and isinstance(answer.get("variants"), list) else []) if isinstance(v, dict)}
        for p in text_platforms:
            link = retarget(link0, p)
            raw = tidy(by.get(p, {}).get("text", "")) if isinstance(by.get(p, {}).get("text"), str) else ""
            if p == "x":
                single = base_body[:270].rsplit(" ", 1)[0] if len(base_body) > 270 else base_body  # fallback: master body trimmed to fit
                text, _ = thread(raw or single, link)
                out.append({"platform": "x", "format": "thread", "text": text, "media": "", "link": link})
            else:
                text, _ = build("linkedin", raw or base_body, [], link)
                out.append({"platform": "linkedin", "format": "text post", "text": text, "media": "", "link": link})
        good = []
        for v in out:
            limit = 280 if v["format"] == "thread" else LIMITS.get(v["platform"], 2200)
            parts = v["text"].split("\n\n") if v["format"] == "thread" else [v["text"]]
            count = max(len(x) for x in parts)
            clickable = v["platform"] not in BIO
            bad = count > limit or re.search(r"[\u2013\u2014!]", v["text"]) or HYPE.search(v["text"]) or (v["link"] and not clickable) or (clickable and v["link"] and v["link"] not in v["text"])
            bad = bad or any(n not in master_text for n in re.findall(r"\d+(?:[.,]\d+)*", re.sub(r"https?://\S+", "", v["text"])))
            if not bad:
                good.append({**v, "char_count": count, "limit": limit})
        if good:
            k.write(ctx, f"launch/adapted/{pid}.json", {"post_id": pid, "variants": good})
            done += 1
    if not done:
        return {"skipped": "no master had captions yet, or no variant passed the checks"}
    table = ["# Adapted variants", "", "| Post | Platform | Format | Characters | Media |", "|---|---|---|---|---|"]
    for p in sorted((folder / "launch/adapted").glob("*.json")) if not ctx["dry_run"] else []:
        d = json.loads(p.read_text(encoding="utf-8"))
        table += [f"| {d.get('post_id')} | {v['platform']} | {v['format']} | {v['char_count']} of {v['limit']} | {v['media'] or 'pending'} |" for v in d.get("variants", [])]
    k.write(ctx, "launch/adapted/index.md", "\n".join(table))
    return {"summary": f"{done} masters adapted for {', '.join(platforms)}; media paths are blank where a render does not exist yet.", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
