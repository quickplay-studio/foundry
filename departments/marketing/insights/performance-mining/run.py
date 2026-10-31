"""Performance Mining: GitHub implementation of departments/marketing/insights/performance-mining/SKILL.md.

Ranks our own posts by sign-ups, views against the median and engagement, groups what worked and asks the
free model which to redo or drop (from a table only, never raw comments). Steps 1 to 5 are arithmetic, so the
report is useful with every model down.
"""
import csv
import datetime as dt
import io
import re
import statistics

from foundry import jobkit as k


def tidy(text):
    return re.sub(r"\s+", " ", re.sub(r"\s*[\u2013\u2014]\s*", ", ", re.sub(r"!+", ".", str(text)).replace(" - ", ", "))).strip()


def when(value):
    try:
        d = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def med(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else 0


def band(seconds):
    return "unknown" if not seconds else "under 20 s" if seconds < 20 else "20 to 45 s" if seconds <= 45 else "over 45 s"


def fetch_metrics(rows, skipped):
    raw, stats = {}, {}
    key, meta = k.secret("YOUTUBE_API_KEY"), k.secret("META_ACCESS_TOKEN")
    ids = {m.group(1): r["post_id"] for r in rows for m in [re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", str(r.get("url", "")))] if m}
    if ids and key:
        for i in range(0, len(ids), 50):
            try:
                data = k.requests.get("https://www.googleapis.com/youtube/v3/videos", params={"part": "statistics", "id": ",".join(list(ids)[i:i + 50]), "key": key}, timeout=20).json()
                raw.setdefault("youtube", []).append(data)
                for v in data.get("items", []):
                    s = v.get("statistics", {})
                    stats[ids[v["id"]]] = {"views": int(s.get("viewCount", 0)), "likes": int(s.get("likeCount", 0)), "comments": int(s.get("commentCount", 0)), "shares": None, "saves": None}
            except Exception as exc:  # noqa: BLE001
                skipped.append(f"youtube: {type(exc).__name__}")
    elif ids:
        skipped.append("youtube: YOUTUBE_API_KEY missing")
    for r in rows:  # Instagram and Facebook need the Graph media id in the log row
        if r.get("media_id") and meta and r.get("platform") in ("instagram", "facebook"):
            fields = "like_count,comments_count" if r["platform"] == "instagram" else "shares,reactions.summary(true),comments.summary(true)"
            try:
                d = k.requests.get(f"https://graph.facebook.com/{r['media_id']}", params={"fields": fields, "access_token": meta}, timeout=20).json()
                raw.setdefault("meta", []).append({k_: v for k_, v in d.items() if k_ != "access_token"})
                likes = d.get("like_count") if r["platform"] == "instagram" else d.get("reactions", {}).get("summary", {}).get("total_count")
                stats[r["post_id"]] = {"views": None, "likes": likes, "comments": d.get("comments_count", d.get("comments", {}).get("summary", {}).get("total_count")), "shares": (d.get("shares") or {}).get("count"), "saves": None}
            except Exception as exc:  # noqa: BLE001
                skipped.append(f"meta {r['post_id']}: {type(exc).__name__}")
        elif r.get("platform") in ("instagram", "facebook") and not meta:
            skipped.append("meta: META_ACCESS_TOKEN missing") if "meta: META_ACCESS_TOKEN missing" not in skipped else None
    return stats, raw


def main(ctx):
    idea, brain, skipped, today = ctx["idea"], ctx["brain"], [], dt.date.today().isoformat()
    log = k.read(ctx, "launch/publish-log.json")
    rows = [r for r in (log.get("log", log.get("posts", [])) if isinstance(log, dict) else log or []) if isinstance(r, dict) and r.get("post_id")]
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=48)
    rows = [r for r in rows if (when(r.get("published")) or cutoff) < cutoff and str(r.get("status", "posted")) in ("posted", "published", "manual", "done")]
    if not rows:
        return {"skipped": "no posts old enough (48 hours or more)"}
    stats, raw = fetch_metrics(rows, skipped)
    vid = k.read(ctx, "launch/inputs/vidiq.json", []) or []  # Charlie's export fills what the APIs did not
    for v in vid if isinstance(vid, list) else []:
        pid = v.get("post_id") or next((r["post_id"] for r in rows if v.get("url") and r.get("url") == v["url"]), None)
        if pid and pid not in stats:
            stats[pid] = {x: v.get(x) for x in ("views", "likes", "comments", "shares", "saves")}
    if raw:
        k.write(ctx, f"launch/inputs/metrics-{today}.json", raw)
    signups = {}
    for r in csv.DictReader(io.StringIO(k.read(ctx, "launch/inputs/signups.csv", "") or "")):
        signups[r.get("utm_content", "")] = signups.get(r.get("utm_content", ""), 0) + 1
    hooks = {h.get("id"): h.get("pattern", "") for h in (k.read(ctx, "launch/hooks.json", {}) or {}).get("hooks", []) if isinstance(h, dict)}
    posts = []
    for r in rows:
        s = stats.get(r["post_id"])
        if s is None:
            skipped.append(f"{r['post_id']}: no metrics from any source")
            continue
        script = k.read(ctx, f"launch/scripts/{r['post_id']}.json", {}) or {}
        d = when(r.get("published"))
        eng = sum(s.get(x) or 0 for x in ("likes", "comments", "shares", "saves"))
        posts.append({"post_id": r["post_id"], "platform": r.get("platform", ""), "format": r.get("format", "video"), "url": r.get("url", ""), "views": s.get("views"), "engagement_count": eng,
                      "signups": signups.get(r["post_id"], 0), "hook_pattern": hooks.get(r.get("hook_id"), "unknown"), "length_band": band(script.get("duration_s") if isinstance(script, dict) else None), "hour": d.strftime("%H") if d else "unknown"})
    if not posts:
        return {"skipped": "no metrics for any post: " + "; ".join(skipped)[:150]}
    for p in posts:
        m = med([q["views"] for q in posts if q["platform"] == p["platform"] and q["format"] == p["format"]])
        p["vs_median"] = round(p["views"] / m, 2) if p["views"] is not None and m else None
        p["engagement"] = round(p["engagement_count"] / p["views"], 4) if p["views"] else None
    posts.sort(key=lambda p: (-p["signups"], -(p["vs_median"] or 0), -(p["engagement"] or 0)))
    for n, p in enumerate(posts, 1):
        p["rank"] = n
    patterns = []
    for by, field in (("hook_pattern", "hook_pattern"), ("format", "format"), ("length_band", "length_band"), ("posting_hour", "hour")):
        for g in sorted({p[field] for p in posts}):
            members = [p for p in posts if p[field] == g]
            patterns.append({"by": by, "group": g, "count": len(members), "median_views": med([p["views"] for p in members]), "median_signups": med([p["signups"] for p in members])})
    table = "\n".join(f"{p['post_id']} {p['platform']} {p['format']} views={p['views']} vs_median={p['vs_median']} engagement={p['engagement']} signups={p['signups']} pattern={p['hook_pattern']} hour={p['hour']}" for p in posts)
    answer = k.ask('Return JSON only: {"redo": [{"post_id": "...", "change": "...", "why": "..."}], "drop": [{"post_id": "...", "why": "..."}]}. Up to five redo from the top three posts, up to three drop from the bottom three. Worked means sign-ups first, views second.\n\nTABLE\n' + table)
    top3, bottom3 = {p["post_id"] for p in posts[:3]}, {p["post_id"] for p in posts[-3:]}
    redo = [{"post_id": r["post_id"], "change": tidy(r.get("change", "")), "why": tidy(r.get("why", ""))} for r in (answer.get("redo") if isinstance(answer, dict) and isinstance(answer.get("redo"), list) else []) if isinstance(r, dict) and r.get("post_id") in top3][:5]
    drop = [{"post_id": r["post_id"], "why": tidy(r.get("why", ""))} for r in (answer.get("drop") if isinstance(answer, dict) and isinstance(answer.get("drop"), list) else []) if isinstance(r, dict) and r.get("post_id") in bottom3][:3]
    small = len(posts) < 10
    best, worst = posts[0], posts[-1]
    win = next((p for p in sorted(patterns, key=lambda p: (-p["median_signups"], -p["median_views"])) if p["by"] == "hook_pattern" and p["group"] != "unknown"), None)
    summary = [f"Best post: {best['post_id']} on {best['platform']} with {best['signups']} sign-ups and {best['views']} views.", f"Worst post: {worst['post_id']} on {worst['platform']} with {worst['signups']} sign-ups.",
               f"One pattern: {win['group']} hooks lead on median sign-ups ({win['median_signups']})." if win else "One pattern: not enough hook data yet."]
    md = [f"# Performance: {tidy(idea.get('title', ctx['slug']))}", f"{today}. {len(posts)} posts." + (" The sample is small, so read the ranking loosely." if small else ""), "", "## Summary"] + [f"- {s}" for s in summary]
    md += ["", "## Ranked posts", "| Rank | Platform | URL | Views | vs median | Engagement | Sign-ups |", "|---|---|---|---|---|---|---|"]
    md += [f"| {p['rank']} | {p['platform']} | {p['url']} | {p['views']} | {p['vs_median']} | {p['engagement']} | {p['signups']} |" for p in posts]
    md += ["", "## Patterns", "| By | Group | Count | Median views | Median sign-ups |", "|---|---|---|---|---|"] + [f"| {p['by']} | {p['group']} | {p['count']} | {p['median_views']} | {p['median_signups']} |" for p in patterns]
    md += ["", "## Redo"] + ([f"- {r['post_id']}: {r['change']} ({r['why']})" for r in redo] or ["- not written: no model answered"]) + ["", "## Drop"] + ([f"- {r['post_id']}: {r['why']}" for r in drop] or ["- none"])
    if skipped:
        md += ["", "## Skipped"] + [f"- {s}" for s in skipped]
    k.write(ctx, "launch/insights/performance.md", "\n".join(md))
    k.write(ctx, "launch/insights/performance.json", {"date": today, "sample_small": small, "summary": summary, "ranked": posts, "patterns": patterns, "redo": redo, "drop": drop, "skipped": skipped})
    return {"summary": f"{len(posts)} posts ranked; best {best['post_id']} with {best['signups']} sign-ups. Skipped: {len(skipped)}.", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
