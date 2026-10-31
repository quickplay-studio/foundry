"""Carousel Production: GitHub implementation of departments/marketing/creation/carousel-production/SKILL.md.

Up to three carousels from unused cover hooks: seven slides each (cover, problem, three points, proof, call to
action), copy from the free model checked against the brain, slides rendered at 1080 by 1350 with an 80 pixel
margin using ImageMagick (the brief allows it in place of headless Chrome), plus a PDF for LinkedIn. Without
ImageMagick the copy and index are still written and the render is marked pending.
"""
import re
import shutil
import subprocess
import tempfile

from foundry import jobkit as k

IM = shutil.which("convert") or shutil.which("magick")
BRAND = {"colours": {"bg": "#FFFFFF", "text": "#111111", "accent": "#0B5FFF"}, "font": "system-ui, sans-serif", "logo": ""}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
W, H, MARGIN = 1080, 1350, 80
ROLES = ["cover", "problem", "point 1", "point 2", "point 3", "proof", "call to action"]
HYPE = re.compile(r"\b(amazing|revolutionary|game[- ]changing|insane|secret|incredible|unbelievable|guaranteed?|life[- ]changing|ultimate)\b", re.I)


def tidy(text):
    return re.sub(r"\s+", " ", re.sub(r"\s*[\u2013\u2014]\s*", ", ", re.sub(r"!+", ".", str(text)).replace(" - ", ", "))).strip()


def contrast(a, b):
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def font_path(family):
    fam = str(family).split(",")[0].strip(" '\"")
    if not shutil.which("fc-match") or not fam or fam in ("system-ui", "sans-serif"):
        return None
    try:
        return subprocess.run(["fc-match", "-f", "%{file}", fam], capture_output=True, text=True, timeout=10).stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


def run_im(args):
    try:
        return subprocess.run([IM, *args], capture_output=True, timeout=90).returncode == 0
    except Exception:  # noqa: BLE001
        return False


def slide(path, head, body, n, total, brand):
    c = brand["colours"]
    fg = c["text"] if contrast(c["text"], c["bg"]) >= 4.5 else ("#000000" if contrast("#000000", c["bg"]) >= contrast("#FFFFFF", c["bg"]) else "#FFFFFF")
    font = ["-font", f] if (f := font_path(brand.get("font"))) else []
    tw = f"{W - 2 * MARGIN}x"
    cap = lambda size, text: ["-size", tw, "-background", c["bg"], "-fill", fg, *font, "-pointsize", str(size), "-gravity", "west", f"caption:{text}"]
    args = ["-size", f"{W}x{H}", f"xc:{c['bg']}", "(", "-size", f"{W - 2 * MARGIN}x14", f"xc:{c['accent']}", ")", "-gravity", "northwest", "-geometry", f"+{MARGIN}+{MARGIN}", "-composite",
            "(", *cap(76, head), "(", "-size", f"{W - 2 * MARGIN}x48", f"xc:{c['bg']}", ")", *cap(46, body), "-append", ")", "-gravity", "northwest", "-geometry", f"+{MARGIN}+{MARGIN + 80}", "-composite",
            "(", "+size", "-background", c["bg"], "-fill", c["accent"], *font, "-pointsize", "40", f"label:{n}/{total}", ")", "-gravity", "southeast", "-geometry", f"+{MARGIN}+{MARGIN}", "-composite", "-depth", "8", path]
    ok = run_im(args)
    return ok


def main(ctx):
    hooks = [h for h in (k.read(ctx, "launch/hooks.json", {}) or {}).get("hooks", []) if isinstance(h, dict) and h.get("kind") == "cover" and h.get("status") != "rejected"]
    index = [r for r in (k.read(ctx, "launch/carousels/index.json", []) or []) if isinstance(r, dict)]
    used = {r.get("hook_id") for r in index}
    picked, themes = [], set()
    for h in sorted((h for h in hooks if h.get("id") not in used), key=lambda h: -(h.get("score") or 0)):
        if h.get("theme") not in themes and len(picked) < 3:
            themes.add(h.get("theme"))
            picked.append(h)
    if not picked:
        return {"skipped": "no unused cover hook in launch/hooks.json" if hooks else "launch/hooks.json has no cover hooks: run hook-writing first"}
    idea, brain, folder = ctx["idea"], ctx["brain"], ctx["folder"]
    brand = k.read(ctx, "launch/brand.json")
    made_brand = not (isinstance(brand, dict) and isinstance(brand.get("colours"), dict))
    brand = dict(BRAND) if made_brand else brand
    brand["colours"] = {key: (brand["colours"].get(key) if HEX.match(str(brand["colours"].get(key, ""))) else BRAND["colours"][key]) for key in BRAND["colours"]}
    if made_brand:
        k.write(ctx, "launch/brand.json", brand)
    audience = k.read(ctx, "launch/insights/audience.json", {}) or {}
    points = [x.get("theme", "") for x in (audience.get("questions", []) if isinstance(audience, dict) else []) if isinstance(x, dict)][:5]
    mvp = [str(m) for m in idea.get("mvp", [])] if isinstance(idea.get("mvp"), list) else []
    src = next((p.get("source", "") for p in idea.get("proof", []) if isinstance(p, dict)), "") if isinstance(idea.get("proof"), list) else ""
    proof = f"Demand seen on {tidy(src)}" if src else ""
    nxt = max([int(r["carousel_id"][2:]) for r in index if re.match(r"c-\d+$", str(r.get("carousel_id", "")))] + [0]) + 1
    made, rendered = [], 0
    for h in picked:
        cid, theme = f"c-{nxt:03d}", h.get("theme", "")
        nxt += 1
        answer = k.ask('Return JSON only: {"slides": [{"headline": "8 words or fewer", "body": "25 words or fewer", "alt": "alt text"}]}. Exactly seven slides in order: ' + ", ".join(ROLES)
                       + f". The cover headline is this hook: \"{h.get('text', '')}\". Points teach something about: {', '.join(points) or theme}. Every number or claim must be in the brain. Plain UK English, no hype, no dashes, no exclamation marks.\n\nBRAIN\n{brain[:2500]}")
        raw = [s for s in (answer.get("slides") if isinstance(answer, dict) and isinstance(answer.get("slides"), list) else []) if isinstance(s, dict) and tidy(s.get("headline", ""))]
        fallback = [(h.get("text", ""), ""), (str(idea.get("problem", "")).split(".")[0], ""), *[(m, "") for m in (mvp + ["", "", ""])[:3]], ("What it does today", proof), ("Sign up at the link in bio", "")]
        slides = []
        for i, role in enumerate(ROLES):
            s = raw[i] if len(raw) == len(ROLES) else {}
            head, body = tidy(s.get("headline") or fallback[i][0]), tidy(s.get("body") or fallback[i][1])
            if HYPE.search(head + body) or any(n not in brain for n in re.findall(r"\d+(?:[.,]\d+)*", head + " " + body)):
                head, body = tidy(fallback[i][0]), tidy(fallback[i][1])
            slides.append({"headline": " ".join(head.split()[:8]), "body": " ".join(body.split()[:25]), "alt": tidy(s.get("alt") or f"Slide {i + 1}: {head}")[:125]})
        d = folder / "launch/carousels" / cid
        copy = [f"# Carousel {cid}: {tidy(idea.get('title', ctx['slug']))}", f"Hook {h.get('id')} ({theme}). Brand look is a default if launch/brand.json was just created: Charlie approves it once.", ""]
        for i, s in enumerate(slides, 1):
            copy += [f"## Slide {i:02d}", f"Headline: {s['headline']}", f"Body: {s['body']}", f"Alt: {s['alt']}", ""]
        k.write(ctx, f"launch/carousels/{cid}/copy.md", "\n".join(copy))
        pdf = ""
        if IM and not ctx["dry_run"]:
            d.mkdir(parents=True, exist_ok=True)
            files = []
            for i, s in enumerate(slides, 1):
                p = d / f"slide-{i:02d}.png"
                if slide(str(p), s["headline"], s["body"], i, len(slides), brand):
                    if p.stat().st_size > 400 * 1024:
                        run_im([str(p), "-colors", "128", str(p)])
                    files.append(str(p))
                    ctx["outputs"].append(str(p.relative_to(folder)))
            if len(files) == len(slides) and run_im([*files, str(d / "carousel.pdf")]):
                pdf = f"launch/carousels/{cid}/carousel.pdf"
                ctx["outputs"].append(pdf)
            rendered += len(files)
        index.append({"carousel_id": cid, "hook_id": h.get("id"), "slides": len(slides), "pdf": pdf, "theme": theme, **({} if IM else {"render": "pending: ImageMagick not found"})})
        made.append(cid)
    k.write(ctx, "launch/carousels/index.json", index)
    return {"summary": f"{len(made)} carousels written ({', '.join(made)}), {rendered} slides rendered." + ("" if IM else " Render pending: ImageMagick not found, copy only.") + (" Default brand.json created for Charlie to approve." if made_brand else ""), "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
