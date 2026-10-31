"""Audit engine: mark the tree for one venture and order the jobs.

Given a venture's idea.json, decide which jobs apply, in which stage order,
and why. A free model picks and explains; without one, the heuristic keeps
every staged job and drops the sell stage for consumer products.
"""
import json

from . import util

STAGE_ORDER = ["validate", "clear", "build", "launch", "sell", "support", "run"]

PROMPT = """You are the audit engine of an AI workforce. A new product idea is below, and after it the list of agent jobs the workforce can run, one per line as id | department | stage | summary.

Return JSON only: {{"model": "b2b" or "b2c" or "both", "reasoning": "<two sentences>", "keep": [{{"id": "<job id>", "why": "<ten words max>"}}], "drop": ["<job id>", ...], "first_three": ["<job id>", "<job id>", "<job id>"]}}

Keep a job if it does real work for this specific idea in the next ninety days. Drop jobs that only make sense for an agency, a team or a different business model. Drop the whole sell stage for a consumer app unless it has a business buyer. first_three is what to run on day one.

IDEA
{idea}

JOBS
{jobs}
"""


def topo_order(jobs):
    """Stage order first, then builds_on inside a stage, then title."""
    by_id = {j["id"]: j for j in jobs}
    done, out = set(), []

    def rank(j):
        return STAGE_ORDER.index(j["stage"]) if j.get("stage") in STAGE_ORDER else 99

    pending = sorted(jobs, key=lambda j: (rank(j), j["title"]))
    while pending:
        for j in pending:  # lowest stage whose dependencies are done goes next
            deps = [d for d in j.get("builds_on", []) if d in by_id]
            if all(d in done for d in deps):
                break
        else:
            j = pending[0]  # a cycle: take the lowest stage and carry on
        out.append(j)
        done.add(j["id"])
        pending.remove(j)
    return out


def heuristic(idea, jobs):
    text = json.dumps(idea).lower()
    b2b = any(w in text for w in ["business", "agency", "agencies", "team", "b2b", "saas", "client", "firm", "company", "companies", "enterprise", "freelancer", "founder", "startup", "developer", "indie", "professional"])
    keep, drop = [], []
    for j in jobs:
        if not j.get("stage"):
            drop.append(j["id"])
        elif j["stage"] == "sell" and not b2b:
            drop.append(j["id"])
        else:
            keep.append({"id": j["id"], "why": "staged job, heuristic"})
    first = [k["id"] for k in keep if k["id"] in ("regulatory-screen", "vertical-analysis", "competitor-teardown")][:3]
    return {"model": "b2b" if b2b else "b2c", "reasoning": "Heuristic: no free model answered. Every staged job kept; sell stage only for business buyers.",
            "keep": keep, "drop": drop, "first_three": first}


def run(idea, tree=None, skipped=None):
    tree = tree or util.load_tree()
    jobs = util.all_jobs(tree)
    lines = "\n".join(f"{j['id']} | {j['department']} | {j.get('stage') or 'none'} | {j['summary']}" for j in jobs)
    idea_text = json.dumps({k: idea.get(k) for k in ("title", "problem", "who", "gap", "mvp", "money", "category")}, ensure_ascii=False)
    result, model = util.ask_json(PROMPT.format(idea=idea_text, jobs=lines), skipped)
    valid = {j["id"] for j in jobs}
    if not result or not isinstance(result.get("keep"), list):
        result, model = heuristic(idea, jobs), "heuristic"
    keep = [k for k in result["keep"] if isinstance(k, dict) and k.get("id") in valid]
    keep_ids = {k["id"] for k in keep}
    why = {k["id"]: str(k.get("why", ""))[:80] for k in keep}
    ordered = topo_order([j for j in jobs if j["id"] in keep_ids])
    plan = [{"id": j["id"], "title": j["title"], "department": j["department"], "stage": j["stage"],
             "autonomy": j["autonomy"], "why": why.get(j["id"], "")} for j in ordered]
    return {
        "audited": util.now(), "model_used": model,
        "business_model": result.get("model", "unknown"), "reasoning": str(result.get("reasoning", ""))[:400],
        "first_three": [i for i in result.get("first_three", []) if i in keep_ids][:3],
        "jobs": plan, "dropped": sorted(valid - keep_ids),
    }
