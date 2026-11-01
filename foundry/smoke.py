"""Rehearse a venture stage by stage in a throwaway data folder (smoke.yml).

    python -m foundry.smoke --slug sample --through clear --limit 8

For each stage up to and including the one named: run up to --limit ready GitHub jobs with foundry.jobs, then
pass that stage's gate and mark its unfinished jobs skipped so the next stage can start. Charlie never does this
on a real venture; it is how a later stage gets exercised live before a venture reaches it.
"""
import argparse
import sys

from . import audit, jobs, util


def advance(board, stage):
    """Pass the gate for a stage and mark its jobs that did not run as skipped (smoke only)."""
    left = 0
    for j in board["jobs"]:
        if j.get("stage") == stage and j.get("status") == "todo":
            j["status"] = "skipped"
            jobs.note_skipped(board, j["id"], "smoke: stage advanced before this job ran")
            left += 1
    board["gates"][stage] = "passed"
    board["verdict"] = "pending" if board.get("verdict") == "blocked" else board.get("verdict", "pending")
    board["updated"] = util.now()
    return left


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--slug", required=True)
    p.add_argument("--through", required=True, choices=audit.STAGE_ORDER)
    p.add_argument("--limit", type=int, default=jobs.MAX_JOBS)
    a = p.parse_args(argv)
    folder = util.VENTURES / a.slug
    for stage in audit.STAGE_ORDER[: audit.STAGE_ORDER.index(a.through) + 1]:
        board = util.read_json(folder / "board.json")
        if not board:
            print(f"{a.slug}: no board.json")
            return 1
        if not any(j.get("stage") == stage for j in board["jobs"]):
            print(f"== {stage}: no jobs in this launch")
            continue
        print(f"== {stage}", flush=True)
        ran = jobs.run_venture(a.slug, a.limit)
        board = util.read_json(folder / "board.json")
        left = advance(board, stage)
        util.write_json(folder / "board.json", board)
        print(f"== {stage}: {ran} jobs ran, {left} left todo and marked skipped, gate passed", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
