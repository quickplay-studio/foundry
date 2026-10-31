"""Cross-department contracts: which skill writes which venture file, and who reads it.

    python -m foundry.contracts            # write map/contracts.json and print the gaps
    python -m foundry.contracts --check    # exit 1 when a read path has no writer (used by the tests)

A path is any `ventures/<slug>/...` or `office/...` string in a skill. Paths in the
Output section are writes; paths in Inputs and Steps are reads. The launch writes the
base files (BASE). Folders named data/, inputs/, raw/ and finance/ are Charlie's drops.
Glob characters and <placeholders> are normalised so `sell/leads.csv` matches
`ventures/<slug>/sell/leads.csv` and `ventures/{slug}/sell/leads.csv` alike.
"""
import json
import re
import sys

from . import util

PATH = re.compile(r"`?(?:ventures/(?:<slug>|\{slug\}|<venture>)/|office/)([\w\-./<>{}*]+?)`?(?=[\s`,;:)\]]|$)")
BASE = {"idea.json", "brain.md", "plan.md", "board.json", "budget.json", "audit.json"}
# Folders Charlie drops files into (exports, documents, assets); a job reads them and never expects another job to write them.
DROPS = ("data/", "inputs/", "raw/", "finance/", "meetings/", "inbox/", "calendar/", "hr/", "talent/", "records/", "extract/",
         "migration/", "eval/", "brand/", "proof/", "support/inbox", "support/community/rules.md", "deliverables/",
         "launch/deals/", "sell/proposals/proposal.css", "sell/network/my-contacts.csv", "sell/manual-changes.csv")
# Per-job state and settings a job creates with defaults on its first run, then reads back.
STATE = ("-state.json", "seen.json", "index.json", "usage.jsonl", "limits.json", "people.json", "rules.json", "watch.json",
         "events.json", "comments.json", "dms.json", "inbox.json", "suppressed.json", "corrections.csv", "health-history/")
SECTION = re.compile(r"^## +(.+?)\s*$", re.M)


def normalise(path):
    path = path.strip("`'\". ").rstrip("/")
    path = re.sub(r"<[^>]+>|\{[^}]+\}", "*", path)  # placeholders become globs
    return path


def sections(text):
    """{section name: body} for a SKILL.md body."""
    out, parts = {}, SECTION.split(text)
    for i in range(1, len(parts) - 1, 2):
        out[parts[i].lower()] = parts[i + 1]
    return out


def scan():
    rows = []
    for path in sorted(util.DEPARTMENTS.glob("*/*/*/SKILL.md")):
        job = path.parent.name
        dept = path.parents[2].name
        text = path.read_text(encoding="utf-8")
        office = "office/" in text
        sec = sections(text)
        writes = {normalise(p) for p in PATH.findall(sec.get("output", ""))}
        for m in PATH.finditer(sec.get("steps", "")):  # a path a step writes, appends, saves or creates counts as written
            before = sec["steps"][max(0, m.start() - 60):m.start()].lower()
            if re.search(r"\b(write|writes|written|append|appends|save|saves|create|creates|created|produce|produces|emit|emits|record|records)\b", before):
                writes.add(normalise(m.group(1)))
        reads = set()
        for name in ("inputs", "steps", "reads from the brain"):
            reads |= {normalise(p) for p in PATH.findall(sec.get(name, ""))}
        reads -= writes
        reads = {r for r in reads if r not in ("**", "*")}
        rows.append({"job": job, "department": dept, "writes": sorted(writes), "reads": sorted(reads), "office": office})
    return rows


def glob_re(path):
    return re.escape(path).replace(r"\*", r"[^/]+")


def matches(read, writes):
    """Does any written path cover this read path? Both may hold * globs. A written folder covers files
    under it, a read folder (no extension) is covered by anything written under it, and a read glob is
    covered by any written file it matches."""
    folder_read = "." not in read.split("/")[-1]
    for w in writes:
        if re.fullmatch(glob_re(w), read) or re.fullmatch(glob_re(w) + r"/.*", read):
            return True
        if re.fullmatch(glob_re(read), w):
            return True
        if folder_read and (w.startswith(read + "/") or re.fullmatch(glob_re(read) + r"/.*", w)):
            return True
    return False


def classify(read, written):
    """base (the launch writes it), written (another job writes it), drop (Charlie supplies it), state (the job's own
    settings or memory, created on first run) or gap (nobody writes it and nothing says who should)."""
    name = read.split("/")[-1]
    if name in BASE:
        return "base"
    if matches(read, written):
        return "written"
    if any((read + "/").startswith(d) or f"/{d}" in read + "/" for d in DROPS):
        return "drop"
    if any(read.endswith(s) or f"/{s}" in read + "/" for s in STATE):
        return "state"
    return "gap"


def gaps(rows):
    written = sorted({w for r in rows for w in r["writes"]})
    return [{"job": r["job"], "department": r["department"], "reads": read}
            for r in rows for read in r["reads"] if classify(read, written) == "gap"]


def drops(rows):
    """What Charlie can drop into a venture folder, and which job reads it."""
    written = sorted({w for r in rows for w in r["writes"]})
    out = {}
    for r in rows:
        for read in r["reads"]:
            if classify(read, written) == "drop":
                out.setdefault(read, []).append(f"{r['department']}/{r['job']}")
    return dict(sorted(out.items()))


def main(check=False):
    rows = scan()
    missing = gaps(rows)
    util.write_json(util.ROOT / "map" / "contracts.json", {"generated": util.now(), "jobs": rows, "gaps": missing, "drops": drops(rows)})
    print(f"{len(rows)} skills, {sum(len(r['writes']) for r in rows)} written paths, {len(drops(rows))} drop files, {len(missing)} reads without a writer")
    for m in missing:
        print(f"  {m['department']}/{m['job']} reads {m['reads']}")
    if check and missing:
        sys.exit(1)
    return rows, missing


if __name__ == "__main__":
    main(check="--check" in sys.argv)
