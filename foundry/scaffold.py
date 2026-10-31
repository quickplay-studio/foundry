"""Create department folders and one SKILL.md stub per job from map/tree.json.

Never overwrites a skill whose status is not stub. Safe to re-run after every
weekly drop: new jobs get stubs, existing work is untouched.

    python -m foundry.scaffold          # write stubs
    python -m foundry.scaffold --check  # report only
"""
import re
import sys

from . import util

TEMPLATE = util.ROOT / "templates" / "SKILL.template.md"
FRONT = re.compile(r"^---\n(.*?)\n---", re.S)


def render(job, dept, fn):
    text = TEMPLATE.read_text(encoding="utf-8")
    fields = {
        "id": job["id"], "title": job["title"], "department": dept["id"], "function": fn["id"],
        "autonomy": job["autonomy"], "stage": job.get("stage") or "none",
        "builds_on": ", ".join(job.get("builds_on", [])), "summary": job["summary"],
    }
    for key, value in fields.items():
        text = text.replace("{" + key + "}", str(value))
    return text


def status_of(path):
    m = FRONT.search(path.read_text(encoding="utf-8"))
    if not m:
        return "unknown"
    for line in m.group(1).splitlines():
        if line.startswith("status:"):
            return line.split(":", 1)[1].strip()
    return "unknown"


def dept_readme(dept):
    lines = [f"# {dept['title']}", "", dept.get("tagline", ""), ""]
    if dept.get("note"):
        lines += [dept["note"], ""]
    total = sum(len(f["jobs"]) for f in dept["functions"])
    lines += [f"{total} jobs. Stage: {dept.get('stage')}.", ""]
    for fn in dept["functions"]:
        lines.append(f"## {fn['title']}")
        for job in fn["jobs"]:
            lines.append(f"- `{job['id']}` ({job['autonomy']}): {job['summary']}")
        lines.append("")
    return "\n".join(lines)


def main(check=False):
    tree = util.load_tree()
    created, kept = [], []
    for dept in tree["departments"]:
        droot = util.DEPARTMENTS / dept["id"]
        readme = droot / "README.md"
        if not check:
            droot.mkdir(parents=True, exist_ok=True)
            readme.write_text(dept_readme(dept), encoding="utf-8")
        for fn in dept["functions"]:
            for job in fn["jobs"]:
                path = droot / fn["id"] / job["id"] / "SKILL.md"
                if path.exists() and status_of(path) != "stub":
                    kept.append(str(path.relative_to(util.ROOT)))
                    continue
                created.append(str(path.relative_to(util.ROOT)))
                if not check:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(render(job, dept, fn), encoding="utf-8")
    print(f"stubs written or refreshed: {len(created)}, filled skills kept: {len(kept)}")
    return created, kept


if __name__ == "__main__":
    main(check="--check" in sys.argv)
