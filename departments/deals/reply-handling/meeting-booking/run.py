"""Meeting Booking: GitHub implementation of departments/deals/reply-handling/meeting-booking/SKILL.md.

Tracks every routed reply through offered, booked, held, no_show and cancelled in sell/meetings.json. Cal.com is
read only (slots and bookings, when CALCOM_API_KEY is set); otherwise times are proposals. Offers, reminders and
chasers are drafts under sell/drafts/ for Charlie to send. Nothing is sent or booked. Times are stored in UTC.
"""
import datetime as dt
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import dealkit as D  # noqa: E402
from foundry import jobkit as k  # noqa: E402

CAL = "https://api.cal.com/v1"
RECORD = "I would like to record the call for notes; tell me if you would rather I did not."
YES = re.compile(r"(happy|fine|ok|okay|no problem|yes|sure)\W.{0,30}record|record\w*\W.{0,30}(fine|ok|okay|no problem)", re.I)
NO = re.compile(r"(rather not|prefer not|do not|don.t|no)\W.{0,20}record|not record|no recording", re.I)
UTC = dt.timezone.utc


def cal_get(path, key, **params):
    try:
        r = requests.get(CAL + path, params=dict(params, apiKey=key), timeout=30)
        return r.json() if r.ok else None
    except Exception:  # noqa: BLE001
        return None


def slots(n, key):
    """n free slots (UTC), and whether Cal.com checked them."""
    types = ((cal_get("/event-types", key) or {}).get("event_types") or []) if key else []
    if types:
        start = dt.date.today() + dt.timedelta(days=1)
        data = cal_get("/slots", key, eventTypeId=types[0].get("id"), startTime=start.isoformat(), endTime=(start + dt.timedelta(days=7)).isoformat()) or {}
        days = [[x.get("time") for x in v if isinstance(x, dict)] for _, v in sorted((data.get("slots") or {}).items()) if isinstance(v, list)]
        picked = [d[0] for d in days if d][:n] or []
        picked += [t for d in days for t in d[1:]][:max(0, n - len(picked))]
        got = sorted(D.parse_dt(t) for t in picked if D.parse_dt(t))
        if got:
            return got[:n], True
    out, day = [], dt.date.today()
    while len(out) < n:
        day += dt.timedelta(days=1)
        if day.weekday() < 5:
            out.append(dt.datetime(day.year, day.month, day.day, (10, 14, 16)[len(out) % 3], tzinfo=D.UK).astimezone(UTC))
    return out, False


def uk(d):
    return d.astimezone(D.UK).strftime("%a %d %b, %H:%M UK time")


def working_days(since):
    d, n = D.parse_date(since), 0
    while d and d < dt.date.today():
        d += dt.timedelta(days=1)
        n += d.weekday() < 5
    return n


def offer(ctx, name, entry, row, n, intro, key):
    got, checked = slots(n, key)
    url = k.secret("CALCOM_BOOKING_URL")
    body = f"Hi {D.first_name(row.get('contact') or entry['attendee_email'])},\n\n{intro} " + " / ".join(uk(t) for t in got) + "." + (f" Or choose your own time: {url}" if url else "") + f"\n\n{RECORD}\n\n{D.sender(ctx)}"
    entry["offered_slots"] = [t.strftime("%Y-%m-%dT%H:%MZ") for t in got]
    entry[name] = D.draft(ctx, f"meeting-{name.replace('_draft', '')}-{entry['deal_id']}", {"to": entry["attendee_email"], "subject": "Times for a call", "calendar": "checked with Cal.com" if checked else "proposals, not checked against the calendar"}, body)


def main(ctx):
    gate = D.gate(ctx)
    if gate:
        return gate
    replies, meets = k.read(ctx, "sell/replies.json", []) or [], k.read(ctx, "sell/meetings.json", []) or []
    rows, sup, key = D.pipeline(ctx), D.suppressed(ctx), k.secret("CALCOM_API_KEY")
    by_id, lines, done = {r.get("id"): r for r in rows}, [], []
    seen = {m.get("deal_id") for m in meets}
    for r in replies:
        row = by_id.get(r.get("deal_id"))
        if r.get("status") == "routed" and row and r["deal_id"] not in seen and D.email_of(row.get("email")) not in sup and row.get("email"):
            e = {"deal_id": r["deal_id"], "start": "", "end": "", "attendee_email": row["email"].lower(), "join_url": "", "status": "offered", "consent": "unknown", "transcript": ""}
            offer(ctx, "offer_draft", e, row, 3, "Thanks for coming back to me. Three times for a call:", key)
            row.update(next_step="send call times", next_step_date=D.today(), updated=D.today())
            meets.append(e)
            done.append("offered " + r["deal_id"])
    bookings = (cal_get("/bookings", key) or {}).get("bookings") or [] if key else []
    for m in meets:
        row = by_id.get(m.get("deal_id"))
        for b in bookings:
            emails = [str(a.get("email", "")).lower() for a in (b.get("attendees") or []) if isinstance(a, dict)]
            if m.get("attendee_email") in emails and m["status"] in ("offered", "booked", "cancelled"):
                state = str(b.get("status", "")).lower()
                if "cancel" in state and m["status"] != "cancelled":
                    m["status"] = "cancelled"
                    done.append("cancelled " + m["deal_id"])
                elif "cancel" not in state and (m["status"] == "offered" or (b.get("startTime") and b["startTime"] != m["start"])):
                    m.update(status="booked", start=b.get("startTime", ""), end=b.get("endTime", ""), join_url=str((b.get("metadata") or {}).get("videoCallUrl", "")))
                    if row:
                        row.update(stage="meeting_booked" if row.get("stage") in ("new", "qualified") else row.get("stage"), next_step="take call", next_step_date=m["start"][:10], updated=D.today())
                    done.append("booked " + m["deal_id"])
                note = str(b.get("description") or "")
                if m["consent"] == "unknown":
                    m["consent"] = "no" if NO.search(note) else "yes" if YES.search(note) else "unknown"
        if m["consent"] == "unknown":
            said = " ".join(D.txt(r.get("summary"), 300) for r in replies if r.get("deal_id") == m.get("deal_id"))
            m["consent"] = "no" if NO.search(said) else "yes" if YES.search(said) else "unknown"
        start = D.parse_dt(m.get("start"))
        now = dt.datetime.now(UTC)
        if m["status"] == "booked" and start:
            if now <= start <= now + dt.timedelta(hours=24) and not m.get("reminder_draft"):
                m["reminder_draft"] = D.draft(ctx, f"meeting-reminder-{m['deal_id']}", {"to": m["attendee_email"], "subject": "Our call: " + uk(start)}, f"Hi {D.first_name(m['attendee_email'])},\n\nA reminder of our call on {uk(start)}. Join here: {m.get('join_url') or 'link to follow'}\n\n{D.sender(ctx)}")
                done.append("reminder " + m["deal_id"])
            if now > start + dt.timedelta(minutes=30) and not m.get("attendance_alert"):
                m["attendance_alert"] = D.today()
                lines.append(f"Set held or no_show for {m['deal_id']} ({m['attendee_email']}) in sell/meetings.json: the call was due {uk(start)}")
        chases = m.setdefault("chases", []) if m["status"] in ("no_show", "cancelled") else []
        row = row or {}
        if m["status"] == "no_show" and m["attendee_email"] not in sup:
            if not chases:
                offer(ctx, "chase_draft_1", m, row, 2, "Sorry we missed each other. Two new times:", key)
                chases.append(D.today())
                done.append("no-show chase " + m["deal_id"])
            elif len(chases) == 1 and working_days(chases[0]) >= 3:
                offer(ctx, "chase_draft_2", m, row, 2, "A last note on a call. Two times:", key)
                chases.append(D.today())
                row.update(stage="dormant", next_step_date=(dt.date.today() + dt.timedelta(days=30)).isoformat(), updated=D.today())
                done.append("final chase " + m["deal_id"])
        elif m["status"] == "cancelled" and not chases and m["attendee_email"] not in sup:
            offer(ctx, "cancel_draft", m, row, 2, "No problem about the change. Two new times:", key)
            chases.append(D.today())
            done.append("cancel offer " + m["deal_id"])
    if not done and not lines:
        return {"skipped": "no routed replies without a meeting, no bookings to match, no reminders due"}
    k.write(ctx, "sell/meetings.json", meets)
    if rows:
        D.save_pipeline(ctx, rows)
    D.alert(ctx, "meeting-booking", lines)
    return {"summary": f"{len(done)} meeting actions ({', '.join(done[:4])}); drafts under sell/drafts/, nothing sent." + ("" if key else " Cal.com skipped: no CALCOM_API_KEY, times are proposals.")}


if __name__ == "__main__":
    k.run(main)
