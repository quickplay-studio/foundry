"""Helpers for a job's run.py: the GitHub implementation of a skill.

A skill folder may hold a `run.py` beside its SKILL.md. `foundry.jobs` runs it as
`python -P run.py --slug <slug> --folder <venture folder>` (PYTHONPATH is the repo root) with the venture folder
on disk and the secrets in the environment, and expects one JSON line on stdout at
the end: {"outputs": [...paths relative to the venture folder...], "summary": "...",
"flag": "ok|clear|caution|stop", "skipped": "<reason>" when nothing could be done}.
Without a run.py the job runs in model-only mode (the skill text plus the brains).

    from foundry import jobkit as k

    def main(ctx):
        rows = k.search("uk meal planning app complaints", 5)
        page = k.fetch("https://example.com")
        answer = k.ask("Return JSON ...")   # the free model chain, parsed JSON or None
        k.write(ctx, "validate/vertical-analysis.md", text)
        return {"summary": "...", "flag": "clear"}   # or {"skipped": "why"}

    if __name__ == "__main__":
        k.run(main)

main(ctx) is also what the tests call, with k.ask, k.search and k.fetch replaced by fakes
(tests/test_runs.py): every run.py must finish offline without raising and write the files
its SKILL.md names.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests

from . import util

FIRECRAWL = "https://api.firecrawl.dev/v1"


def start(description=""):
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--slug", required=True)
    p.add_argument("--folder", required=True)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    folder = Path(a.folder)
    ctx = {"slug": a.slug, "folder": folder, "dry_run": a.dry_run, "outputs": [],
           "idea": util.read_json(folder / "idea.json", {}), "board": util.read_json(folder / "board.json", {}),
           "budget": util.read_json(folder / "budget.json", {}),
           "brain": (folder / "brain.md").read_text(encoding="utf-8") if (folder / "brain.md").exists() else "",
           "company": (util.ROOT / "brain" / "company.md").read_text(encoding="utf-8")}
    return ctx


def kind(ctx):
    return str(ctx["idea"].get("kind", "app")).lower()


def read(ctx, rel, default=None):
    path = ctx["folder"] / rel
    if not path.exists():
        if os.environ.get("FOUNDRY_FAKE_MODEL"):  # local lifecycle runs: record what was wanted and missing
            try:
                with open(util.DATA / "office" / "read-misses.log", "a", encoding="utf-8") as f:
                    f.write(f"{ctx['slug']}\t{sys.argv[0].split('/departments/')[-1].replace('/run.py', '')}\t{rel}\n")
            except OSError:
                pass
        return default
    if rel.endswith(".json"):
        return util.read_json(path, default)
    return path.read_text(encoding="utf-8")


def write(ctx, rel, content):
    """Write a file under the venture folder (JSON for dicts and lists), unless dry run."""
    if isinstance(content, (dict, list)):
        content = json.dumps(content, indent=2, ensure_ascii=False) + "\n"
    elif not content.endswith("\n"):
        content += "\n"
    ctx["outputs"].append(rel)
    if ctx["dry_run"]:
        print(f"dry run: would write {rel} ({len(content)} chars)", file=sys.stderr)
        return
    path = ctx["folder"] / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def ask(prompt, prefer=None):
    """One JSON answer from the free model chain, or None."""
    result, _ = util.ask_json(prompt, prefer=prefer)
    return result


def search(query, n=5, topic="general"):
    """Web search: the router, then Firecrawl when a key exists, then the keyless engines (DuckDuckGo, Hacker News); [] when all fail."""
    rows = util.search(query, n, topic)
    if rows:
        return rows
    key = os.environ.get("FIRECRAWL_API_KEY", "").strip()
    if key:
        try:
            r = requests.post(f"{FIRECRAWL}/search", json={"query": query, "limit": n},
                              headers={"Authorization": f"Bearer {key}"}, timeout=40)
            data = r.json().get("data", []) if r.ok else []
            rows = [{"title": d.get("title", ""), "url": d.get("url", ""), "content": str(d.get("description", "") or d.get("markdown", ""))[:1500]} for d in data][:n]
        except Exception:  # noqa: BLE001
            rows = []
    return rows or util.keyless_search(query, n)


def fetch(url, limit=12000):
    """Page text: Firecrawl scrape when a key exists, else a plain GET with tags stripped. '' on failure."""
    if os.environ.get("FOUNDRY_FAKE_MODEL"):
        return f"stub page text for {url}"[:limit]
    key = os.environ.get("FIRECRAWL_API_KEY", "").strip()
    try:
        if key:
            r = requests.post(f"{FIRECRAWL}/scrape", json={"url": url, "formats": ["markdown"]},
                              headers={"Authorization": f"Bearer {key}"}, timeout=60)
            if r.ok:
                return str(r.json().get("data", {}).get("markdown", ""))[:limit]
        r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0 (Foundry research bot)"})
        if not r.ok:
            return ""
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", r.text, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text)[:limit]
    except Exception:  # noqa: BLE001
        return ""


def secret(name):
    return os.environ.get(name, "").strip()


def md_html(text):
    """Small markdown to HTML: headings, bullet lists, pipe tables, paragraphs, bold."""
    import html
    out, buf = [], []

    def inline(s):
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html.escape(s))

    def flush():
        if not buf:
            return
        if buf[0][0] == "li":
            out.append("<ul>" + "".join(f"<li>{inline(b[1])}</li>" for b in buf) + "</ul>")
        elif buf[0][0] == "tr":
            rows = [b[1] for b in buf if not re.fullmatch(r"[\s|:-]+", b[1])]
            out.append("<table>" + "".join("<tr>" + "".join(f"<td>{inline(c.strip())}</td>" for c in r.strip("|").split("|")) + "</tr>" for r in rows) + "</table>")
        else:
            out.append("<p>" + inline(" ".join(b[1] for b in buf)) + "</p>")
        buf.clear()

    for line in text.splitlines():
        s = line.strip()
        h = re.match(r"(#{1,4}) +(.*)", s)
        kind = "h" if h else "li" if re.match(r"[-*] +", s) else "tr" if s.startswith("|") else "p" if s else None
        if buf and kind != buf[0][0]:
            flush()
        if kind == "h":
            out.append(f"<h{len(h.group(1))}>{inline(h.group(2))}</h{len(h.group(1))}>")
        elif kind:
            buf.append((kind, re.sub(r"^[-*] +", "", s) if kind == "li" else s))
    flush()
    return "\n".join(out)


PDF_CSS = ("body{font-family:Georgia,serif;max-width:720px;margin:2em auto;line-height:1.5;color:#222}h1,h2{font-family:Arial,sans-serif}"
           "table{border-collapse:collapse}td{border:1px solid #bbb;padding:4px 8px}h1{page-break-before:always}h1:first-of-type{page-break-before:avoid}")


def chrome():
    import shutil
    return shutil.which("google-chrome") or shutil.which("google-chrome-stable") or shutil.which("chromium") or shutil.which("chromium-browser")


def render_pdf(ctx, rel, markdown, css=None):
    """Render markdown to a PDF under the venture folder with the runner's headless Chrome (ubuntu-latest has it).
    Returns the relative path when the file was written, else None (no Chrome, dry run, offline test, or Chrome failed);
    the caller records the pending render and carries on, nothing else depends on the PDF."""
    import subprocess
    import tempfile
    exe = chrome()
    if not exe or ctx.get("dry_run") or os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("FOUNDRY_FAKE_MODEL"):
        return None
    out = ctx["folder"] / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "page.html"
        page.write_text(f"<!doctype html><meta charset=utf-8><style>{css or PDF_CSS}</style>{md_html(markdown)}", encoding="utf-8")
        try:
            subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={out}", page.as_uri()],
                           capture_output=True, timeout=90)
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"pdf render failed: {type(exc).__name__}", file=sys.stderr)
            return None
    if not out.exists() or out.stat().st_size == 0:
        return None
    if rel not in ctx["outputs"]:
        ctx["outputs"].append(rel)
    return rel


def known_competitors(idea, n=6):
    """Products the model already knows as direct alternatives for the idea: [{"name", "url", "why"}], verified only as far
    as having a plausible https url. Seeds competitor discovery when web search is thin; the scripts fetch the sites afterwards."""
    brief = json.dumps({k: idea.get(k) for k in ("title", "kind", "problem", "who", "gap", "mvp") if idea.get(k)}, ensure_ascii=False)[:1500]
    answer = ask('Return JSON only: {"competitors": [{"name": "the product name", "url": "https://its-homepage.example", "why": "one line on what it does"}]}. '
                 f'List up to {n} real, existing products that people with this problem use today as direct alternatives, best known first, each with its real homepage. '
                 'Leave the list empty rather than inventing one.\n\nIDEA\n' + brief)
    rows = answer.get("competitors") if isinstance(answer, dict) and isinstance(answer.get("competitors"), list) else []
    out, seen = [], set()
    for r in rows:
        if not isinstance(r, dict):
            continue
        name, url = str(r.get("name", "")).strip()[:60], str(r.get("url", "")).strip()
        if not re.match(r"^https?://[\w.-]+\.[a-z]{2,}", url, flags=re.I) or ".example" in url or not name or name.lower() in seen or name.lower() == "the product name":
            continue
        seen.add(name.lower())
        out.append({"name": name, "url": url.split("?")[0], "why": str(r.get("why", ""))[:120]})
    return out[:n]


def test_ctx(folder, idea=None, board=None):
    """A context for tests: a venture folder on disk with idea.json and brain.md."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    idea = idea or {"slug": folder.name, "title": "Test venture", "kind": "app", "problem": "p", "who": "w", "gap": "g",
                    "mvp": ["one"], "money": "m", "channels": ["web"], "budget_gbp": 50}
    util.write_json(folder / "idea.json", idea)
    (folder / "brain.md").write_text("# Test venture\n\n## Problem\np\n", encoding="utf-8")
    if board:
        util.write_json(folder / "board.json", board)
    return {"slug": folder.name, "folder": folder, "dry_run": False, "outputs": [], "idea": idea, "board": board or {},
            "budget": {"currency": "GBP", "ad_budget": idea.get("budget_gbp", 0), "spent": 0, "revenue": 0},
            "brain": (folder / "brain.md").read_text(encoding="utf-8"), "company": "# Company brain\n"}


def run(main):
    """Entry point for a run.py: build the context, call main(ctx), print the result line."""
    ctx = start()
    try:
        result = main(ctx) or {}
    except Exception as exc:  # noqa: BLE001
        print(f"run.py error: {type(exc).__name__}: {exc}", file=sys.stderr)
        finish(ctx, skipped=f"{type(exc).__name__}: {exc}")
    finish(ctx, summary=str(result.get("summary", "")), flag=str(result.get("flag", "ok")), skipped=result.get("skipped"))


def finish(ctx, summary="", flag="ok", skipped=None):
    """Print the result line foundry.jobs reads, and exit 0."""
    out = {"outputs": ctx["outputs"], "summary": summary[:300], "flag": flag}
    if skipped:
        out["skipped"] = skipped[:200]
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(0)
