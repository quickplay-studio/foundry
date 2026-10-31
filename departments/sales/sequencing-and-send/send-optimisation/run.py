"""Send Optimisation: GitHub implementation of departments/sales/sequencing-and-send/send-optimisation/SKILL.md.

Writes sell/send-windows.json: default windows (Tue to Thu, 08:00 to 10:00 and 13:00 to 15:00, recipient
local time, UK recipients on Europe/London), UK bank holidays from gov.uk and Christmas week skipped, pacing
(2 to 6 minute gaps, one send a day per recipient domain) and the effective daily cap, never above the
deliverability cap. Under 100 sends only the defaults and the holiday skip apply. After that a window
moves only if the better two-hour bucket has 30 or more sends and at least twice the reply rate. Live
campaigns in campaigns.json get the window and cap with a changelog reason. Country is not held on
leads, so every recipient is treated as GB. The weekly line is kept in send-windows.json.
"""
import csv
import datetime as dt
import io
import math

import requests

from foundry import jobkit as k

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DEFAULT = {"days": ["Tue", "Wed", "Thu"], "windows": ["08:00-10:00", "13:00-15:00"]}
AVG_GAP = 4  # minutes, the middle of the 2 to 6 minute random gap


def b2b(ctx):
    audit = k.read(ctx, "audit.json", {}) or {}
    return "b2b" in (str(ctx["idea"].get("business_model", "")).lower(), str(audit.get("business_model", "")).lower())


def table(ctx, rel):
    return list(csv.DictReader(io.StringIO(k.read(ctx, rel, "") or "")))


def holidays():
    try:
        d = requests.get("https://www.gov.uk/bank-holidays.json", timeout=15).json()
        return sorted(e["date"] for e in d["england-and-wales"]["events"])
    except Exception:  # noqa: BLE001
        return []


def bounds(window):
    return tuple(int(x[:2]) * 60 + int(x[3:5]) for x in window.split("-"))


def span(days):
    idx = sorted(DAYS.index(d) for d in days if d in DAYS)
    return f"{DAYS[idx[0]]}-{DAYS[idx[-1]]}" if len(idx) > 1 and idx[-1] - idx[0] + 1 == len(idx) else ",".join(DAYS[i] for i in idx)


def local(stamp):
    try:
        t = dt.datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return None
    try:
        from zoneinfo import ZoneInfo
        return t.astimezone(ZoneInfo("Europe/London"))
    except Exception:  # noqa: BLE001
        return t


def rate(b):
    return b[1] / b[0] if b[0] else 0.0


def main(ctx):
    if not b2b(ctx):
        return {"skipped": "no business buyer"}
    today = dt.date.today()
    sent = sorted((s for s in table(ctx, "sell/sent.csv") if s.get("channel", "email") in ("email", "")), key=lambda s: s.get("sent_at", ""))
    good = set()  # lead and thread ids of positive or neutral replies
    for r in table(ctx, "sell/replies.csv") + [r for r in (k.read(ctx, "sell/replies.json", []) or []) if isinstance(r, dict)]:
        if str(r.get("label") or r.get("classification") or r.get("class") or "reply").lower() not in ("never", "unsubscribe"):
            good |= {str(r.get("lead_id", "")), str(r.get("thread_id", ""))} - {""}

    def replied(s):
        return s.get("lead_id") in good or s.get("thread_id") in good

    deliv, camps = k.read(ctx, "sell/deliverability.json", {}) or {}, k.read(ctx, "sell/campaigns.json", {}) or {}
    prior = k.read(ctx, "sell/send-windows.json", {}) or {}
    log = [c for c in prior.get("changelog", []) if isinstance(c, dict)] if isinstance(prior, dict) else []
    dcap = int(deliv["daily_cap"]) if isinstance(deliv, dict) and isinstance(deliv.get("daily_cap"), (int, float)) else 0
    bounce = max([float(m.get("bounce_rate") or 0) for m in (deliv.get("mailboxes") or []) if isinstance(m, dict)] or [0.0]) if isinstance(deliv, dict) else 0.0
    gb = {**DEFAULT, "timezone": "Europe/London"}
    if len(sent) >= 100:  # tune from replies only once there is data
        inside, outside = [0, 0], {}
        for s in sent:
            t = local(s.get("sent_at", ""))
            if not t:
                continue
            mins = t.hour * 60 + t.minute
            in_default = DAYS[t.weekday()] in DEFAULT["days"] and any(a <= mins < b for a, b in map(bounds, DEFAULT["windows"]))
            b = inside if in_default else outside.setdefault((DAYS[t.weekday()], f"{t.hour // 2 * 2:02d}:00-{t.hour // 2 * 2 + 2:02d}:00"), [0, 0])
            b[0] += 1
            b[1] += bool(replied(s))
        base = rate(inside)
        best = max(((key, b) for key, b in outside.items() if b[0] >= 30), key=lambda kb: rate(kb[1]), default=None)
        if best and rate(best[1]) > 0 and rate(best[1]) >= 2 * base:
            gb = {"days": sorted(set(DEFAULT["days"]) | {best[0][0]}, key=DAYS.index), "windows": [best[0][1], DEFAULT["windows"][0]], "timezone": "Europe/London"}
            log.append({"date": today.isoformat(), "change": f"GB window moved to {best[0][0]} {best[0][1]}", "reason": f"{best[1][0]} sends at {rate(best[1]):.0%} reply rate against {base:.0%} in the default windows"})
    capacity = sum(bounds(w)[1] - bounds(w)[0] for w in gb["windows"]) // AVG_GAP
    hol = [d for d in holidays() if today.isoformat() <= d <= (today + dt.timedelta(days=400)).isoformat()]
    skip = sorted(set(hol + [f"{today.year}-12-{d}" for d in range(24, 32)]))  # Christmas week
    falling = len(sent) >= 100 and sum(map(replied, sent[-50:])) < sum(map(replied, sent[-100:-50]))
    window_text = f"{span(gb['days'])} {' and '.join(gb['windows'])} Europe/London"
    touched = 0
    for c in camps.get("campaigns", []) if isinstance(camps, dict) else []:
        if not isinstance(c, dict) or c.get("status") != "live":
            continue
        cap = int(c.get("daily_cap") or 0)
        eff = min(dcap, cap or dcap, capacity)  # never above the deliverability cap
        raised = [e["date"] for e in log if str(c.get("id")) in str(e.get("change", "")) and "raised" in str(e.get("change", ""))]
        week_ok = not raised or (today - dt.date.fromisoformat(max(raised))).days >= 7
        if len(sent) >= 100 and bounce < 0.02 and not falling and week_ok and eff < min(dcap, capacity):
            new = min(dcap, capacity, math.ceil(max(eff, 1) * 1.2))  # one 20 percent step a week
            if new > eff:
                log.append({"date": today.isoformat(), "change": f"{c.get('id')} daily_cap raised {eff} to {new}", "reason": f"bounce rate {bounce:.1%} under 2 percent and replies not falling"})
                eff = new
        if c.get("daily_cap") != eff or c.get("window") != window_text:
            log.append({"date": today.isoformat(), "change": f"{c.get('id')} window and cap set ({window_text}, cap {eff})", "reason": "send-optimisation windows and pace; cap never above the deliverability cap"})
            c["daily_cap"], c["window"], touched = eff, window_text, touched + 1
    if touched:
        k.write(ctx, "sell/campaigns.json", camps)
    week = sent[-50:]
    got = sum(map(replied, week))
    k.write(ctx, "sell/send-windows.json", {
        "updated": today.isoformat(), "default": DEFAULT, "by_region": {"GB": gb}, "skip_dates": skip,
        "pace": {"gap_minutes": [2, 6], "max_sends_per_recipient_domain_per_day": 1, "capacity_per_day": capacity, "deliverability_cap": dcap},
        "weekly": {"week": "%d-W%02d" % today.isocalendar()[:2], "sends": len(week), "replies": got, "reply_rate": round(got / len(week), 3) if week else 0, "bounce_rate": bounce},
        "changelog": log[-40:]})
    note = "" if len(sent) >= 100 else f" Only {len(sent)} sends so far: defaults and holiday skip only."
    return {"summary": f"Send windows: {window_text}, capacity {capacity} a day, deliverability cap {dcap}, {len(hol)} bank holidays skipped, {touched} live campaigns updated.{note}" + ("" if hol else " Bank holiday feed unreachable."), "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
