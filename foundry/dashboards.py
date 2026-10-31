"""Build data/radar-data.json (in the private foundry-ventures checkout): one document per venture for the Foundry Radar page.

The Radar page (a pinned Claude page with a database) shows the six command
centres. Nothing on GitHub can write to that database, so the daily console
sync copies these documents across. Run after every launch and every weekly run:

    python -m foundry.dashboards
"""
import json

from . import audit, util

OUT = util.DATA / "radar-data.json"


def summarise(folder):
    board = util.read_json(folder / "board.json", {})
    budget = util.read_json(folder / "budget.json", {})
    idea = util.read_json(folder / "idea.json", {})
    jobs = board.get("jobs", [])
    by_stage = {}
    for j in jobs:
        s = by_stage.setdefault(j.get("stage") or "none", {"total": 0, "done": 0})
        s["total"] += 1
        s["done"] += 1 if j.get("status") == "done" else 0
    weekly = board.get("weekly", [])[-8:]
    last = weekly[-1] if weekly else {}
    return {
        "slug": folder.name,
        "title": board.get("title") or idea.get("title") or folder.name,
        "category": idea.get("category", ""),
        "kind": idea.get("kind", "app"),
        "sample": bool(idea.get("note", "").startswith("Sample venture")),
        "deployed": board.get("deployed") or idea.get("deployed", ""),
        "updated": board.get("updated", ""),
        "stage": board.get("stage", "validate"),
        "verdict": board.get("verdict", "pending"),
        "business_model": board.get("business_model", ""),
        "gates": board.get("gates", {}),
        "stages": {s: by_stage.get(s, {"total": 0, "done": 0}) for s in audit.STAGE_ORDER},
        "jobs_total": len(jobs),
        "jobs_done": sum(1 for j in jobs if j.get("status") == "done"),
        "incidents": len(board.get("incidents", [])),
        "skipped": len(board.get("skipped", [])),
        "budget": {"ad_budget": budget.get("ad_budget", 0), "spent": budget.get("spent", 0), "revenue": budget.get("revenue", 0)},
        "weekly": weekly,
        "sign_ups": last.get("sign_ups", 0),
        "cost_per_sign_up": last.get("cost_per_sign_up"),
    }


def main():
    docs = [summarise(f) for f in sorted(util.VENTURES.glob("*/")) if (f / "idea.json").exists()]
    data = {"generated": util.now(), "ventures": docs}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT}: {len(docs)} ventures")
    return data


if __name__ == "__main__":
    main()
