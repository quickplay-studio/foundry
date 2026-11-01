"""What needs Charlie, in one page: data/office/digest.md and the workflow's step summary.

Runs after every launch and jobs run. Reads every board.json and lists, per venture:
drafts waiting for review (with links into the private repo), a blocked verdict,
a stage whose jobs are all finished so its gate can be passed, jobs that gave up,
and the last few log lines. No model, no Claude: a GitHub page is enough to steer.

    python -m foundry.digest            # writes the file, appends to $GITHUB_STEP_SUMMARY when set
"""
import os

from . import audit, util

REPO = "quickplay-studio/foundry-ventures"
OUT = util.OFFICE / "digest.md"


def link(slug, rel):
    return f"[{rel}](https://github.com/{REPO}/blob/main/ventures/{slug}/{rel})"


def gate_ready(board):
    """Stages where every job has finished (done, review or skipped) and the gate is still open."""
    out = []
    for stage in audit.STAGE_ORDER:
        jobs = [j for j in board.get("jobs", []) if j.get("stage") == stage]
        if jobs and board.get("gates", {}).get(stage) == "open" and all(j.get("status") in ("done", "review", "skipped") for j in jobs):
            out.append(stage)
    return out


def venture_lines(folder):
    board = util.read_json(folder / "board.json", {})
    if not board:
        return []
    slug, jobs = folder.name, board.get("jobs", [])
    done = sum(1 for j in jobs if j.get("status") == "done")
    lines = [f"## {board.get('title') or slug} (`{slug}`)",
             f"Stage **{board.get('stage', '?')}**, verdict **{board.get('verdict', 'pending')}**, {done} of {len(jobs)} jobs done, "
             f"gates: " + ", ".join(f"{s} {g}" for s, g in board.get("gates", {}).items() if g != "open") + ".", ""]
    todo = []
    if board.get("verdict") == "blocked":
        stops = [e for e in board.get("log", []) if e.get("flag") == "stop"]
        why = f" ({stops[-1]['job']}: {stops[-1].get('summary', '')[:160]})" if stops else ""
        todo.append(f"- **Blocked**{why}. Override in writing in `board.json` (set `verdict` back to `pending`) or set it to `kill`.")
    for stage in gate_ready(board):
        todo.append(f"- Stage **{stage}** is finished: set `gates.{stage}: passed` in {link(slug, 'board.json')} to start the next stage.")
    for j in jobs:
        if j.get("status") == "review":
            outs = j.get("outputs") or ([j["output"]] if j.get("output") else [])
            todo.append(f"- Review `{j['id']}` ({j.get('autonomy', '')}): " + (", ".join(link(slug, o) for o in outs[:4]) or "no file") + ".")
    gave_up = {s["job"]: s for s in board.get("skipped", []) if int(s.get("attempts", 0)) >= 3}
    for j in jobs:
        if j.get("status") == "skipped" and j["id"] in gave_up:
            todo.append(f"- `{j['id']}` gave up after {gave_up[j['id']]['attempts']} days: {gave_up[j['id']].get('reason', '')[:140]}. Set it back to `todo` to retry.")
    lines += ["### Needs you", *(todo or ["- Nothing. The workforce is running."]), ""]
    recent = board.get("log", [])[-5:]
    if recent:
        lines += ["### Last runs", *(f"- {e.get('date', '')} `{e.get('job', '')}` {e.get('status', '')}, flag {e.get('flag', '')}: {str(e.get('summary') or '')[:140]}" for e in recent), ""]
    return lines


def build():
    ventures = [f for f in sorted(util.VENTURES.glob("*/")) if (f / "board.json").exists()]
    lines = [f"# Foundry digest, {util.today()}", ""]
    if not ventures:
        lines.append("No launched ventures yet.")
    for f in ventures:
        lines += venture_lines(f)
    return "\n".join(lines).rstrip() + "\n"


def main():
    text = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(text)
    return text


if __name__ == "__main__":
    main()
