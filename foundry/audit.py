"""Audit engine: mark the tree for one venture and order the jobs.

Given a venture's idea.json, decide which jobs apply, in which stage order,
and why. A free model picks and explains; without one, the heuristic keeps
every staged job and drops the sell stage for consumer products.
"""
import json

from . import util

STAGE_ORDER = ["validate", "clear", "build", "launch", "sell", "support", "run"]

COMMERCE_KINDS = ("shop", "tiktok-shop", "dropshipping")

PROMPT = """You are the audit engine of an AI workforce. A new venture is below (its kind is one of app, channel, shop, tiktok-shop, dropshipping, service), and after it the list of agent jobs the workforce can run, one per line as id | department | stage | summary.

Return JSON only, with real content in every field: {{"model": "b2b" or "b2c" or "both", "reasoning": "two sentences on who pays and what matters first", "drop": [{{"id": "a job id from the list", "why": "ten words max"}}], "first_three": ["job id", "job id", "job id"]}}

Every job not in drop is kept. Drop a job when it only makes sense for an agency, a team or a different business model, or does no real work for this specific venture in the next ninety days. Drop the whole sell stage unless the venture has a business buyer. Jobs with stage none and commerce jobs for a venture that is not a shop are handled in code, so leave them out of drop. For a channel, the build stage is the content pipeline and the launch stage is distribution. first_three is what to run on day one.

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
    kind = str(idea.get("kind", "app")).lower()
    keep, drop = [], []
    for j in jobs:
        if not j.get("stage"):
            drop.append(j["id"])
        elif j["stage"] == "sell" and not b2b:
            drop.append(j["id"])
        elif j["department"] == "commerce" and kind not in COMMERCE_KINDS:
            drop.append(j["id"])
        else:
            keep.append({"id": j["id"], "why": ""})
    first = [k["id"] for k in keep if k["id"] in ("regulatory-screen", "vertical-analysis", "competitor-teardown")][:3]
    return {"model": "b2b" if b2b else "b2c", "reasoning": "Heuristic: no free model answered. Every staged job kept; sell stage only for business buyers.",
            "keep": keep, "drop": drop, "first_three": first}


def run(idea, tree=None, skipped=None):
    tree = tree or util.load_tree()
    jobs = util.all_jobs(tree)
    lines = "\n".join(f"{j['id']} | {j['department']} | {j.get('stage') or 'none'} | {j['summary']}" for j in jobs)
    idea_text = json.dumps({k: idea.get(k) for k in ("title", "kind", "problem", "who", "gap", "mvp", "money", "category", "channels", "note")}, ensure_ascii=False)
    result, model = util.ask_json(PROMPT.format(idea=idea_text, jobs=lines), skipped)
    valid = {j["id"] for j in jobs}
    if not result or not isinstance(result.get("drop"), list) or result.get("model") not in ("b2b", "b2c", "both"):
        if result and skipped is not None:
            skipped.append({"model": model, "reason": "answer not in the audit shape (drop list and model missing)"})
        result, model = heuristic(idea, jobs), "heuristic"
    kind = str(idea.get("kind", "app")).lower()
    b2b = result.get("model") in ("b2b", "both")
    drop_why = {str(d.get("id") if isinstance(d, dict) else d): str(d.get("why", "") if isinstance(d, dict) else "")[:80] for d in result["drop"]}
    # the model decides the venture-specific drops; the structural rules stay in code whatever it said
    keep = [j for j in jobs if j["id"] not in drop_why and j.get("stage")
            and not (j["stage"] == "sell" and not b2b) and not (j["department"] == "commerce" and kind not in COMMERCE_KINDS)]
    keep_ids = {j["id"] for j in keep}
    plan = [{"id": j["id"], "title": j["title"], "department": j["department"], "stage": j["stage"], "autonomy": j["autonomy"], "why": ""}
            for j in topo_order(keep)]
    return {
        "audited": util.now(), "model_used": model,
        "business_model": "b2b" if result.get("model") == "both" else result.get("model", "unknown"),
        "buyers": result.get("model", "unknown"), "reasoning": str(result.get("reasoning", ""))[:400],
        "first_three": [i for i in result.get("first_three", []) if i in keep_ids][:3],
        "jobs": plan, "dropped": sorted(valid - keep_ids),
        "dropped_why": {i: w for i, w in drop_why.items() if i in valid and w},
    }
