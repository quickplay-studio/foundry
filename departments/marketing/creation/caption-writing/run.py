"""Caption Writing: GitHub implementation of departments/marketing/creation/caption-writing/SKILL.md.

A platform-correct caption for every scripted post that has none yet. The model writes the body and
hashtags; code places the call to action and the UTM link, applies the platform limits and checks the voice.
"""
import json
import re

from foundry import jobkit as k

# Platform limits in characters (as of Oct 2026, check the limit). The only place to edit.
LIMITS = {"youtube": 5000, "x": 280, "linkedin": 3000, "instagram": 2200, "tiktok": 2200, "facebook": 2200}
YT_TITLE_LIMIT = 100
BIO = ("instagram", "tiktok")  # links are not clickable
HASHTAGS = {"instagram": (3, 5), "tiktok": (3, 5), "x": (0, 1), "linkedin": (0, 1), "youtube": (0, 3), "facebook": (0, 3)}
HYPE = re.compile(r"\b(amazing|revolutionary|game[- ]changing|insane|secret|incredible|unbelievable|guaranteed?|life[- ]changing|ultimate)\b", re.I)


def tidy(text):
    return re.sub(r"[ \t]+", " ", re.sub(r"\s*[\u2013\u2014]\s*", ", ", re.sub(r"!+", ".", str(text)).replace(" - ", ", "))).strip()


def link_for(site, platform, post_id):
    if not site:
        return ""
    return f"{site}{'&' if '?' in site else '?'}utm_source={platform}&utm_medium=organic&utm_campaign=launch&utm_content={post_id}"


def tags(model_tags, extra, platform):
    lo, hi = HASHTAGS.get(platform, (0, 3))
    out = []
    for source in (model_tags if isinstance(model_tags, list) else [], extra):
        for t in source:
            t = re.sub(r"[^A-Za-z0-9]", "", str(t))
            if 2 < len(t) <= 24 and "#" + t.lower() not in [x.lower() for x in out] and (source is not extra or len(out) < lo):
                out.append("#" + t)
    return out[:hi]


def assemble(platform, body, hashtags, link):
    """Body, hashtags and call to action in the right places. Returns (caption, cta)."""
    lines = [l for l in body.strip().splitlines()] or [""]
    tag_line = " ".join(hashtags)
    if platform in BIO:
        cta, parts = "Link in bio", lines + ([""] + [tag_line] if tag_line else []) + ["", "Link in bio"]
    elif platform == "youtube":
        cta = f"Sign up: {link}" if link else "Sign up on the site"
        parts = [lines[0], cta] + lines[1:] + ([""] + [tag_line] if tag_line else [])
    else:
        cta = f"Sign up: {link}" if link else "Sign up on the site"
        parts = lines + ([""] + [tag_line] if tag_line else []) + ["", cta]
    return "\n".join(parts).strip(), cta


def fit_limit(platform, body, hashtags, link):
    limit = LIMITS.get(platform, 2200)
    caption, cta = assemble(platform, body, hashtags, link)
    lines = body.splitlines()
    while len(caption) > limit and len(lines) > 1:
        lines.pop()
        caption, cta = assemble(platform, "\n".join(lines), hashtags, link)
    if len(caption) > limit:
        caption, cta = assemble(platform, lines[0][:max(20, limit - len(cta) - 10)].rsplit(" ", 1)[0], [], link)
    return caption, cta


def valid(platform, caption, alt, link):
    if len(caption) > LIMITS.get(platform, 2200) or re.search(r"[\u2013\u2014!]", caption) or HYPE.search(caption) or len(alt) > 125:
        return False
    if platform in BIO:
        return "http" not in caption and caption.endswith("Link in bio")
    if platform == "youtube" and link:
        return link in "\n".join(caption.splitlines()[:2])
    return not link or caption.endswith(link)


def main(ctx):
    idea, brain = ctx["idea"], ctx["brain"]
    scripts = []
    for p in sorted((ctx["folder"] / "launch/scripts").glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8")) if p.name != "index.json" else None
        if isinstance(data, dict) and data.get("post_id"):
            scripts.append(data)
    if not scripts:
        return {"skipped": "no scripts in launch/scripts: run script-writing first"}
    channels = k.read(ctx, "launch/channels.json", {}) or {}
    platforms = [str(p).lower() for p in channels.get("platforms", [])] if isinstance(channels, dict) and channels.get("platforms") else ["tiktok", "instagram", "youtube"]
    site = str(channels.get("site", "")).strip().rstrip("/") if isinstance(channels, dict) else ""
    hooks = {h.get("id"): h.get("text", "") for h in (k.read(ctx, "launch/hooks.json", {}) or {}).get("hooks", []) if isinstance(h, dict)}
    audience = k.read(ctx, "launch/insights/audience.json", {}) or {}
    themes = [x.get("theme", "") for x in audience.get("questions", []) + audience.get("objections", []) if isinstance(x, dict)] if isinstance(audience, dict) else []
    extra = [re.sub(r"\W", "", t) for t in themes][:6]
    old = k.read(ctx, "launch/captions.json", {}) or {}
    rows = [r for r in (old.get("captions", []) if isinstance(old, dict) else old) if isinstance(r, dict)]
    done = {(r.get("post_id"), r.get("platform")) for r in rows}
    mvp = idea.get("mvp") if isinstance(idea.get("mvp"), list) and idea.get("mvp") else [idea.get("problem", "")]
    price = (re.search(r"£\s?\d[\d,.]*(?:\s?(?:/|per|a)\s?(?:month|year|week))?", str(idea.get("money", "")) + brain) or [""])[0]
    product_line = tidy(f"{idea.get('title', ctx['slug'])}: {str(mvp[0]).rstrip('.')}." + (f" {price}." if price else ""))
    new = failed = used_model = 0
    for s in scripts:
        todo = [p for p in platforms if (s["post_id"], p) not in done]
        if not todo or new >= 36:
            continue
        lines_v = [l.get("voiceover", "") for l in s.get("lines", []) if isinstance(l, dict)]
        hook = tidy(hooks.get(s.get("hook_id"), "") or (lines_v[0] if lines_v else ""))
        promo = bool(price and any(price in v for v in lines_v)) or not lines_v
        answer = k.ask('Return JSON only: {"captions": [{"platform": "...", "caption": "...", "hashtags": ["..."], "alt": "..."}]}. One per platform: ' + ", ".join(todo)
                       + ". The caption body only, no link, no call to action, no hashtags in it. The first line is the hook or its natural continuation. "
                       + ("This post promotes the product: state what it does and the price in the first two lines. " if promo else "This is a value post: mention the product once, near the end. ")
                       + "Alt text 125 characters or fewer. Plain, no hype, no exclamation marks, no dashes, no emoji.\n\nHOOK\n" + hook + "\nSCRIPT\n" + "\n".join(lines_v)[:1500]
                       + "\nPRODUCT\n" + product_line + "\nBRAIN\n" + brain[:1500])
        by = {str(c.get("platform", "")).lower(): c for c in (answer.get("captions") if isinstance(answer, dict) and isinstance(answer.get("captions"), list) else []) if isinstance(c, dict)}
        for p in todo:
            link, c = link_for(site, p, s["post_id"]), by.get(p, {})
            body = tidy(c.get("caption", "")) if isinstance(c.get("caption"), str) else ""
            used_model += bool(body)
            variants = [(body, c.get("hashtags"), tidy(c.get("alt", ""))[:125])] * bool(body) + [(f"{hook}\n{product_line}", [], tidy(hook)[:125])]
            for body_v, tag_v, alt in variants:  # model caption first, then the template fallback
                caption, cta = fit_limit(p, body_v, tags(tag_v, extra, p), link_for(site, p, s["post_id"]))
                if valid(p, caption, alt, link):
                    rows.append({"post_id": s["post_id"], "platform": p, "caption": caption, "hashtags": [t for t in caption.split() if t.startswith("#")], "cta": cta,
                                 "link": "" if p in BIO else link, "alt": alt, "char_count": len(caption)})
                    new += 1
                    break
            else:
                failed += 1
    if not rows:
        return {"skipped": "no caption passed the checks"}
    bio = {p: link_for(site, p, "bio") for p in platforms if site}
    k.write(ctx, "launch/captions.json", {"bio_link": bio, "captions": rows})
    md = [f"# Captions: {tidy(idea.get('title', ctx['slug']))}", "", "Bio links: " + (", ".join(f"{p} {u}" for p, u in bio.items()) if bio else "no site in launch/channels.json, add one"), ""]
    for pid in dict.fromkeys(r["post_id"] for r in rows):
        md += [f"## {pid}"] + [x for r in rows if r["post_id"] == pid for x in (f"### {r['platform']} ({r['char_count']} characters)", r["caption"], f"Alt: {r['alt']}", "")]
    k.write(ctx, "launch/captions.md", "\n".join(md))
    return {"summary": f"{new} new captions across {len(platforms)} platforms ({used_model} from the model), {failed} failed the checks." + ("" if site else " No site in channels.json, so no links."), "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
