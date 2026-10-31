"""Image Generation: GitHub implementation of departments/marketing/creation/image-generation/SKILL.md.

For each request in launch/image-requests.json with no file yet: a reference screenshot, else a free stock photo
(Pexels or Unsplash with their keys), else a flat brand card. ImageMagick crops and brands it, and every credit is
logged. Without ImageMagick the job writes launch/images/brief.md and says the render is pending. Gemini image
output is not used: its free-tier image access is unconfirmed.
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from foundry import jobkit as k

IM = shutil.which("convert") or shutil.which("magick")
BRAND = {"colours": {"bg": "#FFFFFF", "text": "#111111", "accent": "#0B5FFF"}, "font": "system-ui, sans-serif", "logo": ""}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
REF = (".png", ".jpg", ".jpeg", ".webp")


def tidy(text):
    return re.sub(r"\s+", " ", re.sub(r"\s*[\u2013\u2014]\s*", ", ", re.sub(r"!+", ".", str(text)).replace(" - ", ", "))).strip()


def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def font_path(family):
    fam = re.split(r",", str(family))[0].strip(" '\"")
    if not shutil.which("fc-match") or not fam or fam in ("system-ui", "sans-serif"):
        return None
    try:
        out = subprocess.run(["fc-match", "-f", "%{file}", fam], capture_output=True, text=True, timeout=10).stdout.strip()
        return out or None
    except Exception:  # noqa: BLE001
        return None


def im(args):
    try:
        return subprocess.run([IM, *args], capture_output=True, timeout=90).returncode == 0
    except Exception:  # noqa: BLE001
        return False


def render(base, out, w, h, text, brand, quality=85, folder=Path(".")):
    c = brand["colours"]
    fg = c["text"] if contrast(c["text"], c["bg"]) >= 4.5 else ("#000000" if contrast("#000000", c["bg"]) > contrast("#FFFFFF", c["bg"]) else "#FFFFFF")
    font = font_path(brand.get("font"))
    args = ([base, "-resize", f"{w}x{h}^", "-gravity", "center", "-extent", f"{w}x{h}", "-fill", c["bg"], "-colorize", "65%"] if base else ["-size", f"{w}x{h}", f"xc:{c['bg']}"])
    if text:  # a background request has no text
        args += ["(", "-size", f"{int(w * 0.8)}x{int(h * 0.5)}", "-background", "none", "-fill", fg] + (["-font", font] if font else []) + ["-gravity", "center", f"caption:{text}", ")", "-gravity", "center", "-composite"]
    logo = Path(str(brand.get("logo") or "x"))
    logo = logo if logo.is_absolute() else folder / logo
    if brand.get("logo") and logo.is_file():
        args += ["(", str(logo), "-resize", f"{int(w * 0.14)}x", ")", "-gravity", "northeast", "-geometry", "+40+40", "-composite"]
    args += ["-depth", "8", "-quality", str(quality), out]
    return im(args), fg


def stock(keywords, w, h):
    """(bytes, credit) from Pexels or Unsplash, or (None, None)."""
    q, orient = " ".join(keywords)[:80], "portrait" if h > w else "landscape"
    try:
        if k.secret("PEXELS_API_KEY"):
            d = k.requests.get("https://api.pexels.com/v1/search", params={"query": q, "per_page": 3, "orientation": orient}, headers={"Authorization": k.secret("PEXELS_API_KEY")}, timeout=20).json()
            p = d["photos"][0]
            return k.requests.get(p["src"]["large"], timeout=40).content, {"source": "Pexels", "author": p.get("photographer", ""), "url": p.get("url", ""), "licence": "Pexels licence"}
        if k.secret("UNSPLASH_ACCESS_KEY"):
            key = k.secret("UNSPLASH_ACCESS_KEY")
            p = k.requests.get("https://api.unsplash.com/search/photos", params={"query": q, "per_page": 3, "orientation": orient, "client_id": key}, timeout=20).json()["results"][0]
            k.requests.get(p["links"]["download_location"], params={"client_id": key}, timeout=20)  # Unsplash expects the download ping
            return k.requests.get(p["urls"]["regular"], timeout=40).content, {"source": "Unsplash", "author": p["user"].get("name", ""), "url": p["links"].get("html", ""), "licence": "Unsplash licence"}
    except Exception:  # noqa: BLE001
        pass
    return None, None


def main(ctx):
    reqs = k.read(ctx, "launch/image-requests.json")
    reqs = [r for r in reqs if isinstance(r, dict) and r.get("id")] if isinstance(reqs, list) else []
    folder = ctx["folder"]
    todo = [r for r in reqs if not any((folder / "launch/images" / f"{r['id']}{e}").exists() for e in (".jpg", ".png"))]
    if not todo:
        return {"skipped": "no image requests without a file" if reqs else "launch/image-requests.json missing or empty"}
    brand = k.read(ctx, "launch/brand.json")
    made_brand = not (isinstance(brand, dict) and isinstance(brand.get("colours"), dict))
    brand = dict(BRAND) if made_brand else brand
    brand["colours"] = {key: (brand["colours"].get(key) if HEX.match(str(brand["colours"].get(key, ""))) else BRAND["colours"][key]) for key in BRAND["colours"]}
    if made_brand:
        k.write(ctx, "launch/brand.json", brand)
    if not IM:
        lines = ["# Image brief (render pending: ImageMagick not found on this runner)", ""] + [f"- {r['id']}: {r.get('purpose', '')}, {r.get('size', '1080x1350')}, text \"{tidy(r.get('text', ''))}\", keywords {r.get('keywords', [])}" for r in todo]
        k.write(ctx, "launch/images/brief.md", "\n".join(lines))
        return {"summary": f"ImageMagick missing: wrote launch/images/brief.md for {len(todo)} images, render pending.", "flag": "caution"}
    credits, done, failed = [r for r in (k.read(ctx, "launch/images/credits.json", []) or []) if isinstance(r, dict)], 0, []
    refs = sorted(p for p in (folder / "launch/references").glob("*") if p.suffix.lower() in REF) if (folder / "launch/references").is_dir() else []
    with tempfile.TemporaryDirectory() as tmp:
        for r in todo:
            m = re.match(r"^(\d{2,4})x(\d{2,4})$", str(r.get("size", "1080x1350")))
            w, h = (int(m.group(1)), int(m.group(2))) if m else (1080, 1350)
            text, kw = tidy(r.get("text", "")), [str(x) for x in r.get("keywords", [])] if isinstance(r.get("keywords"), list) else []
            heavy = len(text.split()) > 6 or "text" in str(r.get("purpose", "")).lower()
            ref = next((p for p in refs if any(x.lower() in p.stem.lower() for x in kw)), refs[0] if refs else None)
            base, credit = (str(ref), {"source": "reference library", "author": "Charlie", "url": "", "licence": "owned"}) if ref else (None, None)
            if not base and kw:
                data, credit = stock(kw, w, h)
                if data:
                    base = str(Path(tmp) / f"{r['id']}.src")
                    Path(base).write_bytes(data)
            credit = credit or {"source": "flat brand card", "author": "", "url": "", "licence": "none needed"}
            out = folder / "launch/images" / f"{r['id']}{'.png' if heavy else '.jpg'}"
            if ctx["dry_run"]:
                ctx["outputs"].append(str(out.relative_to(folder)))
                done += 1
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            ok = False
            for q in (85, 70, 55):
                ok, _ = render(base, str(out), w, h, text or ("" if "background" in str(r.get("purpose", "")).lower() else tidy(ctx["idea"].get("title", ""))), brand, q, folder)
                if not ok or out.stat().st_size <= 500 * 1024 or heavy:
                    break
            if ok and out.exists():
                ctx["outputs"].append(str(out.relative_to(folder)))
                credits.append({"id": r["id"], **credit, "generated": False, "prompt": ""})
                done += 1
            else:
                failed.append(r["id"])
    if done and not ctx["dry_run"]:
        k.write(ctx, "launch/images/credits.json", credits)
    if not done:
        return {"skipped": "ImageMagick failed on every request: " + ", ".join(failed)[:120]}
    return {"summary": f"{done} images written with credits, {len(failed)} failed." + (" Default brand.json created for Charlie to edit." if made_brand else ""), "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
