"""Approval Docs: GitHub implementation of departments/marketing/brand-deals/approval-docs/SKILL.md.

Assembles the sign-off pack for the latest script version of each deal: cover, compliance table, final script,
storyboard, disclosure, claims list, schedule and rights as Charlie recorded them, a brand-safety table and a blank
sign-off block. Each version is a new file and earlier ones are never overwritten. The PDF is rendered with the
runner's headless Chrome (foundry.jobkit.render_pdf) and pending where there is none. It never emails a sponsor.
"""
import datetime as dt
import difflib
import re

from foundry import jobkit as k

PROFANITY = re.compile(r"\b(fuck|shit|bastard|bollocks|piss|crap)\w*\b", re.I)


def tidy(text):
    return re.sub(r"\s+", " ", re.sub(r"\s*[\u2013\u2014]\s*", ", ", re.sub(r"!+", ".", str(text)).replace(" - ", ", "))).strip()


def groups(md):
    out, cur = {}, None
    for line in md.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip().lower()
            out[cur] = []
        elif cur is not None and line.strip():
            out[cur].append(re.sub(r"^[-*]\s*(\[.\]\s*)?", "", line.strip()))
    return out


def variant_rows(script):
    chosen = (re.search(r"^\W*chosen\W*[:=]\s*([AB])", script, re.I | re.M) or [None, "A"])[1].upper()
    block = re.search(rf"## Variant {chosen}[^\n]*\n(.*?)(?=\n## |\Z)", script, re.S)
    rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in (block.group(1) if block else "").splitlines() if l.startswith("|") and not re.match(r"^\|\s*(Time|-)", l)]
    return chosen, [r for r in rows if len(r) >= 4]


def words_of(text):
    return {w for w in re.findall(r"[a-z0-9£']+", text.lower()) if len(w) > 2}


def meets(point, rows):
    pw = words_of(point)
    return next((f"line {i}" for i, r in enumerate(rows, 1) if pw and len(pw & words_of(r[1])) / len(pw) >= 0.6), "NOT MET")


def scripts_of(d):
    found = {int(m.group(1)): p for p in d.glob("script-v*.md") for m in [re.match(r"script-v(\d+)\.md$", p.name)] if m}
    return found


def main(ctx):
    folder, brain, idea = ctx["folder"], ctx["brain"], ctx["idea"]
    base = folder / "launch/deals"
    today = dt.date.today().isoformat()
    comps = [str(c.get("name", "")).lower() for c in (k.read(ctx, "launch/inputs/competitors.json", []) or []) if isinstance(c, dict) and c.get("name")]
    made, issues, pdfs = [], 0, 0
    for d in sorted(base.glob("*")) if base.is_dir() else []:
        found = scripts_of(d) if d.is_dir() else {}
        if not found:
            continue
        n = max(found)
        if (d / f"approval-pack-v{n}.md").exists():
            continue
        script = found[n].read_text(encoding="utf-8")
        brief = (d / "brief.md").read_text(encoding="utf-8") if (d / "brief.md").exists() else ""
        check = groups((d / "checklist.md").read_text(encoding="utf-8")) if (d / "checklist.md").exists() else {}
        feedback = (d / "feedback.md").read_text(encoding="utf-8") if (d / "feedback.md").exists() else ""
        brand = (re.search(r"^\W*brand\W*[:=]\s*(.+)$", brief, re.I | re.M) or [None, d.name.replace("-", " ").title()])[1].strip()
        chosen, rows = variant_rows(script)
        voice = " ".join(r[1] for r in rows)
        must, banned, claims, dates = (check.get(g, []) for g in ("must-say points", "banned", "claims supplied", "dates"))
        safety = [("Banned words from the brief", [b for b in banned if len(b) > 2 and b.lower() in script.lower()]), ("Competitor names", [c for c in comps if c and c in voice.lower()]),
                  ("Claim not in the brief's supplied list", [x for x in re.findall(r"\d+(?:[.,]\d+)*", voice) if x not in brief]), ("Profanity", PROFANITY.findall(voice)),
                  ("Music or footage with no licence noted", [r[3][:40] for r in rows if re.search(r"music|footage|stock|clip", r[3], re.I) and not re.search(r"licen", r[3], re.I)]),
                  ("Personal data of anyone shown", re.findall(r"[\w.+-]+@[\w-]+\.\w+|\+?\d[\d\s-]{9,}\d", script))]
        ai = k.ask('Return JSON only: {"flags": [{"issue": "...", "where": "..."}]}. Brand-safety review of this sponsored script against the brief. List only real problems: a claim the brief did not supply, a competitor mention, anything unsafe for a brand. Empty list if none.\n\nBRIEF\n' + brief[:2000] + "\nSCRIPT\n" + voice[:1500])
        ai_flags = [f for f in (ai.get("flags") if isinstance(ai, dict) and isinstance(ai.get("flags"), list) else []) if isinstance(f, dict) and f.get("issue")] if isinstance(ai, dict) else None
        failed = [s for s in safety if s[1]]
        issues += len(failed) + len(ai_flags or [])
        disc = next((r for r in rows if re.search(r"\bad\b", r[1], re.I)), None)
        legal = [l.strip() for l in brief.splitlines() if re.search(r"\bfee\b|usage|rights|exclusiv", l, re.I)]
        tag = f"_Version v{n}, {today}_"
        md = [f"# Approval pack: {brand}", tag, "", "## Cover", f"- Deal: {brand}", f"- Version: v{n}, {today}", f"- Deliverables: {'; '.join(check.get('deliverables', [])) or 'see the brief'}", f"- Planned post date: {dates[0] if dates else 'not recorded'}", "",
              f"{idea.get('title', ctx['slug'])} is made by Charlie Page-Blair in London. {tidy(str(idea.get('problem', '')).split('.')[0])}.", tag, "",
              "## Compliance table", "| Brief requirement | Where it is met |", "|---|---|", *[f"| {p} | {meets(p, rows)} |" for p in must], *[f"| Avoid: {b} | {'FOUND in script' if any(b == s for s in safety[0][1]) else 'not used'} |" for b in banned], tag, "",
              f"## Final script (variant {chosen})", "| Time | Voiceover | On screen | Visual |", "|---|---|---|---|", *[f"| {' | '.join(r[:4])} |" for r in rows], tag, "",
              "## Storyboard", "| Scene | Visual | On-screen text | Voiceover |", "|---|---|---|---|", *[f"| {i} | {r[3]} | {r[2]} | {r[1]} |" for i, r in enumerate(rows, 1)], tag, "",
              "## Disclosure", f"Wording: {disc[1] if disc else 'none found: add it'}", f"Appears: {'at the first line, with an Ad label on screen' if disc and rows and disc is rows[0] else 'check the script'}.", "Use the platform's paid partnership tool as well.", tag, "",
              "## Claims", "| Claim | Source |", "|---|---|", *[f"| {c} | supplied by the brand in the brief |" for c in claims], *([] if claims else ["| none | the script uses no brand claims |"]), tag, "",
              "## Schedule and usage rights", *([f"- {l}" for l in legal] or ["- Not recorded. Charlie confirms the fee, schedule and usage rights."]), tag, "",
              "## Brand-safety check", "| Check | Result | Detail |", "|---|---|---|", *[f"| {name} | {'FAIL' if hit else 'pass'} | {', '.join(map(str, hit))[:80]} |" for name, hit in safety],
              f"| AI check | {'not run' if ai_flags is None else 'FAIL' if ai_flags else 'pass'} | {'; '.join(tidy(f['issue']) for f in (ai_flags or []))[:120]} |", tag, "",
              "## Sign-off", "Name:", "Date:", "Approved, or changes needed:", tag]
        k.write(ctx, f"launch/deals/{d.name}/approval-pack-v{n}.md", "\n".join(md))
        pdfs += 1 if k.render_pdf(ctx, f"launch/deals/{d.name}/approval-pack-v{n}.pdf", "\n".join(md)) else 0
        prev = scripts_of(d).get(n - 1)
        diff = [l for l in difflib.unified_diff(prev.read_text(encoding="utf-8").splitlines(), script.splitlines(), lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")] if prev else []
        why = [l.strip() for l in feedback.splitlines() if l.strip()][:3]
        change = f"{len(diff)} script lines changed" + (f" after feedback: {tidy(' / '.join(why))[:150]}" if why else "") if prev else "First pack"
        old = k.read(ctx, f"launch/deals/{d.name}/changes.md", "") or "# Changes\n\n| Version | Date | What changed |\n|---|---|---|\n"
        k.write(ctx, f"launch/deals/{d.name}/changes.md", old.rstrip("\n") + f"\n| v{n} | {today} | {change} |")
        made.append(f"{d.name} v{n}")
    if not made:
        return {"skipped": "no deal has a script version without an approval pack"}
    return {"summary": f"Packs written for {', '.join(made)}. {issues} brand-safety issues shown in the pack. {pdfs} PDFs rendered{'' if pdfs == len(made) else ' (the rest pending headless Chrome)'}; Charlie sends them, nothing was emailed.", "flag": "caution" if issues else "ok"}


if __name__ == "__main__":
    k.run(main)
