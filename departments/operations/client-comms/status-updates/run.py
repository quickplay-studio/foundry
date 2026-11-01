"""Status Updates: GitHub implementation of departments/operations/client-comms/status-updates/SKILL.md.

Reads board.json, budget.json and the previous update, and writes a 5 line update (under 600
characters) to status/<date>.md and status/latest.md. Every number comes from the files. Lines 1
and 5 are fixed text; the free model may only reword lines 2 to 4, and a draft with a number
that is not in the facts, a dash or an exclamation mark is thrown away for the template.
No issue comment and no email are sent from here.
"""
import datetime as dt
import json
import re

from foundry import jobkit as k, util

BAD = re.compile("[" + chr(0x2013) + chr(0x2014) + "!]")  # dashes and exclamation marks are not allowed in the voice


def gbp(x):
    try:
        x = float(x or 0)
    except (TypeError, ValueError):
        x = 0.0
    return f"£{x:,.2f}".replace(".00", "")


def ids(items, cap=4):
    items = list(items)
    return ", ".join(items[:cap]) + (f" and {len(items) - cap} more" if len(items) > cap else "") if items else ""


def last_date(ctx):
    dated = sorted(p.stem for p in (ctx["folder"] / "status").glob("????-??-??.md")) if (ctx["folder"] / "status").is_dir() else []
    if dated:
        return dated[-1]
    m = re.search(r"\d{4}-\d{2}-\d{2}", (k.read(ctx, "status/latest.md", "") or "")[:200])
    return m.group(0) if m else ""


def facts_from(ctx, since):
    board = ctx["board"] if isinstance(ctx["board"], dict) else {}
    jobs = [j for j in board.get("jobs") or [] if isinstance(j, dict) and j.get("id")]
    gates = board.get("gates") or {}

    def after(d):
        return str(d or "")[:10] > since

    inc = [i for i in board.get("incidents") or [] if isinstance(i, dict)]
    open_inc = [i for i in inc if i.get("status") in ("open", "mitigated")]
    stages = [s for s in gates if any(j.get("stage") == s for j in jobs)]
    nxt = next((s for s in stages if gates.get(s) != "passed"), "")
    pending = [j for j in jobs if j.get("stage") == nxt and j.get("status") in ("todo", "review", "blocked")]
    review = [j["id"] for j in jobs if j.get("status") == "review"]
    blocked = [j["id"] for j in jobs if j.get("status") == "blocked"]
    waits = (f"Charlie to review {ids(review)} and set gates.{nxt} to passed" if review else f"{ids(j['id'] for j in pending)} to run" if pending else f"Charlie to set gates.{nxt} to passed") if nxt else "nothing, every gate is passed"
    budget = ctx["budget"] if isinstance(ctx["budget"], dict) else {}
    return {"stage": board.get("stage", ""), "done_total": sum(j.get("status") == "done" for j in jobs), "total": len(jobs),
            "passed": [s for s in gates if gates[s] == "passed"], "next_gate": nxt, "waits": waits,
            "done_new": [j["id"] for j in jobs if j.get("status") == "done" and (not since or after(j.get("updated")))],
            "incidents_new": [str(i.get("id")) for i in inc if not since or after(i.get("date")) or (i.get("status") == "resolved" and after(i.get("last_seen")))],
            "skipped_new": sum(1 for s in board.get("skipped") or [] if isinstance(s, dict) and (not since or after(s.get("date")))),
            "review": review, "blocked": blocked, "open_incidents": len(open_inc),
            "high_incidents": [str(i.get("id")) for i in open_inc if i.get("severity") == "high"],
            "spent": gbp(budget.get("spent")), "revenue": gbp(budget.get("revenue")), "ad_budget": gbp(budget.get("ad_budget")),
            "qa": qa_line(ctx)}


def qa_line(ctx):
    """One line from qa/result.json when the QA job has run (its documented shape: verdict, sha, date, checks)."""
    qa = k.read(ctx, "qa/result.json", None)
    if not isinstance(qa, dict) or not qa.get("verdict"):
        return ""
    checks = [c for c in (qa.get("checks") or []) if isinstance(c, dict)]
    failed = sum(1 for c in checks if str(c.get("result", "")).lower() not in ("pass", "ok"))
    return f"QA: {str(qa['verdict']).upper()} on {str(qa.get('sha', ''))[:7] or 'no sha'} ({len(checks)} checks, {failed} failed, {str(qa.get('date', ''))[:10]})."


def template(f):
    need = []
    if f["review"]:
        need.append(f"review {ids(f['review'])}")
    if f["blocked"]:
        need.append(f"unblock {ids(f['blocked'])}")
    if f["high_incidents"]:
        need.append(f"read high incidents {ids(f['high_incidents'])}")
    return [f"Done since the last update: {ids(f['done_new']) or 'nothing new'}.",
            f"Next: the {f['next_gate']} gate, which waits for {f['waits']}." if f["next_gate"] else "Next: every gate is passed, so the venture is in run.",
            f"Needed from Charlie: {'; '.join(need) if need else 'nothing'}."]


def reword(f, base, today, since):
    ans = k.ask("You copy-edit a project status update. Reword the three lines below in plain, short UK English without changing a fact. No dashes, no exclamation marks, "
                "no number that is not already in the lines. Keep each line's first words. Return JSON only: {\"lines\": [\"<line 2>\", \"<line 3>\", \"<line 4>\"]}\n\nLINES\n" + "\n".join(base))
    lines = ans.get("lines") if isinstance(ans, dict) else None
    blob = json.dumps(f) + today + since
    if not (isinstance(lines, list) and len(lines) == 3 and all(isinstance(x, str) for x in lines)):
        return base
    for new, old in zip(lines, base):
        if new.split(":")[0] != old.split(":")[0] or BAD.search(new) or any(n not in blob for n in re.findall(r"\d+(?:[.,]\d+)*", new)):
            return base
    return [x.strip() for x in lines]


def main(ctx):
    today, since = util.today(), last_date(ctx)
    f = facts_from(ctx, since)
    if not f["total"]:
        return {"skipped": "the board has no jobs yet"}
    if (ctx["folder"] / "status" / f"{today}.md").exists():
        return {"skipped": "an update for today exists"}
    changed = bool(f["done_new"] or f["incidents_new"] or f["skipped_new"] or not since)
    age = (dt.date.fromisoformat(today) - dt.date.fromisoformat(since)).days if since else 99
    if not changed and age < 7:
        return {"skipped": f"no change since {since}, last update under 7 days old"}
    if not changed:
        text = f"No change since {since}. Blocker: the {f['next_gate'] or 'last'} gate waits for {f['waits']}."
    else:
        head = f"Where we are: {f['stage'] or 'launch'} stage, {f['done_total']} of {f['total']} jobs done. Gates passed: {', '.join(f['passed']) or 'none'}."
        body = reword(f, template(f), today, since)
        spend = f"Spend: {f['spent']} of {f['ad_budget']} ad budget, revenue {f['revenue']}."
        text = "\n".join([head] + body + [spend] + ([f["qa"]] if f["qa"] else []))
        if len(text) > 600 or BAD.search(text):  # over length or a stray mark: fall back to the short template
            f = dict(f, done_new=f["done_new"][:2], review=f["review"][:2], blocked=f["blocked"][:2], high_incidents=f["high_incidents"][:2])
            text = "\n".join([head] + template(f) + [spend])[:600]
    k.write(ctx, f"status/{today}.md", text)
    k.write(ctx, "status/latest.md", text)
    return {"summary": f"Status update written for {today}: {f['done_total']} of {f['total']} jobs done, {f['open_incidents']} open incidents.", "flag": "caution" if f["high_incidents"] else "ok"}


if __name__ == "__main__":
    k.run(main)
