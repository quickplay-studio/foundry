"""Build docs/map.html: the map template with the index and each skill's status inlined.

    python -m foundry.mapbuild
"""
import json

from . import scaffold, util

TEMPLATE = util.ROOT / "docs" / "map.template.html"
OUT = util.ROOT / "docs" / "map.html"


def main():
    tree = util.load_tree()
    for dept in tree["departments"]:
        for fn in dept["functions"]:
            for job in fn["jobs"]:
                path = util.DEPARTMENTS / dept["id"] / fn["id"] / job["id"] / "SKILL.md"
                job["status"] = scaffold.status_of(path) if path.exists() else "missing"
    data = json.dumps(tree, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", data)
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT.relative_to(util.ROOT)} ({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
