"""Event Coordination: GitHub implementation of departments/customer/community/event-coordination/SKILL.md.

Decides whether a live event is worth it (a thin community gets a text AMA), proposes two evening or
weekend UK slots outside bank holidays, and drafts the run sheet, announcement, reminder and recap.
It books nothing, invites nobody and writes no calendar entry: Charlie picks the slot and posts.
"""
import re
from datetime import date, datetime, timedelta, timezone

import requests

from foundry import jobkit as k, util

HOLIDAYS = {date.fromisoformat(x) for x in (
    "2026-12-25 2026-12-28 2027-01-01 2027-03-26 2027-03-29 2027-05-03 2027-05-31 2027-08-30 2027-12-27 2027-12-28 2028-01-03 2028-04-14 2028-04-17").split()}
GQL = ('query{repository(owner:"%s",name:"%s"){discussions(first:30,orderBy:{field:UPDATED_AT,direction:DESC}){nodes{id createdAt '
       "author{login} comments(first:30){nodes{id createdAt author{login}}}}}}}")
JOIN = {"text AMA": "post your question in the Discussions thread once it opens", "spotlight evening": "join the thread or call link posted on the day", "short call": "use the call link posted on the day"}


def members(ctx, notes):
    """Distinct authors and items from the last 30 days: Discussions, or drops in support/community/inbox/."""
    seen, repo, tok = [], str(ctx["idea"].get("repo") or ""), k.secret("GH_TOKEN")
    if re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        try:
            if not tok:
                raise ValueError("GH_TOKEN not set")
            r = requests.post("https://api.github.com/graphql", json={"query": GQL % tuple(repo.split("/", 1))}, headers={"Authorization": f"Bearer {tok}"}, timeout=40)
            for dsc in r.json()["data"]["repository"]["discussions"]["nodes"]:
                seen += [(x["createdAt"], (x.get("author") or {}).get("login", "")) for x in [dsc] + dsc["comments"]["nodes"]]
        except Exception as exc:  # noqa: BLE001
            notes.append(f"GitHub Discussions skipped ({type(exc).__name__})")
    for p in sorted((ctx["folder"] / "support" / "community" / "inbox").glob("*.json")):
        data = util.read_json(p, [])
        seen += [(str(x.get("created", "")), str(x.get("author", ""))) for x in (data if isinstance(data, list) else []) if isinstance(x, dict)]
    cut = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    live = [(c, a) for c, a in seen if str(c)[:10] >= cut and a]
    return len({a for _, a in live}), len(live)


def slot(day, hour, minute):
    try:
        from zoneinfo import ZoneInfo
        return datetime(day.year, day.month, day.day, hour, minute, tzinfo=ZoneInfo("Europe/London")).strftime("%A %d %B %Y, %H:%M %Z (Europe/London)")
    except Exception:  # noqa: BLE001
        return f"{day:%A %d %B %Y}, {hour:02d}:{minute:02d} UK time (Europe/London)"


def pick(start, weekdays, hour, minute):
    for n in range(14):
        day = start + timedelta(days=n)
        if day.weekday() in weekdays and day not in HOLIDAYS:
            return day, slot(day, hour, minute)
    return None, ""


def main(ctx):
    notes, today = [], datetime.now(timezone.utc).date()
    raw = k.read(ctx, "support/community/events.json", []) or []
    raw = raw if isinstance(raw, list) else []
    cfgs = [e for e in raw if isinstance(e, dict) and "min_members_for_live" in e]
    events = [e for e in raw if isinstance(e, dict) and "min_members_for_live" not in e]
    try:
        threshold = int((cfgs[0] if cfgs else k.read(ctx, "support/config.json", {}) or {}).get("min_members_for_live", 50))
    except (TypeError, ValueError):
        threshold = 50
    n_members, n_posts = members(ctx, notes)
    faq = (k.read(ctx, "support/faq.json", {}) or {}).get("entries", [])
    gaps = (k.read(ctx, "support/community/faq-gaps.json", {}) or {})
    topics = [str(e.get("question")) for e in faq if isinstance(e, dict) and e.get("status") in ("needs-human-fact", "stale") and e.get("question")]
    topics += [str(q.get("question")) for q in gaps.get("top_questions", []) if isinstance(q, dict)] + [str(g.get("question")) for g in gaps.get("gaps", []) if isinstance(g, dict)]
    topics = list(dict.fromkeys(t[:120] for t in topics))[:5]
    spots = [s for s in (k.read(ctx, "support/community/spotlights.json", []) or []) if isinstance(s, dict) and s.get("permission") == "granted" and not s.get("posted")]
    fmt = "text AMA" if n_members < threshold else "spotlight evening" if spots else "short call"
    dated = sorted(str(e.get("date", ""))[:10] for e in events if e.get("status") in ("proposed", "scheduled", "held") and str(e.get("date", ""))[:10])
    recent = [x for x in dated if x >= (today - timedelta(days=30)).isoformat()]
    pending = [e for e in events if e.get("status") in ("proposed", "scheduled") and str(e.get("date", ""))[:10] >= today.isoformat()]
    first = today + timedelta(days=8)
    day1, s1 = pick(first, (1, 2, 3), 19, 30)
    day2, s2 = pick(first, (5,), 11, 0)
    propose = not pending and not recent and day1
    lines = [f"# Event brief {today}", "", "## Why now",
             f"{n_members} active member(s) and {n_posts} post(s) in 30 days. The live-event threshold is {threshold} members, so the default is a {fmt}. One event a month at most; nothing is booked and nobody is invited by this job."]
    if pending:
        lines += ["", f"An event is already {pending[0].get('status')} for {pending[0].get('date')}. No new one is proposed."]
    elif recent:
        lines += ["", f"The last event was {recent[-1]}, so the next window opens after {(datetime.fromisoformat(recent[-1]).date() + timedelta(days=30)).isoformat()}. This month is skipped rather than filled."]
    topic = topics[0] if topics else "open questions"
    if propose:
        lines += ["", "## Two slots (Charlie picks)", f"1. {s1}", f"2. {s2 or s1}", "", "## Run sheet (relative to the slot you pick)",
                  f"- {day1 - timedelta(days=7)}: announce (T minus 7 days)", f"- {day1 - timedelta(days=1)}: reminder (T minus 1)", f"- {day1}: start, then close", f"- {day1 + timedelta(days=1)}: recap (T plus 1)",
                  "- Questions in advance: create a free Tally form and paste its link here; pre-fill the topics below.", "", "## Drafts"]
        ans = k.ask("Write three short posts for a small UK product community: an announcement, a reminder and a recap for an upcoming event. Each states what happens, when, how to join and what is free. Plain UK English, no hype, no exclamation marks. "
                    'Return JSON only: {"announcement": "...", "reminder": "...", "recap": "..."}\n' + f"FORMAT: {fmt}. SLOT: {s1}. HOW TO JOIN: {JOIN[fmt]}. TOPICS: {topics}. PRODUCT: {ctx['idea'].get('title', '')}")
        ans = ans if isinstance(ans, dict) else {}
        base = f"We are holding a {fmt} on {s1}. It is free. How to join: {JOIN[fmt]}. Topics so far: {', '.join(topics) or 'your questions'}."
        fallback = {"announcement": f"Announcement: {base} Add your question in advance using the form linked here.", "reminder": f"Reminder: tomorrow. {base}",
                    "recap": "Recap: thank you to everyone who took part. Answers to the questions we could not cover will go on the help page."}
        for key in ("announcement", "reminder", "recap"):
            text = str(ans.get(key) or "").replace(chr(33), ".").strip()
            lines += [f"### {key.title()}", text if text and len(text.split()) <= 120 else fallback[key], ""]
        events.append({"id": f"{day1}-{util.slugify(fmt)}", "date": day1.isoformat(), "format": fmt, "topic": topic, "attendance": 0, "questions": [], "status": "proposed"})
    held = [e for e in events if e.get("status") == "held" and isinstance(e.get("questions"), list) and e["questions"]]
    known = {str(g.get("question")) for g in gaps.get("gaps", []) if isinstance(g, dict)}
    new_q = [{"question": str(q)[:200], "url": "", "seen": util.today()} for e in held for q in e["questions"] if str(q)[:200] not in known]
    if new_q:
        gaps["gaps"] = list(gaps.get("gaps", [])) + new_q
        gaps.setdefault("updated", util.now())
        k.write(ctx, "support/community/faq-gaps.json", gaps)
        lines += ["", f"After a held event: {len(new_q)} unanswered question(s) added to faq-gaps.json."]
    lines += ["", "## Topics", *([f"- {t}" for t in topics] or ["- none yet: the FAQ and faq-gaps.json are empty"])]
    if spots:
        lines += ["", f"Granted spotlights waiting to be posted: {len(spots)}."]
    lines += ["", *[f"Note: {n}" for n in notes]]
    k.write(ctx, "support/community/event-brief.md", "\n".join(lines))
    k.write(ctx, "support/community/events.json", cfgs + events)
    return {"summary": (f"Event brief: {fmt} proposed for {day1} or {day2 or day1}" if propose else "Event brief: no event proposed this run") + f" ({n_members} active members, threshold {threshold}). Nothing booked.", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
