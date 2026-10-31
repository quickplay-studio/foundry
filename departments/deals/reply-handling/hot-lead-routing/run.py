"""Hot-Lead Routing: GitHub implementation of departments/deals/reply-handling/hot-lead-routing/SKILL.md.

Rules only, no model. Interested replies with status new get a pipeline row (new or updated), a priority and
status routed. The alert for Charlie is written to sell/alerts.md; no issue is opened and nothing is sent.
"""
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import dealkit as D  # noqa: E402
from foundry import jobkit as k  # noqa: E402

HIGH_WORDS = re.compile(r"price|pricing|cost|how much|quote|demo|£|today|tomorrow|this week|next week", re.I)
HIGH_ROLE = re.compile(r"owner|director|head|founder", re.I)


def soon(text):
    for m in re.findall(r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}", text):
        d = D.parse_date(m)
        if d and 0 <= (d - dt.date.today()).days <= 7:
            return True
    return False


def main(ctx):
    gate = D.gate(ctx)
    if gate:
        return gate
    replies = k.read(ctx, "sell/replies.json", []) or []
    sup = D.suppressed(ctx)
    todo = [r for r in replies if isinstance(r, dict) and r.get("label") == "interested" and r.get("status") == "new"]
    blocked = [r for r in todo if D.email_of(r.get("from", "")) in sup]
    todo = [r for r in todo if r not in blocked]
    if not todo:
        return {"skipped": f"no new interested replies ({len(blocked)} suppressed)" if blocked else "no new interested replies"}
    rows, new_ids, lines, high_n = D.pipeline(ctx), set(), [], 0
    for r in todo:
        addr = D.email_of(r["from"])
        name = re.sub(r"<.*?>|[\"']", "", r["from"]).strip()
        name = "" if "@" in name else name
        summary = D.txt(r.get("summary"), 200)
        row = D.find_row(rows, addr, r.get("company", ""), name)
        if row:
            if row.get("stage") in ("new", "dormant"):
                row["stage"] = "qualified"
            row["last_touch"] = row["updated"] = D.today()
            D.add_note(row, f"{D.today()} interested reply: {summary}")
        else:
            row = D.new_row(rows, company=r.get("company", ""), contact=name, email=addr, source="outbound-reply", stage="qualified",
                            next_step="book call", next_step_date=D.today(), last_touch=D.today(), notes=f"{D.today()} interested reply: {summary}")
            rows.append(row)
            new_ids.add(row["id"])
        high = bool(HIGH_WORDS.search(summary) or soon(summary) or HIGH_ROLE.search(row.get("role", "")))
        high_n += high
        r.update(status="routed", deal_id=row["id"], priority="high" if high else "normal")
        if row["id"] in new_ids:
            link = f", thread https://mail.google.com/mail/u/0/#all/{r['thread_id']}" if r.get("thread_id") else ""
            note = summary if r.get("classified_by") == "model" else "keyword match, read the thread"
            lines.append(f"Hot lead: {row.get('company') or addr} ({r['priority']}): pipeline {row['id']}{link}. {note}")
    D.save_pipeline(ctx, rows)
    k.write(ctx, "sell/replies.json", replies)
    D.alert(ctx, "hot-lead-routing", lines)
    return {"summary": f"Routed {len(todo)} interested replies ({high_n} high priority, {len(new_ids)} new deals). {len(blocked)} suppressed."}


if __name__ == "__main__":
    k.run(main)
