"""SOP Generation: GitHub implementation of departments/operations/knowledge/sop-generation/SKILL.md.

Finds work done at least twice with the same shape across the ventures next to this one (a job
done in two ventures, an incident cause seen twice, a "Needed from Charlie" line in two status
updates), collects the real commands, files and secret names, and drafts sops/<task-slug>.md in the
triggering venture's folder, 60 lines at most. A step the model cannot tie to collected evidence
is deleted. Nothing is run, so every draft says `tested: no`. The pull request is not opened from
here: sops/publish-commands.md has the commands that move a draft to playbooks/sops/.
"""
import datetime as dt
import re
from collections import defaultdict

from foundry import jobkit as k, util

SECRETS = "GEMINI_API_KEY GROQ_API_KEY GH_TOKEN FIRECRAWL_API_KEY APIFY_TOKEN COMPANIES_HOUSE_API_KEY POSTHOG_API_KEY POSTHOG_PROJECT_ID SUPPORT_IMAP_USER SUPPORT_IMAP_PASSWORD DISCORD_BOT_TOKEN PAYMENTS_READ_KEY".split()
BAD = re.compile("[" + chr(0x2013) + chr(0x2014) + "!]")


def norm(text):
    return re.sub(r"[^a-z]+", " ", str(text).lower()).strip()


def first_date(text, default=""):
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text) or re.search(r"(\d{4})(\d{2})(\d{2})", text)
    return "-".join(m.groups()) if m else default


def candidates(root):
    """slug -> {"kind", "title", "sources": [(venture, date, ref)], "ref": job id or text}."""
    out = {}
    jobs, causes, needs = defaultdict(list), defaultdict(list), defaultdict(list)
    for folder in sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []:
        board = util.read_json(folder / "board.json", {}) if (folder / "board.json").exists() else {}
        for j in board.get("jobs", []) if isinstance(board, dict) else []:
            if isinstance(j, dict) and j.get("status") == "done" and j.get("id") not in (None, "sop-generation"):
                jobs[j["id"]].append((folder.name, str(j.get("updated", ""))[:10], str(j.get("output", ""))))
        for p in sorted((folder / "incidents").glob("*.md")) if (folder / "incidents").is_dir() else []:
            text = p.read_text(encoding="utf-8", errors="replace")
            m = re.search(r"^Cause:\s*(.+)$", text, re.M)
            if m and not norm(m.group(1)).startswith("unknown"):
                causes[norm(m.group(1))].append((folder.name, first_date(text, first_date(p.name)), f"incidents/{p.name}"))
        for p in sorted((folder / "status").glob("????-??-??.md")) if (folder / "status").is_dir() else []:
            m = re.search(r"^Needed from Charlie:\s*(.+?)\.?$", p.read_text(encoding="utf-8", errors="replace"), re.M)
            if m and not norm(m.group(1)).startswith("nothing"):
                needs[norm(m.group(1))].append((folder.name, p.stem, f"status/{p.name}"))
    for jid, src in jobs.items():
        if len({s[0] for s in src}) >= 2:
            out[f"run-{jid}"] = {"kind": "job", "title": f"Run the {jid} job", "sources": src, "ref": jid}
    for cause, src in causes.items():
        if len(src) >= 2:
            out["fix-" + util.slugify(cause)[:40]] = {"kind": "incident", "title": "Fix: " + cause, "sources": src, "ref": cause}
    for need, src in needs.items():
        if len(src) >= 2:
            out["handle-" + util.slugify(need)[:40]] = {"kind": "status", "title": "Handle: " + need, "sources": src, "ref": need}
    return out


def evidence(cand):
    """Real commands, files and secret names; the only things a step may point at."""
    items = []
    if cand["kind"] == "job":
        skill = next(iter(util.DEPARTMENTS.glob(f"*/*/{cand['ref']}/SKILL.md")), None)
        text = skill.read_text(encoding="utf-8") if skill else ""
        items.append(f"python -m foundry.jobs --slug <slug> --job {cand['ref']}")
        items += sorted({o for s in cand["sources"] for o in re.findall(r"[\w./-]+\.\w+", s[2])})[:4]
        items += [n for n in SECRETS if n in text]
        for wf in sorted((util.ROOT / ".github" / "workflows").glob("*.yml")):
            items += [ln.strip().removeprefix("run:").strip() for ln in wf.read_text(encoding="utf-8").splitlines() if "foundry.jobs" in ln and "run:" in ln][:1]
    else:
        items += sorted({s[2] for s in cand["sources"]})
    return list(dict.fromkeys(items))


def draft(slug, cand, items):
    names = ", ".join(f"{v} ({d})" for v, d, _ in cand["sources"])
    ans = k.ask("Draft a short standard operating procedure for a solo founder's repeated task from the evidence only. Every step must name one evidence item exactly as given in `ref`; "
                "no step without one. Plain UK English, no dashes, no exclamation marks. "
                'Return JSON only: {"purpose": "<one sentence>", "when": "<one sentence>", "steps": [{"text": "<step>", "ref": "<evidence item>"}], "check": "<how to see it worked>"}\n\nTASK '
                + cand["title"] + "\nSOURCES " + names + "\nEVIDENCE\n" + "\n".join(items))
    steps, purpose, when, check = [], "", "", ""
    if isinstance(ans, dict):
        steps = [s for s in ans.get("steps") or [] if isinstance(s, dict) and s.get("ref") in items and str(s.get("text", "")).strip() and not BAD.search(str(s["text"]))]
        purpose, when, check = (str(ans.get(x, "")).strip() for x in ("purpose", "when", "check"))
    if not steps:  # template: one step per evidence item
        steps = [{"text": (f"Run `{i}` and expect it to finish without an error." if i.startswith(("python", "git", "gh", "pip")) else f"Check that `{i}` exists." if "/" in i or "." in i else f"Set the secret `{i}` (name only)."), "ref": i} for i in items]
    if BAD.search(purpose + when + check) or min(len(purpose), len(when), len(check)) < 15:
        purpose, when, check = f"Repeat the work named: {cand['title']}.", f"When the same task comes up again; it has been done {len(cand['sources'])} times.", "The output file named in the steps exists and the board shows the job as done."
    secrets = [i for i in items if i in SECRETS]
    lines = ["tested: no", "untested steps: all, because the job that wrote this draft ran no command", "", f"# SOP: {slug}", "", "## Purpose", purpose, "", "## When to use it", when, "", "## Before you start",
             "- Inputs: the venture folder with its board.json.", f"- Secret names: {', '.join(secrets) if secrets else 'none'}", "", "## Steps"]
    lines += [f"{n}. {s['text']}" for n, s in enumerate(steps[:12], 1)] + ["", "## Check it worked", check, "", "## If it fails"]
    lines += [f"- See `{s[2]}` in {s[0]}" for s in cand["sources"] if s[2].startswith("incidents/")] or ["- Read the job's last board.json log entry, then open an incident note."]
    lines += ["", "## Owner", "Charlie Page-Blair", "", "## Last checked", util.today(), "", "## Source ventures"] + [f"- {v} ({d})" for v, d, _ in cand["sources"]]
    return "\n".join(lines[:60])


def main(ctx):
    root = ctx["folder"].parent
    made = []
    existing = {p.stem for p in (util.ROOT / "playbooks").rglob("*.md")} if (util.ROOT / "playbooks").is_dir() else set()
    stale = []
    for p in sorted((util.ROOT / "playbooks" / "sops").glob("*.md")) if (util.ROOT / "playbooks" / "sops").is_dir() else []:
        m = re.search(r"## Last checked\s*\n(\d{4}-\d{2}-\d{2})", p.read_text(encoding="utf-8"))
        if m and (dt.date.fromisoformat(util.today()) - dt.date.fromisoformat(m.group(1))).days > 90:
            stale.append(p.stem)
    for slug, cand in candidates(root).items():
        if slug in existing or (ctx["folder"] / "sops" / f"{slug}.md").exists() or len(cand["sources"]) < 2:
            continue
        k.write(ctx, f"sops/{slug}.md", draft(slug, cand, evidence(cand)))
        made.append((slug, cand))
        if len(made) == 3:
            break
    if not made:
        return {"skipped": "no repeated work qualifies yet (needs two ventures or two sources)" + (f"; SOPs older than 90 days: {', '.join(stale)}" if stale else "")}
    cmds = (k.read(ctx, "sops/publish-commands.md", "") or "# Publish the SOP drafts\n\nNothing is pushed from the job. Run from the Foundry repo root, with the private checkout in data/.\n").rstrip("\n")
    for slug, cand in made:
        srcs = "; ".join(f"{v} {d}" for v, d, _ in cand["sources"])
        cmds += f"\n\n```\ngit checkout -b sop/{slug}\ncp data/ventures/{ctx['slug']}/sops/{slug}.md playbooks/sops/{slug}.md\ngit add playbooks/sops/{slug}.md && git commit -m \"sop: {slug}\"\ngit push -u origin sop/{slug}\ngh pr create --title \"sop: {slug}\" --body \"Sources: {srcs}. tested: no.\"\n```"
    k.write(ctx, "sops/publish-commands.md", cmds)
    return {"summary": f"{len(made)} SOP drafts written ({', '.join(s for s, _ in made)}), all tested: no" + (f"; SOPs older than 90 days: {', '.join(stale)}" if stale else ""), "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
