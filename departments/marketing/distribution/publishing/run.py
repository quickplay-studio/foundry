"""Publishing: GitHub implementation of departments/marketing/distribution/publishing/SKILL.md.

Builds the posting schedule only: launch/queue.json (every row approved:false), launch/queue.md (the pull-request
body with a manual checklist) and an untouched or empty launch/publish-log.json. Nothing is posted from here: no API
call, no upload, no message. A separate hourly workflow, after Charlie approves rows, would do the posting.
"""
import datetime as dt
import json
import re
from zoneinfo import ZoneInfo

from foundry import jobkit as k

try:
    UK = ZoneInfo("Europe/London")
except Exception:  # noqa: BLE001
    UK = dt.timezone.utc
DEFAULT_SLOTS = [(12, 0), (18, 30)]  # UK local time
METHODS = ("api", "buffer", "manual")


def slots_for(performance):
    """Best two posting hours (UTC) from performance.json, else the UK defaults."""
    rows = [r for r in (performance.get("patterns", []) if isinstance(performance, dict) else []) if isinstance(r, dict) and r.get("by") == "posting_hour" and str(r.get("group", "")).isdigit()]
    best = sorted(rows, key=lambda r: (-(r.get("median_signups") or 0), -(r.get("median_views") or 0)))[:2]
    if len(best) == 2 and (best[0].get("median_views") or best[0].get("median_signups")):
        return sorted((int(r["group"]), 0) for r in best), dt.timezone.utc, "best hours from performance.json"
    return DEFAULT_SLOTS, UK, "default 12:00 and 18:30 UK time"


def launch_day(ctx):
    plan = k.read(ctx, "plan.md", "") or ""
    for m in re.finditer(r"(\d{4}-\d{2}-\d{2})", "\n".join(l for l in plan.splitlines() if "launch" in l.lower())):
        try:
            d = dt.date.fromisoformat(m.group(1))
            if d >= dt.date.today():
                return d
        except ValueError:
            continue
    return dt.date.today() + dt.timedelta(days=1)


def main(ctx):
    folder = ctx["folder"]
    variants = []
    for p in sorted((folder / "launch/adapted").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(d, dict) and d.get("post_id"):
            variants += [{**v, "post_id": d["post_id"], "source": f"launch/adapted/{p.name}"} for v in d.get("variants", []) if isinstance(v, dict) and v.get("platform")]
    if not variants:
        return {"skipped": "no variants in launch/adapted: run cross-platform-adaptation first"}
    queue = [r for r in (k.read(ctx, "launch/queue.json", []) or []) if isinstance(r, dict)]
    have = {(r.get("post_id"), r.get("platform"), r.get("format")) for r in queue}
    chan = k.read(ctx, "launch/channels.json", {}) or {}
    chan = chan if isinstance(chan, dict) else {}
    proof = {r.get("post_id") for r in (k.read(ctx, "launch/scripts/index.json", []) or []) if isinstance(r, dict) and (r.get("needs_proof") or 0) > 0}
    slots, tz, how = slots_for(k.read(ctx, "launch/insights/performance.json", {}) or {})
    posts = list(dict.fromkeys(v["post_id"] for v in variants))
    planned = [p for p in posts if any((v["post_id"], v["platform"], v.get("format")) not in have for v in variants if v["post_id"] == p)]
    start = launch_day(ctx)
    last, per_day = {}, {}
    for r in queue:
        try:
            due = dt.datetime.fromisoformat(str(r.get("due")).replace("Z", "+00:00"))
            last[r["platform"]] = max(last.get(r["platform"], due), due)
            per_day[(r["platform"], due.date())] = per_day.get((r["platform"], due.date()), 0) + 1
        except (ValueError, KeyError):
            continue
    added, ids = 0, {p: i for i, p in enumerate(planned[:10])}  # ten organic posts across the first two weeks
    for v in variants:
        key = (v["post_id"], v["platform"], v.get("format"))
        if key in have or v["post_id"] not in ids:
            continue
        p = v["platform"]
        method = str((chan.get(p) or {}).get("method", "manual")) if isinstance(chan.get(p), dict) else "manual"
        method = method if method in METHODS else "manual"
        if p == "tiktok" and method == "api" and not (chan.get("tiktok") or {}).get("audited"):
            method = "manual"  # unaudited TikTok apps can only post privately
        blocked = "[needs proof]" in v.get("text", "") or v["post_id"] in proof
        day = start + dt.timedelta(days=int(ids[v["post_id"]] * 14 / 10))
        due = None
        for offset in range(0, 30):
            d = day + dt.timedelta(days=offset)
            if per_day.get((p, d), 0) >= 2:
                continue
            for h, m in slots:
                cand = dt.datetime.combine(d, dt.time(h, m), tzinfo=tz).astimezone(dt.timezone.utc)
                if p not in last or cand >= last[p] + dt.timedelta(hours=4):
                    due = cand
                    break
            if due:
                per_day[(p, due.date())] = per_day.get((p, due.date()), 0) + 1
                last[p] = due
                break
        queue.append({"post_id": v["post_id"], "platform": p, "due": due.strftime("%Y-%m-%dT%H:%M:%SZ") if due else "", "approved": False, "status": "blocked" if blocked else "queued",
                      "format": v.get("format", ""), "method": method, "media": v.get("media", ""), "source": v["source"], **({"reason": "needs proof upstream"} if blocked else {})})
        added += 1
    if not added and not queue:
        return {"skipped": "nothing to schedule"}
    k.write(ctx, "launch/queue.json", queue)
    if not (folder / "launch/publish-log.json").exists():
        k.write(ctx, "launch/publish-log.json", [])
    text = {(v["post_id"], v["platform"], v.get("format")): v.get("text", "") for v in variants}
    md = ["# Publishing queue", "", f"Schedule: {how}. Nothing posts until Charlie sets `approved` to true on a row, or merges this pull request with every row approved. Rows marked blocked carry a `[needs proof]` line upstream and never post.", "",
          "| Due (UTC) | Post | Platform | Format | Method | Status | Approved |", "|---|---|---|---|---|---|---|"]
    md += [f"| {r['due'] or 'unscheduled'} | {r['post_id']} | {r['platform']} | {r.get('format', '')} | {r.get('method', '')} | {r['status']} | {'yes' if r['approved'] else 'no'} |" for r in sorted(queue, key=lambda r: r.get("due", ""))]
    md += ["", "## Manual posting checklist"]
    md += [x for r in queue if r.get("method") == "manual" and r["status"] == "queued" for x in (f"- [ ] {r['post_id']} on {r['platform']} ({r.get('format', '')}) at {r['due']}", f"  - Media: {r.get('media') or 'none'}", "  - Text:", *[f"    > {l}" for l in text.get((r["post_id"], r["platform"], r.get("format")), "").splitlines()])] or ["- none"]
    k.write(ctx, "launch/queue.md", "\n".join(md))
    return {"summary": f"{added} new rows queued ({len(queue)} in total), all unapproved. Nothing was posted. Schedule: {how}.", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
