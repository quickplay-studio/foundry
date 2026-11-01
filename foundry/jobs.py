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
import datetime as dt
import os
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


HALT_VERDICTS = ("blocked", "park", "kill")


def deps_done(board, job):
    """Every builds_on job that is on this board has produced its output (done or review)."""
    status = {j["id"]: j["status"] for j in board["jobs"]}
    meta = {j["id"]: j for j in util.all_jobs()}.get(job["id"], {})
    # a dependency that gave up (skipped) no longer blocks: every script copes with a missing input
    return all(status.get(dep, "absent") in ("done", "review", "skipped", "absent") for dep in meta.get("builds_on", []))


def can_run(board, job):
    order = audit.STAGE_ORDER
    stage = job["stage"]
    if stage not in order or board.get("verdict") in HALT_VERDICTS:
        return False
    for earlier in order[: order.index(stage)]:
        has_jobs = any(j["stage"] == earlier for j in board["jobs"])
        if has_jobs and board["gates"].get(earlier) != "passed":
            return False
    return deps_done(board, job)


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
    script = path.parent / "run.py"
    if script.exists():
        return run_script(script, folder, job, dry_run)
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


def run_script(script, folder, job, dry_run=False):
    """A job's own run.py: the GitHub implementation of the skill (see foundry.jobkit)."""
    import subprocess
    args = [sys.executable, "-P", str(script), "--slug", folder.name, "--folder", str(folder)] + (["--dry-run"] if dry_run else [])
    env = dict(os.environ, PYTHONPATH=str(util.ROOT))
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=1500, env=env, cwd=str(util.ROOT))
    except subprocess.TimeoutExpired:
        return {"skipped": "run.py timed out after 25 minutes"}
    last = [line for line in proc.stdout.strip().splitlines() if line.startswith("{")]
    if proc.returncode != 0 or not last:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-3:]
        return {"skipped": ("run.py failed: " + " | ".join(tail))[:200]}
    try:
        result = json.loads(last[-1])
    except json.JSONDecodeError:
        return {"skipped": "run.py printed no result line"}
    if dry_run:
        print(f"would run {job['id']} for {folder.name} via run.py: {result.get('outputs')}")
        return {"dry_run": True}
    if result.get("skipped") and not result.get("outputs"):
        return {"skipped": str(result["skipped"])[:200]}
    outputs = [str(o) for o in result.get("outputs", [])][:12]
    return {"output": outputs[0] if outputs else f"{job['stage']}/{job['id']}.md", "outputs": outputs,
            "summary": str(result.get("summary", ""))[:300], "flag": str(result.get("flag", "ok"))[:10], "model": "run.py"}


RECURRING_DAYS = {"run": 7, "support": 3}  # done jobs in these stages run again after this many days


def due_again(job):
    days = RECURRING_DAYS.get(job.get("stage"))
    if not days or job["status"] != "done" or not job.get("updated"):
        return False
    try:
        last = dt.datetime.strptime(job["updated"][:10], "%Y-%m-%d").date()
    except ValueError:
        return False
    return (dt.date.today() - last).days >= days


MAX_ATTEMPTS = 3  # a job that skips on three different days is marked skipped so its dependants can move on


def note_skipped(board, job_id, reason):
    """One skipped line per job (with an attempt count across days), forty kept. Returns the attempt count."""
    old = next((s for s in board.get("skipped", []) if s.get("job") == job_id), {})
    attempts = int(old.get("attempts", 0)) + (0 if old.get("date") == util.today() else 1)
    board["skipped"] = [s for s in board.get("skipped", []) if s.get("job") != job_id][-39:]
    board["skipped"].append({"job": job_id, "reason": reason, "date": util.today(), "attempts": max(attempts, 1)})
    return max(attempts, 1)


def run_venture(slug, limit, dry_run=False, only=None):
    folder = util.VENTURES / slug
    board = util.read_json(folder / "board.json")
    if not board:
        return 0
    done = 0
    for job_id in [j["id"] for j in board["jobs"]]:
        if done >= limit:
            break
        if only and job_id != only:
            continue
        job = next(j for j in board["jobs"] if j["id"] == job_id)
        on_demand = bool(only) and job_id == only  # --job runs a named job whatever its stage or gate, once
        if not (job["status"] == "todo" or due_again(job) or on_demand) or not (on_demand or can_run(board, job)):
            continue
        result = run_job(folder, board, job, dry_run)
        if result.get("dry_run"):
            done += 1
            continue
        # a run.py may have written board.json itself (incidents, weekly lines, verdict): re-read before touching it
        fresh = util.read_json(folder / "board.json") or board
        board = fresh
        job = next(j for j in board["jobs"] if j["id"] == job_id)
        job["updated"] = util.now()
        if "skipped" in result:
            reason = result["skipped"]
            print(f"  {job_id}: skipped, {reason}", flush=True)
            attempts = note_skipped(board, job_id, reason)
            if attempts >= MAX_ATTEMPTS and not reason.startswith("no free model") and "Claude Code" not in reason and "stub" not in reason:
                job["status"] = "skipped"  # give up for now; Charlie can set it back to todo
            if reason.startswith("no free model"):
                board["updated"] = util.now()
                if not dry_run:
                    util.write_json(folder / "board.json", board)
                break  # nothing else will answer today either; try again tomorrow
            if reason == "skill file missing":
                job["status"] = "skipped"
        else:
            job["status"] = "done" if job["autonomy"] == "solo" else "review"
            print(f"  {job_id}: {job['status']}, flag {result['flag']}, {result['summary'][:120]}", flush=True)
            job["output"] = result["output"]
            job["outputs"] = result["outputs"]
            board.setdefault("log", []).append({"date": util.today(), "job": job_id, "status": job["status"], "flag": result["flag"], "summary": result["summary"], "model": result["model"]})
            if result["flag"] == "stop":
                board["gates"][job["stage"]] = "failed"
                board["verdict"] = "blocked"  # Charlie decides: override in writing, or kill
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
