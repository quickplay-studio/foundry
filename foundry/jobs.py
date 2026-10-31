"""Run jobs marked runs_on: github for every venture, in plan order, on the free models.

    python -m foundry.jobs --all                 # up to config max_jobs_per_run across ventures
    python -m foundry.jobs --slug sample --job vertical-analysis
    python -m foundry.jobs --slug sample --dry-run

A job can run when its stage is the venture's current stage or the gates of every
earlier stage with jobs are "passed" (Charlie sets gates in board.json). The model
reads the skill, the company brain, the venture brain and the venture files the skill
names, and returns one output file. Solo jobs are marked done; assisted and human
jobs are marked review, so Charlie sees the draft before it is used.
"""
import argparse
import json
import re
import sys

from . import audit, util

MAX_JOBS = 5
PROMPT = """You are one agent in a small company's AI workforce. Do the job below exactly as its skill file says, for the venture described, using only the material given. Write in UK English, no em or en dashes, no hype. If the job needs a service or data you do not have, do the part you can and say what is missing in the summary.

Return JSON only: {{"files": [{{"path": "<relative path under the venture folder, from the skill's Output section>", "content": "<the complete file: markdown, or JSON as a string>"}}], "summary": "<two sentences>", "flag": "<clear, caution or stop, when the skill asks for a flag, else ok>"}}
Write every file the Output section names (a .md and a .json pair both), in the shapes it gives.

COMPANY BRAIN
{company}

VENTURE BRAIN
{brain}

SKILL
{skill}

VENTURE FILES
{files}
"""


def skill_path(job):
    return util.DEPARTMENTS / job["department"] / job["function"] / job["id"] / "SKILL.md"


def runs_on(text):
    m = re.search(r"^runs_on:\s*(\S+)", text, re.M)
    return m.group(1) if m else "github"


def ready(text):
    return bool(re.search(r"^status:\s*ready", text, re.M))


def can_run(board, job):
    order = audit.STAGE_ORDER
    stage = job["stage"]
    if stage not in order:
        return False
    for earlier in order[: order.index(stage)]:
        has_jobs = any(j["stage"] == earlier for j in board["jobs"])
        if has_jobs and board["gates"].get(earlier) != "passed":
            return False
    return True


def venture_files(folder, skill_text, limit=6000):
    """Files under the venture that the skill names, plus the plan, trimmed."""
    names = set(re.findall(r"ventures/<slug>/([\w\-./]+)", skill_text))
    out = []
    for rel in sorted(names):
        path = folder / rel
        if path.is_file():
            out.append(f"--- {rel} ---\n" + path.read_text(encoding="utf-8")[:limit])
    listing = ", ".join(str(p.relative_to(folder)) for p in sorted(folder.rglob("*")) if p.is_file())
    return "\n".join(out) + f"\n--- files present ---\n{listing}"


def run_job(folder, board, job, dry_run=False):
    jobs = {j["id"]: j for j in util.all_jobs()}
    meta = jobs.get(job["id"])
    path = skill_path(meta) if meta else None
    if not path or not path.exists():
        return {"skipped": "skill file missing"}
    text = path.read_text(encoding="utf-8")
    if not ready(text):
        return {"skipped": "skill still a stub"}
    if runs_on(text) != "github":
        return {"skipped": "runs in Claude Code"}
    company = (util.ROOT / "brain" / "company.md").read_text(encoding="utf-8")[:6000]
    brain = (folder / "brain.md").read_text(encoding="utf-8")[:6000] if (folder / "brain.md").exists() else ""
    prompt = PROMPT.format(company=company, brain=brain, skill=text[:9000], files=venture_files(folder, text))
    if dry_run:
        print(f"would run {job['id']} for {folder.name} ({len(prompt)} chars of prompt)")
        return {"dry_run": True}
    skipped = []
    result, model = util.ask_json(prompt, skipped)
    files = []
    if result:
        if isinstance(result.get("files"), list):
            files = [f for f in result["files"] if isinstance(f, dict) and isinstance(f.get("content"), str) and f.get("path")]
        elif isinstance(result.get("content"), str) and result.get("path"):
            files = [{"path": result["path"], "content": result["content"]}]
    if not files:
        return {"skipped": "no free model answered: " + "; ".join(s["reason"] for s in skipped)[:200]}
    written = []
    for i, f in enumerate(files[:6]):
        rel = re.sub(r"^(\./|/)+", "", str(f["path"]).replace("ventures/<slug>/", ""))
        if ".." in rel or not rel:
            rel = f"{job['stage']}/{job['id']}{'' if i == 0 else i}.md"
        out = folder / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(f["content"].rstrip() + "\n", encoding="utf-8")
        written.append(rel)
    return {"output": written[0], "outputs": written, "summary": str(result.get("summary", ""))[:300], "flag": str(result.get("flag", "ok"))[:10], "model": model}


def run_venture(slug, limit, dry_run=False, only=None):
    folder = util.VENTURES / slug
    board = util.read_json(folder / "board.json")
    if not board:
        return 0
    done = 0
    for job in board["jobs"]:
        if done >= limit:
            break
        if only and job["id"] != only:
            continue
        if job["status"] != "todo" or not can_run(board, job):
            continue
        result = run_job(folder, board, job, dry_run)
        if result.get("dry_run"):
            done += 1
            continue
        job["updated"] = util.now()
        if "skipped" in result:
            reason = result["skipped"]
            board.setdefault("skipped", []).append({"job": job["id"], "reason": reason, "date": util.today()})
            board["skipped"] = board["skipped"][-40:]
            if reason.startswith("no free model"):
                break  # nothing else will answer today either; try again tomorrow
            if reason == "skill file missing":
                job["status"] = "skipped"
            continue  # stubs and Claude Code jobs stay todo
        else:
            job["status"] = "done" if job["autonomy"] == "solo" else "review"
            job["output"] = result["output"]
            job["outputs"] = result["outputs"]
            board.setdefault("log", []).append({"date": util.today(), "job": job["id"], "status": job["status"], "flag": result["flag"], "summary": result["summary"], "model": result["model"]})
            if result["flag"] == "stop":
                board["gates"][job["stage"]] = "failed"
                board["verdict"] = "kill"
        done += 1
    board["updated"] = util.now()
    board["stage"] = next((j["stage"] for j in board["jobs"] if j["status"] in ("todo", "review")), board["stage"])
    board["log"] = board.get("log", [])[-60:]
    if not dry_run:
        util.write_json(folder / "board.json", board)
    print(f"{slug}: {done} jobs run")
    return done


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--slug")
    p.add_argument("--job")
    p.add_argument("--all", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int, default=MAX_JOBS)
    a = p.parse_args(argv)
    slugs = [a.slug] if a.slug else [f.parent.name for f in sorted(util.VENTURES.glob("*/board.json"))] if a.all else []
    if not slugs:
        p.error("--slug or --all")
    total = 0
    for slug in slugs:
        total += run_venture(slug, a.limit - total, a.dry_run, a.job)
        if total >= a.limit:
            break


if __name__ == "__main__":
    main(sys.argv[1:])
