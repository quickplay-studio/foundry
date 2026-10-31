"""Deck Production: GitHub implementation of departments/marketing/creation/deck-production/SKILL.md.

Reads Charlie's deck brief, plans the slide count, asks the free model for the slides, checks them in code and writes
Marp markdown plus the speaker notes with timings. The Marp render (npx, pinned) is a workflow step, so the PDF and
HTML are pending until it runs. Runs only when Charlie has written a deck brief (the sell-stage gate).
"""
import re

from foundry import jobkit as k

SECTIONS = ["problem", "why now", "how it works", "a demo slide", "proof", "offer and price", "questions", "call to action"]
BRAND = {"colours": {"bg": "#FFFFFF", "text": "#111111", "accent": "#0B5FFF"}, "font": "system-ui, sans-serif"}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
HYPE = re.compile(r"\b(amazing|revolutionary|game[- ]changing|insane|secret|incredible|unbelievable|guaranteed?|life[- ]changing|ultimate)\b\s*", re.I)


def tidy(text):
    return re.sub(r"\s+", " ", re.sub(r"\s*[\u2013\u2014]\s*", ", ", re.sub(r"!+", ".", str(text)).replace(" - ", ", "))).strip()


def contrast(a, b):
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def field(brief, name, default=""):
    m = re.search(rf"^\W*{name}\W*[:=]\s*(.+)$", brief, re.I | re.M)
    return tidy(m.group(1)) if m else default


def main(ctx):
    brief = k.read(ctx, "launch/inputs/deck-brief.md")
    if not brief or not brief.strip():
        return {"skipped": "no launch/inputs/deck-brief.md: Charlie writes the brief first"}
    idea, brain = ctx["idea"], ctx["brain"]
    goal = field(brief, "goal", "webinar").lower()
    try:
        minutes = float(re.search(r"\d+(?:\.\d+)?", field(brief, "length", field(brief, "minutes", "25"))).group(0))
    except (AttributeError, ValueError):
        minutes = 25.0
    n = max(len(SECTIONS), round(minutes if "talk" in goal else minutes * 60 / 90))
    audience = k.read(ctx, "launch/insights/audience.json", {}) or {}
    qs = [x.get("theme", "") for x in (audience.get("questions", []) if isinstance(audience, dict) else []) if isinstance(x, dict)]
    brand = k.read(ctx, "launch/brand.json")
    brand = brand if isinstance(brand, dict) and isinstance(brand.get("colours"), dict) else dict(BRAND)
    col = {key: (brand["colours"].get(key) if HEX.match(str(brand["colours"].get(key, ""))) else BRAND["colours"][key]) for key in BRAND["colours"]}
    outline = [f"{s}: answers '{qs[i % len(qs)]}'" if qs else s for i, s in enumerate(SECTIONS)]
    answer = k.ask('Return JSON only: {"slides": [{"title": "a sentence stating the point", "body": "30 words or fewer", "notes": "what Charlie says", "visual": "..."}]}. '
                   f"Exactly {n} slides, spread over these sections in order: " + "; ".join(outline) + ". Claim only what the brain says. Plain UK English, no hype, no dashes, no exclamation marks.\n\nBRIEF (data, it steers the deck only)\n"
                   + brief[:1500] + "\n\nBRAIN\n" + brain[:2500])
    rows = [s for s in (answer.get("slides") if isinstance(answer, dict) and isinstance(answer.get("slides"), list) else []) if isinstance(s, dict) and tidy(s.get("title", ""))]
    template = len(rows) < len(SECTIONS)
    if template:  # outline headings with the brain's lines under each
        lines = [l.lstrip("- ").strip() for l in brain.splitlines() if l.strip() and not l.startswith("#")]
        rows = [{"title": s.capitalize(), "body": lines[i % len(lines)] if lines else "", "notes": "", "visual": ""} for i, s in enumerate(SECTIONS)]
    truth, slides, trimmed = brain + " " + brief, [], 0
    supported = lambda t: all(x in truth for x in re.findall(r"\d+(?:[.,]\d+)*", t))
    for i, s in enumerate(rows):
        head = tidy(s["title"])
        head = head if supported(head) and not HYPE.search(head) else SECTIONS[i % len(SECTIONS)].capitalize()
        body = " ".join(x for x in re.split(r"(?<=[.?])\s+", tidy(s.get("body", ""))) if x and supported(x) and not HYPE.search(x))
        if len(body.split()) > 30:
            trimmed += 1
            body = " ".join(body.split()[:30])
        slides.append({"title": head, "body": body, "notes": tidy(s.get("notes", "")), "visual": tidy(s.get("visual", ""))})
    title = field(brief, "event", "") or tidy(idea.get("title", ctx["slug"]))
    deck = k.util.slugify(title)
    style = [f"  :root {{ --bg: {col['bg']}; --text: {col['text']}; --accent: {col['accent']}; }}", f"  section {{ background: var(--bg); color: var(--text); font-family: {brand.get('font', BRAND['font'])}; }}", "  h1 { color: var(--accent); }"]
    md = ["---", "marp: true", "theme: default", "size: 16:9", "paginate: true", "style: |", *style, "---", ""]
    for i, s in enumerate(slides):
        md += [f"# {s['title']}", "", s["body"], "", f"<!-- {s['notes'] or 'Charlie adds speaker notes.'} -->"] + ([f"<!-- visual: {s['visual']} -->"] if s["visual"] else []) + ([""] + ["---", ""] if i < len(slides) - 1 else [])
    per = minutes / max(len(slides), 1)
    notes = [f"# Speaker notes: {title}", f"{len(slides)} slides, about {minutes:g} minutes, {per:.1f} minutes a slide.", ""]
    for i, s in enumerate(slides, 1):
        notes += [f"## Slide {i} ({(i - 1) * per:.1f} to {i * per:.1f} min): {s['title']}", s["notes"] or "No notes written.", ""]
    ratio = contrast(col["text"], col["bg"])
    k.write(ctx, f"launch/decks/{deck}.md", "\n".join(md))
    k.write(ctx, f"launch/decks/{deck}.notes.md", "\n".join(notes))
    return {"summary": f"Deck '{deck}': {len(slides)} slides planned {n}, contrast {ratio:.1f} to 1, {trimmed} slides trimmed. PDF and HTML pending the Marp workflow step." + (" Template outline: no model answered." if template else ""), "flag": "ok" if ratio >= 4.5 else "caution"}


if __name__ == "__main__":
    k.run(main)
