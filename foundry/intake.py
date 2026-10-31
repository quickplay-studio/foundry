"""Add a venture to the private data checkout without Lodestone.

    python -m foundry.intake --slug my-shop --kind tiktok-shop --title "My Shop" \
        --problem "..." --who "..." --gap "..." --money "..." --mvp "a" --mvp "b" --budget 100
    python -m foundry.intake --from idea.json        # a file in the template's shape

Writes data/ventures/<slug>/idea.json. The launch workflow does the rest.
"""
import argparse
import json
import sys

from . import util

KINDS = ("app", "channel", "shop", "tiktok-shop", "dropshipping", "service")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--from", dest="src")
    p.add_argument("--slug")
    p.add_argument("--kind", choices=KINDS)
    p.add_argument("--title")
    p.add_argument("--problem", default="")
    p.add_argument("--who", default="")
    p.add_argument("--gap", default="")
    p.add_argument("--money", default="")
    p.add_argument("--category", default="other")
    p.add_argument("--mvp", action="append", default=[])
    p.add_argument("--channel", action="append", default=[])
    p.add_argument("--budget", type=int, default=0)
    p.add_argument("--note", default="")
    a = p.parse_args(argv)
    if a.src:
        idea = json.load(open(a.src, encoding="utf-8"))
    else:
        if not (a.slug and a.kind and a.title):
            p.error("--slug, --kind and --title, or --from")
        idea = {"slug": a.slug, "title": a.title, "kind": a.kind, "category": a.category, "problem": a.problem,
                "who": a.who, "gap": a.gap, "mvp": a.mvp, "money": a.money, "channels": a.channel, "proof": [],
                "budget_gbp": a.budget, "note": a.note}
    slug = util.slugify(idea.get("slug") or idea["title"])
    idea["slug"] = slug
    idea.setdefault("deployed", util.today())
    if idea.get("kind") not in KINDS:
        p.error(f"kind must be one of {', '.join(KINDS)}")
    out = util.VENTURES / slug / "idea.json"
    if out.exists():
        raise SystemExit(f"{out} exists; edit it or pick another slug")
    util.write_json(out, idea)
    print(f"wrote {out}; the next launch run will audit it")


if __name__ == "__main__":
    main(sys.argv[1:])
