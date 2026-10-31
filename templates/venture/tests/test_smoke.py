import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASH = re.compile("[" + chr(0x2013) + chr(0x2014) + "]")


def test_app_page_exists_and_has_a_title():
    page = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
    assert re.search(r"<title>.+</title>", page)


def test_no_dashes_in_text_files():
    files = [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts and p.suffix in (".md", ".py", ".json", ".yml", ".html")]
    bad = [str(p) for p in files if DASH.search(p.read_text(encoding="utf-8", errors="ignore"))]
    assert not bad, bad
