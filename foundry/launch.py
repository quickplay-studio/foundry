"""Launch: turn ventures/<slug>/idea.json into a brain, a plan and a board.

    python -m foundry.launch --slug <slug>            # run for one venture
    python -m foundry.launch --all                    # every venture without a board
    python -m foundry.launch --slug sample --dry-run  # print, write nothing

idea.json is what Lodestone sends: title, category, problem, who, gap, mvp,
money, proof, scores, plus budget_gbp and deployed (ISO date) if given.
"""
import argparse
import json
import sys

from . import audit, util

GATES = {
    "validate": "Intelligence report says go, Charlie confirms",
    "clear": "Name clear, regulatory screen clear, Charlie confirms",
    "build": "MVP passes QA on real data",
    "launch": "Charlie approves the ad brief and budget, pays the platform",
    "sell": "First reply handled end to end",
    "support": "First support ticket answered",
    "run": "Budget and revenue tracked weekly",
}


def brain_md(idea, slug):
    mvp = idea.get("mvp") or []
    proof = idea.get("proof") or []
    lines = [
        f"# {idea.get('title', slug)}", "",
        f"Slug: `{slug}`. Category: {idea.get('category', 'unknown')}. Source: Lodestone, deployed {idea.get('deployed') or util.today()}.", "",
        "## Problem", idea.get("problem", ""), "",
        "## Who", idea.get("who", ""), "",
        "## Gap", idea.get("gap", ""), "",
        "## MVP", *[f"- {m}" for m in mvp], "",
        "## Money", idea.get("money", ""), "",
        "## Proof", *[f"- {p.get('source', '')}: {p.get('url', '')}" if isinstance(p, dict) else f"- {p}" for p in proof], "",
        "## Scores", json.dumps(idea.get("scores", {})), "",
        "## Constraints", "- Free tools until the first pound of revenue; ad spend only with an approved brief.",
        "- UK market first. UK English. No dashes.", "- Everything an agent writes about this venture goes through this file first.", "",
        "## Decisions", "- ", "",
    ]
    return "\n".join(lines)


def plan_md(idea, result, slug):
    lines = [f"# Launch plan: {idea.get('title', slug)}", "",
             f"Audited {result['audited']} by {result['model_used']}. Business model: {result['business_model']}.", "",
             result["reasoning"], "",
             "## Day one", *[f"- `{i}`" for i in result["first_three"]], ""]
    current = None
    for job in result["jobs"]:
        if job["stage"] != current:
            current = job["stage"]
            lines += [f"## {current.title()}", f"Gate: {GATES.get(current, '')}", ""]
        lines.append(f"- [ ] `{job['id']}` ({job['department']}, {job['autonomy']}) {job['why']}".rstrip())
    lines += ["", f"Dropped {len(result['dropped'])} jobs that do not apply."]
    return "\n".join(lines) + "\n"


def board(result, slug, idea=None):
    return {
        "slug": slug, "title": (idea or {}).get("title", slug), "deployed": (idea or {}).get("deployed", util.today()), "updated": util.now(), "stage": result["jobs"][0]["stage"] if result["jobs"] else "validate",
        "verdict": "pending", "weekly": [], "incidents": [], "skipped": [],
        "business_model": result["business_model"], "model_used": result["model_used"],
        "jobs": [{"id": j["id"], "stage": j["stage"], "department": j["department"], "autonomy": j["autonomy"],
                  "status": "todo", "output": "", "updated": ""} for j in result["jobs"]],
        "gates": {s: "open" for s in audit.STAGE_ORDER},
    }


def budget(idea):
    return {"currency": "GBP", "ad_budget": idea.get("budget_gbp", 0), "spent": 0, "revenue": 0,
            "lines": [], "updated": util.now()}


def run_one(slug, dry_run=False, root=None):
    root = root or util.VENTURES
    folder = root / slug
    idea = util.read_json(folder / "idea.json")
    if not idea:
        raise SystemExit(f"no idea.json in {folder}")
    skipped = []
    result = audit.run(idea, skipped=skipped)
    outputs = {
        "brain.md": brain_md(idea, slug), "plan.md": plan_md(idea, result, slug),
        "board.json": board(result, slug, idea), "budget.json": budget(idea),
        "audit.json": {**result, "skipped": skipped},
    }
    if dry_run:
        print(outputs["plan.md"])
        print(f"dry run: {len(result['jobs'])} jobs kept, {len(result['dropped'])} dropped, model {result['model_used']}")
        return outputs
    for name, content in outputs.items():
        path = folder / name
        if name.endswith(".json"):
            util.write_json(path, content)
        else:
            path.write_text(content, encoding="utf-8")
    print(f"launched {slug}: {len(result['jobs'])} jobs, model {result['model_used']}")
    return outputs


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--slug")
    p.add_argument("--all", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    if a.all:
        if not util.VENTURES.exists():
            print("no data/ventures checkout; nothing to launch")
            return
        for folder in sorted(util.VENTURES.glob("*/idea.json")):
            if not (folder.parent / "board.json").exists():
                run_one(folder.parent.name, a.dry_run)
        return
    if not a.slug:
        p.error("--slug or --all")
    run_one(a.slug, a.dry_run)


if __name__ == "__main__":
    main(sys.argv[1:])
