"""Thumbnail and Cover Design: GitHub implementation of departments/marketing/creation/thumbnail-and-cover-design/SKILL.md.

Three variants (a, b, c: text at top, centre, bottom, key word in the accent colour) per post that has no cover,
rendered with ImageMagick inside the central 1080 square. Checks run in code on the brand colours and the text
size, the vidIQ score picks the winner if Charlie exported one, else the best checked variant. Without ImageMagick
a brief.md per post is written and the render is marked pending.
"""
import re
import shutil
import subprocess

from foundry import jobkit as k

IM = shutil.which("convert") or shutil.which("magick")
BRAND = {"colours": {"bg": "#FFFFFF", "text": "#111111", "accent": "#0B5FFF"}, "font": "system-ui, sans-serif", "logo": ""}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
POSITIONS = {"a": "top", "b": "centre", "c": "bottom"}
MAX_BYTES = 2 * 1024 * 1024


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


def short(text, n=4):
    words = re.sub(r"[^\w\s£'%]", "", tidy(text)).split()
    return " ".join(words[:n])


def variant(path, bg_file, w, h, text, pos, brand, accent_ok):
    c, font = brand["colours"], ["-font", f] if (f := font_path(brand.get("font"))) else []
    sq = min(w, h, 1080) if h > w else min(h, 1080)
    side = int((h - sq) / 2) + 60 if h > w else 60
    pt = int(0.12 * h)
    words = text.split()
    longest = max((len(x) for x in words), default=1)
    avail = int(min(w, 1080) * 0.84)
    pt = min(pt, int(avail / (0.62 * longest)))
    fg, key = c["text"], (c["accent"] if accent_ok else c["text"])
    cap = lambda t, col: ["(", "-size", f"{avail}x", "-background", "none", "-fill", col, *font, "-pointsize", str(pt), "-gravity", "center", f"caption:{t}", ")"]
    head, last = " ".join(words[:-1]), words[-1] if words else ""
    layer = ["(", *(cap(head, fg) if head else []), *cap(last, key), "-background", "none", "-gravity", "center", "-append", ")"]
    base = [bg_file, "-resize", f"{w}x{h}^", "-gravity", "center", "-extent", f"{w}x{h}", "-fill", c["bg"], "-colorize", "60%"] if bg_file else ["-size", f"{w}x{h}", f"xc:{c['bg']}"]
    place = {"top": ["-gravity", "north", "-geometry", f"+0+{side}"], "centre": ["-gravity", "center"], "bottom": ["-gravity", "south", "-geometry", f"+0+{side}"]}[pos]
    ok = run_im([*base, *layer, *place, "-composite", "-depth", "8", path])
    return ok, 0.7 * pt / h


def main(ctx):
    folder, idea = ctx["folder"], ctx["idea"]
    posts = [r for r in (k.read(ctx, "launch/video/index.json", []) or []) if isinstance(r, dict) and r.get("post_id")] or [r for r in (k.read(ctx, "launch/scripts/index.json", []) or []) if isinstance(r, dict) and r.get("post_id")]
    old = [r for r in (k.read(ctx, "launch/thumbnails/index.json", []) or []) if isinstance(r, dict)]
    done = {r.get("post_id") for r in old}
    todo = [p for p in posts if p["post_id"] not in done][:12]
    if not todo:
        return {"skipped": "no posts needing covers" if posts else "no launch/video/index.json or launch/scripts/index.json: no posts to cover"}
    hooks = [h for h in (k.read(ctx, "launch/hooks.json", {}) or {}).get("hooks", []) if isinstance(h, dict) and h.get("kind") in ("cover", "title") and h.get("status") != "rejected"]
    brand = k.read(ctx, "launch/brand.json")
    brand = brand if isinstance(brand, dict) and isinstance(brand.get("colours"), dict) else dict(BRAND)
    brand["colours"] = {key: (brand["colours"].get(key) if HEX.match(str(brand["colours"].get(key, ""))) else BRAND["colours"][key]) for key in BRAND["colours"]}
    texts = {}
    for p in todo:
        pool = sorted((h for h in hooks if h.get("platform") == p.get("platform")), key=lambda h: (h.get("kind") != "cover", -(h.get("score") or 0))) or sorted(hooks, key=lambda h: -(h.get("score") or 0))
        texts[p["post_id"]] = short(pool[0]["text"]) if pool else short(idea.get("title", ctx["slug"]))
    answer = k.ask('Return JSON only: {"covers": [{"post_id": "...", "text": "4 words or fewer"}]}. Tighten each cover text to 4 words or fewer, keeping the head of the sentence and its meaning. No hype.\n\n' + "\n".join(f"{i}: {t}" for i, t in texts.items()))
    for c in (answer.get("covers") if isinstance(answer, dict) and isinstance(answer.get("covers"), list) else []):
        if isinstance(c, dict) and c.get("post_id") in texts and 0 < len(short(c.get("text", "")).split()) <= 4:
            texts[c["post_id"]] = short(c["text"])
    vid = {(str(r.get("post_id")), str(r.get("variant", "")).lower()): r.get("score") for r in (k.read(ctx, "launch/inputs/vidiq-thumbnails.json", []) or []) if isinstance(r, dict)}
    reqs = [r for r in (k.read(ctx, "launch/image-requests.json", []) or []) if isinstance(r, dict)]
    ids = {r.get("id") for r in reqs}
    rows, rendered = [], 0
    for p in todo:
        pid, platform = p["post_id"], str(p.get("platform", "tiktok"))
        w, h = (1280, 720) if platform == "youtube" and (p.get("duration_s") or 0) > 60 else (1080, 1920)
        if f"cover-{pid}" not in ids:
            reqs.append({"id": f"cover-{pid}", "purpose": "cover background", "text": "", "size": f"{w}x{h}", "keywords": [str(idea.get("category", "")), str(idea.get("title", ""))]})
        d, text = f"launch/thumbnails/{pid}", texts[pid]
        accent_ok = contrast(brand["colours"]["accent"], brand["colours"]["bg"]) >= 4.5
        if not IM or ctx["dry_run"]:
            k.write(ctx, f"{d}/brief.md", f"# Cover brief {pid}\n\nSize {w}x{h}. Text: {text}\nVariants: a text at top, b centre, c bottom, key word in the accent colour, all inside the central 1080 square.\nRender pending: ImageMagick not found.")
            rows.append({"post_id": pid, "platform": platform, "chosen": "", "checks": {}, "vidiq_score": None, "render": "pending"})
            continue
        bg = next((str(folder / "launch/images" / f"cover-{pid}{e}") for e in (".jpg", ".png") if (folder / "launch/images" / f"cover-{pid}{e}").exists()), None)
        (folder / d).mkdir(parents=True, exist_ok=True)
        results = {}
        for v, pos in POSITIONS.items():
            path = folder / d / f"{v}.png"
            ok, ratio = variant(str(path), bg, w, h, text, pos, brand, accent_ok)
            if ok and path.exists():
                run_im([str(path), "-resize", "160x160", str(folder / d / ".small.png")])
                small_h = 160 if h > w else 90
                checks = {"contrast": contrast(brand["colours"]["text"], brand["colours"]["bg"]) >= 4.5 and ratio >= 0.08, "size": path.stat().st_size <= MAX_BYTES, "small_legible": ratio >= 0.08 and ratio * small_h >= 6}
                results[v] = (checks, contrast(brand["colours"]["text"], brand["colours"]["bg"]))
                ctx["outputs"].append(f"{d}/{v}.png")
        (folder / d / ".small.png").unlink(missing_ok=True)
        if not results:
            rows.append({"post_id": pid, "platform": platform, "chosen": "", "checks": {}, "vidiq_score": None, "render": "failed"})
            continue
        scored = {v: vid.get((pid, v)) for v in results}
        best = max(results, key=lambda v: (all(results[v][0].values()), scored[v] if isinstance(scored[v], (int, float)) else -1, results[v][1], -ord(v)))
        shutil.copyfile(folder / d / f"{best}.png", folder / d / "chosen.png")
        ctx["outputs"].append(f"{d}/chosen.png")
        rendered += 1
        rows.append({"post_id": pid, "platform": platform, "chosen": f"{d}/chosen.png", "variant": best, "checks": results[best][0], "vidiq_score": scored[best]})
    k.write(ctx, "launch/thumbnails/index.json", old + rows)
    k.write(ctx, "launch/image-requests.json", reqs)
    return {"summary": f"{rendered} of {len(todo)} posts have three cover variants and a checked winner." + ("" if IM else " Render pending: ImageMagick not found, briefs written.") + " Cover background requests added to launch/image-requests.json for image-generation.", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
