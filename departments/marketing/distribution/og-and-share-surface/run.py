"""OG and Share Surface: GitHub implementation of departments/marketing/distribution/og-and-share-surface/SKILL.md.

A 1200 by 630 share image per page (ImageMagick, 60 pixel margin, under 300 KB), the open-graph and Twitter tag
block per page, and once the site is live a check that the image and tags are really served. A changed image gets
a new file name because platform preview caches are sticky. Without ImageMagick the tags and index are still
written and the render is marked pending.
"""
import hashlib
import html
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from foundry import jobkit as k

IM = shutil.which("convert") or shutil.which("magick")
BRAND = {"colours": {"bg": "#FFFFFF", "text": "#111111", "accent": "#0B5FFF"}, "font": "system-ui, sans-serif", "logo": ""}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
W, H, M = 1200, 630, 60


def tidy(text):
    return re.sub(r"\s+", " ", re.sub(r"\s*[\u2013\u2014]\s*", ", ", re.sub(r"!+", ".", str(text)).replace(" - ", ", "))).strip()


def trim(text, n):
    text = tidy(text)
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0].rstrip(",;:")


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


def render(path, title, sub, shot, brand, folder):
    c, font = brand["colours"], ["-font", f] if (f := font_path(brand.get("font"))) else []
    fg = c["text"] if contrast(c["text"], c["bg"]) >= 4.5 else "#000000"
    tw = (W - 2 * M - (440 if shot else 0))
    cap = lambda size, col, text: ["(", "-size", f"{tw}x", "-background", c["bg"], "-fill", col, *font, "-pointsize", str(size), "-gravity", "northwest", f"caption:{text}", ")"]
    args = ["-size", f"{W}x{H}", f"xc:{c['bg']}", "(", "-size", f"14x{H - 2 * M}", f"xc:{c['accent']}", ")", "-gravity", "northwest", "-geometry", f"+{M}+{M}", "-composite",
            "(", *cap(68, fg, title), "(", "-size", f"{tw}x30", f"xc:{c['bg']}", ")", *cap(34, fg, sub), "-append", ")", "-gravity", "northwest", "-geometry", f"+{M + 40}+{M}", "-composite"]
    if shot:
        args += ["(", shot, "-resize", f"400x{H - 2 * M}", ")", "-gravity", "east", "-geometry", f"+{M}+0", "-composite"]
    logo = Path(str(brand.get("logo") or "x"))
    logo = logo if logo.is_absolute() else folder / logo
    if brand.get("logo") and logo.is_file():
        args += ["(", str(logo), "-resize", "160x", ")", "-gravity", "southwest", "-geometry", f"+{M + 40}+{M}", "-composite"]
    return run_im(args + ["-strip", "-depth", "8", "-colors", "256", path])


def tag_block(page, title, desc, image_url, site, alt):
    q = lambda v: html.escape(v, quote=True)
    url = f"{site}/" if page == "home" else f"{site}/{page}"
    rows = [("og:title", title), ("og:description", desc), ("og:image", image_url), ("og:image:width", "1200"), ("og:image:height", "630"), ("og:image:alt", alt), ("og:url", url), ("og:type", "website"),
            ("og:site_name", title.split(":")[0][:40]), ("og:locale", "en_GB")]
    return f"<!-- {page} -->\n" + "\n".join(f'<meta property="{n}" content="{q(v)}">' for n, v in rows) + '\n<meta name="twitter:card" content="summary_large_image">'


def main(ctx):
    idea, folder = ctx["idea"], ctx["folder"]
    channels = k.read(ctx, "launch/channels.json", {}) or {}
    site = str(channels.get("site", "")).strip().rstrip("/") if isinstance(channels, dict) else ""
    meta = k.read(ctx, "launch/seo/metadata.json", {}) or {}
    name = tidy(idea.get("title", ctx["slug"]))
    pages = [{"slug": "home", "title": meta.get("title") or name, "desc": meta.get("description") or str(idea.get("problem", ""))}]
    for p in (channels.get("pages", []) if isinstance(channels, dict) and isinstance(channels.get("pages"), list) else []):
        slug = str(p.get("slug", "") if isinstance(p, dict) else p).strip("/")
        if slug and slug != "home":
            pages.append({"slug": slug, "title": (p.get("title") if isinstance(p, dict) else None) or f"{name}: {slug.replace('-', ' ')}", "desc": (p.get("description") if isinstance(p, dict) else None) or meta.get("description") or str(idea.get("problem", ""))})
    answer = k.ask('Return JSON only: {"pages": [{"slug": "...", "title": "60 characters or fewer", "subtitle": "one line, 90 characters or fewer"}]}. Trim each page title and description for a share image. Keep the meaning, no hype.\n\n' + "\n".join(f"{p['slug']}: {p['title']} | {p['desc']}" for p in pages))
    by = {str(r.get("slug")): r for r in (answer.get("pages") if isinstance(answer, dict) and isinstance(answer.get("pages"), list) else []) if isinstance(r, dict)}
    brand = k.read(ctx, "launch/brand.json")
    brand = brand if isinstance(brand, dict) and isinstance(brand.get("colours"), dict) else dict(BRAND)
    brand["colours"] = {key: (brand["colours"].get(key) if HEX.match(str(brand["colours"].get(key, ""))) else BRAND["colours"][key]) for key in BRAND["colours"]}
    refs = sorted(p for p in (folder / "launch/references").glob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg")) if (folder / "launch/references").is_dir() else []
    old = {r.get("page"): r for r in (k.read(ctx, "launch/og/index.json", []) or []) if isinstance(r, dict)}
    reqs = [r for r in (k.read(ctx, "launch/image-requests.json", []) or []) if isinstance(r, dict)]
    rows, blocks, skipped, rendered = [], [], [], 0
    with tempfile.TemporaryDirectory() as tmp:
        for p in pages:
            slug, r = p["slug"], by.get(p["slug"], {})
            title, sub = trim(r.get("title") or p["title"], 60), trim(r.get("subtitle") or p["desc"], 90)
            cand = sorted((folder / "launch/images").glob(f"og-{slug}.*")) if (folder / "launch/images").is_dir() else []
            shot = str(cand[0]) if cand else (str(refs[0]) if refs else None)
            if not shot and f"og-{slug}" not in {x.get("id") for x in reqs}:
                reqs.append({"id": f"og-{slug}", "purpose": "share image background", "text": "", "size": "800x800", "keywords": [str(idea.get("category", "")), name]})
            fname, checks = (old.get(slug) or {}).get("image", "").rsplit("/", 1)[-1] or f"{slug}.png", {}
            if IM and not ctx["dry_run"]:
                tmp_png = str(Path(tmp) / f"{slug}.png")
                if render(tmp_png, title, sub, shot, brand, folder):
                    digest = hashlib.sha1(Path(tmp_png).read_bytes()).hexdigest()[:6]
                    final = folder / "launch/og" / f"{slug}.png"
                    if final.exists() and hashlib.sha1(final.read_bytes()).hexdigest()[:6] != digest:
                        final = folder / "launch/og" / f"{slug}-{digest}.png"  # changed image, new name
                    final.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(tmp_png, final)
                    fname = final.name
                    ctx["outputs"].append(f"launch/og/{fname}")
                    size = final.stat().st_size
                    checks = {"dimensions": "1200x630", "size_ok": size <= 300 * 1024, "contrast_ok": contrast(brand["colours"]["text"], brand["colours"]["bg"]) >= 4.5, "margin_px": M}
                    rendered += 1
                else:
                    skipped.append(f"{slug}: render failed")
            image_url = f"{site or '<site>'}/og/{fname}"
            live = None
            if site:  # live check: a site not live yet is a retry next run, not a failure
                try:
                    pr = k.requests.get(f"{site}/" if slug == "home" else f"{site}/{slug}", timeout=20)
                    if pr.ok:
                        im_r = k.requests.get(image_url, timeout=20)
                        live = bool(im_r.ok and "image/png" in im_r.headers.get("content-type", "") and 'property="og:title"' in pr.text.replace("'", '"'))
                        if not live:
                            skipped.append(f"{slug}: image or og tags not served yet")
                except Exception:  # noqa: BLE001
                    pass
            blocks.append(tag_block(slug, title, sub, image_url, site or "<site>", f"{name}: {title}"[:120]))
            rows.append({"page": slug, "image": f"launch/og/{fname}", "title": title, "description": sub, "checks": checks, "live_ok": live, **({} if IM else {"render": "pending: ImageMagick not found"})})
    k.write(ctx, "launch/og/tags.html", "\n\n".join(blocks))
    k.write(ctx, "launch/og/index.json", rows)
    k.write(ctx, "launch/image-requests.json", reqs)
    return {"summary": f"{len(rows)} pages: {rendered} share images rendered, tags written." + ("" if IM else " Render pending: ImageMagick not found.") + ("" if site else " No site in channels.json, so tags use a <site> placeholder.") + (f" Notes: {len(skipped)}." if skipped else ""), "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
