"""Meeting Follow-Ups: GitHub implementation of departments/operations/client-comms/meeting-follow-ups/SKILL.md.

For each processed meeting record with no recap it keeps only committed actions (a verb, a named
attendee or "I" or "we" with a known speaker, and a quote found word for word in the transcript),
resolves owners and dates only from what was said, merges into actions.json and drafts a recap of
20 lines at most. Code only, no model. No pull request, issue or comment is opened from here.
"""
import datetime as dt
import json
import re

from foundry import jobkit as k, util

VERBS = set("send share review update draft check book call email write prepare schedule confirm fix build finish deliver follow open close add set create ask tell make run test get "
            "find arrange introduce sort push publish post order buy research look talk speak ping circulate chase raise file submit sign upload cancel move merge deploy ship list collect "
            "gather compile define plan propose present invite remind reply respond provide finalise complete handle take put bring pull record document clean migrate".split())
FIRST = re.compile(r"\b(i will|i'll|i can|i am going to|i'm going to|we will|we'll|we are going to|we'll)\b", re.I)
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
NUM = {"a": 1, "one": 1, "two": 2, "three": 3, "four": 4}


def norm(text):
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def has_verb(text):
    return any(w in VERBS or re.sub(r"(ing|ed|es|s)$", "", w) in VERBS for w in re.findall(r"[a-z']+", text.lower()))


def resolve_due(phrase, date):
    """An ISO date from what was said, relative to the meeting date; '' when no date was said."""
    p, base = phrase.lower(), dt.date.fromisoformat(date)
    iso = re.search(r"\d{4}-\d{2}-\d{2}", p)
    if iso:
        return iso.group(0)
    if "tomorrow" in p:
        return (base + dt.timedelta(days=1)).isoformat()
    if re.search(r"\btoday\b", p):
        return date
    if "next week" in p:
        return (base + dt.timedelta(days=7)).isoformat()
    m = re.search(r"in (\d+|a|one|two|three|four) (day|week)s?", p)
    if m:
        n = int(m.group(1)) if m.group(1).isdigit() else NUM[m.group(1)]
        return (base + dt.timedelta(days=n * (7 if m.group(2) == "week" else 1))).isoformat()
    if re.search(r"end of (the )?month", p):
        nxt = (base.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
        return (nxt - dt.timedelta(days=1)).isoformat()
    if re.search(r"end of (the )?week", p):
        return (base + dt.timedelta(days=(4 - base.weekday()) % 7)).isoformat()
    for i, d in enumerate(DAYS):
        if d in p:
            return (base + dt.timedelta(days=(i - base.weekday()) % 7 or 7)).isoformat()
    return ""


def transcript(ctx, rec):
    raw = ctx["folder"] / "meetings" / "raw" / str(rec.get("source", ""))
    if not raw.is_file():
        return ""
    text = "\n".join(ln for ln in raw.read_text(encoding="utf-8", errors="replace").splitlines() if "-->" not in ln and not ln.strip().isdigit() and ln.strip() != "WEBVTT")
    return norm(re.sub(r"<[^>]+>", "", text))


def triage(a, rec, evidence, people):
    """(action dict or None, reason when dropped)."""
    text, quote = str(a.get("text", "")).strip(), str(a.get("quote", "")).strip()
    hint = str(a.get("owner_hint", "")).strip()
    if not text or not quote:
        return None, "no quote"
    if evidence and norm(quote) not in evidence:
        return None, "quote not in the transcript"
    if not has_verb(text + " " + quote):
        return None, "no verb"
    names = [p for p in people if re.search(r"\b" + re.escape(p.split()[0]) + r"\b", quote, re.I)]
    lead = [p for p in names if re.match(re.escape(p.split()[0]) + r"\b", quote, re.I)]
    named = names[0] if len(names) == 1 else lead[0] if lead else ""  # several names and none leads: no owner
    speaker = next((p for p in people if hint and p.lower() == hint.lower()), "")
    first = FIRST.search(quote)
    if not (names or (first and speaker)):
        return None, "nobody clearly committed"
    owner = named or (speaker if first and re.match(r"(i will|i'll|i can|i am|i'm)", first.group(0), re.I) else "") or "unassigned"
    return {"text": text, "owner": owner, "due": resolve_due(quote + " " + str(a.get("due_hint", "")), str(rec["date"]))}, ""


def recap(rec, taken, dropped, note):
    for dn, an, qn, nn in [(4, 6, 3, 3), (3, 5, 2, 2), (2, 4, 2, 1), (2, 3, 1, 1), (1, 2, 1, 1), (1, 1, 1, 0)]:
        lines = [f"# Recap: {rec['title']} ({rec['date']})"] + ([note] if note else []) + ["Decisions:"]
        decisions = [f"- {d.get('text', '')}" for d in rec.get("decisions", []) if isinstance(d, dict)][:dn]
        lines += decisions or ["- None."]
        lines += ["Actions:", "| Owner | Action | Due |", "|---|---|---|"]
        lines += [f"| {t['owner']} | {t['text']} | {t['due'] or 'not said'} |" for t in taken[:an]] or ["| none | none | none |"]
        lines += ["Open questions:"] + ([f"- {q}" for q in rec.get("open_questions", [])][:qn] or ["- None."])
        lines += ["Not taken as actions:"] + ([f"- {t} ({why})" for t, why in dropped[:nn]] or ["- None."])
        if len(lines) <= 20:
            break
    return "\n".join(lines[:20])


def main(ctx):
    mdir = ctx["folder"] / "meetings"
    recs = [p for p in sorted(mdir.glob("*.json")) if p.name != "index.json" and not (mdir / f"{p.stem}-recap.md").exists()] if mdir.is_dir() else []
    actions = k.read(ctx, "actions.json", None)
    actions = [a for a in actions if isinstance(a, dict)] if isinstance(actions, list) else []
    people_map = k.read(ctx, "people.json", {}) or {}
    today, made, new_n = util.today(), [], 0
    for path in recs[:10]:
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
            dt.date.fromisoformat(str(rec["date"]))
            rec["title"] = str(rec.get("title") or path.stem)
        except (ValueError, KeyError, TypeError):
            continue
        acts = [a for a in rec.get("actions") or [] if isinstance(a, dict)]
        people = [str(a) for a in rec.get("attendees") or []] or sorted({str(a.get("owner_hint")) for a in acts if a.get("owner_hint")})
        evidence, taken, dropped = transcript(ctx, rec), [], []
        for a in acts:
            item, why = triage(a, rec, evidence, people)
            if not item:
                dropped.append((str(a.get("text", "") or "unnamed")[:60], why))
            elif not any(norm(item["text"]) == norm(t["text"]) for t in taken):
                taken.append(item)
        source = f"meetings/{path.name}"
        for t in taken:
            match = next((a for a in actions if a.get("status") == "open" and norm(a.get("text")) == norm(t["text"])), None)
            if match:
                match["source"] = source
                continue
            top = max([int(m.group(1)) for a in actions for m in [re.match(r"A-(\d+)", str(a.get("id", "")))] if m] or [0])
            actions.append({"id": f"A-{top + 1:03d}", "text": t["text"], "owner": t["owner"], "due": t["due"], "source": source, "status": "open", "created": today})
            new_n += 1
        note = "Heuristic route: this transcript was not cleared for models, so check every owner and date." if rec.get("heuristic") or rec.get("share_with_model") is False else ""
        shown = [dict(t, owner=(f"{t['owner']} (@{people_map[t['owner']]})" if isinstance(people_map, dict) and people_map.get(t["owner"]) else t["owner"])) for t in taken]
        k.write(ctx, f"meetings/{path.stem}-recap.md", recap(rec, shown, dropped, note))
        made.append(path.stem)
    if not made:
        return {"skipped": "no processed meeting records without a recap"}
    k.write(ctx, "actions.json", actions)
    overdue = [a["id"] for a in actions if a.get("status") == "open" and a.get("due") and str(a["due"]) < today]
    return {"summary": f"{len(made)} recaps drafted, {new_n} new actions, {len(overdue)} overdue (no pull request or issues opened from here)" + (f": {', '.join(overdue[:5])}" if overdue else ""),
            "flag": "caution" if overdue else "ok"}


if __name__ == "__main__":
    k.run(main)
