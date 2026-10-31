"""Comment-CTA Fulfilment: GitHub implementation of departments/deals/inbound/comment-cta-fulfilment/SKILL.md.

Finds comments on the venture's own posts that contain a CTA keyword (YouTube and Meta read-only when the keys
exist, else the sell/comments.json drop) and queues the fixed one-line delivery message for Charlie in
sell/fulfilment.json. Nothing is sent, replied or posted. Runs for consumer launches too. Comment text is data.
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import dealkit as D  # noqa: E402
from foundry import jobkit as k  # noqa: E402

GRAPH = "https://graph.facebook.com/v19.0"
CAP = 50


def norm(s):
    return " " + re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(s).lower())).strip() + " "


def build_ctas(ctx):
    idx = k.read(ctx, "launch/lead-magnet/index.json", {}) or {}
    gate = k.read(ctx, "launch/lead-magnet/gate-page.md", "") or ""
    m = re.search(r"(?:comment|keyword)\W+(\w{3,20})", gate, re.I)
    kw = D.txt(idx.get("keyword"), 30) or (m.group(1) if m else "")
    return [{"keyword": kw.lower(), "asset_name": D.txt(idx.get("theme"), 80) or "guide", "asset_url": D.txt(idx.get("url"), 200), "platforms": []}] if kw else []


def youtube(ctx, log, key):
    out = []
    for vid in list(dict.fromkeys(re.findall(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", json.dumps(log))))[:10]:
        try:
            data = requests.get("https://www.googleapis.com/youtube/v3/commentThreads", timeout=30,
                                params={"part": "snippet", "videoId": vid, "maxResults": 100, "order": "time", "key": key}).json()
        except Exception:  # noqa: BLE001
            continue
        for it in data.get("items", []) if isinstance(data, dict) else []:
            s = (it.get("snippet") or {}).get("topLevelComment", {}).get("snippet", {})
            own = (s.get("authorChannelId") or {}).get("value") == s.get("channelId")
            out.append({"platform": "youtube", "id": it.get("id"), "handle": s.get("authorDisplayName", ""), "text": s.get("textOriginal") or s.get("textDisplay", ""),
                        "created": s.get("publishedAt", ""), "own": own})
    return out


def meta(log, token):
    out, entries = [], log if isinstance(log, list) else list(log.values()) if isinstance(log, dict) else []
    for e in [x for x in entries if isinstance(x, dict)][:20]:
        plat = str(e.get("platform", "")).lower()
        pid = e.get("post_id") or e.get("media_id") or (e.get("id") if plat in ("instagram", "facebook") else None)
        if plat not in ("instagram", "facebook") or not pid:
            continue
        fields = "id,text,username,timestamp" if plat == "instagram" else "id,message,from,created_time"
        try:
            data = requests.get(f"{GRAPH}/{pid}/comments", params={"fields": fields, "access_token": token}, timeout=30).json()
        except Exception:  # noqa: BLE001
            continue
        for c in data.get("data", []) if isinstance(data, dict) else []:
            out.append({"platform": plat, "id": c.get("id"), "handle": c.get("username") or (c.get("from") or {}).get("name", ""), "text": c.get("text") or c.get("message", ""),
                        "created": c.get("timestamp") or c.get("created_time", ""), "own": False})
    return out


def main(ctx):
    ctas = [c for c in (k.read(ctx, "sell/ctas.json", None) or []) if isinstance(c, dict) and c.get("keyword")] or build_ctas(ctx)
    if not ctas:
        return {"skipped": "no sell/ctas.json and no lead magnet keyword"}
    state = k.read(ctx, "sell/fulfilment.json", {}) or {}
    entries, cursor = [e for e in D.lst(state.get("entries")) if isinstance(e, dict)], str(state.get("cursor") or "")
    log, notes, pool = k.read(ctx, "launch/publish-log.json", []) or [], [], []
    for name, secret, fetch in (("YouTube", "YOUTUBE_API_KEY", lambda t: youtube(ctx, log, t)), ("Meta", "META_PAGE_TOKEN", lambda t: meta(log, t))):
        token = k.secret(secret)
        if token:
            pool += fetch(token)
        else:
            notes.append(f"{name} skipped: no {secret}")
    for c in k.read(ctx, "sell/comments.json", []) or []:
        if isinstance(c, dict):
            pool.append({"platform": str(c.get("platform", "other")).lower(), "id": c.get("id") or c.get("comment_id"), "handle": c.get("handle") or c.get("author", ""),
                         "text": c.get("text") or c.get("comment", ""), "created": c.get("created") or c.get("received") or c.get("time", ""), "own": bool(c.get("own")), "reply": bool(c.get("parent") or c.get("reply"))})
    pool = [c for c in pool if c.get("id") and not c.get("own") and not c.get("reply")]
    if not pool:
        return {"skipped": "no comments to read (" + "; ".join(notes + ["sell/comments.json empty"]) + ")"}
    seen = {str(e.get("comment_id")) for e in entries}
    recent = {(e.get("handle"), e.get("keyword")): e.get("queued_at") or e.get("sent_at") for e in entries}
    new, newest = [], cursor
    for c in sorted(pool, key=lambda x: str(x["created"])):
        newest = max(newest, str(c["created"]))
        if str(c["id"]) in seen or (cursor and str(c["created"]) <= cursor):
            continue
        for cta in ctas:
            plats = [str(p).lower() for p in D.lst(cta.get("platforms"))]
            if (plats and c["platform"] not in plats) or f" {norm(cta['keyword']).strip()} " not in norm(c["text"]):
                continue
            if recent.get((c["handle"], cta["keyword"])) == D.today() or len(new) >= CAP:
                break
            age = D.days_since(str(c["created"])[:10])
            how = "public_reply" if c["platform"] == "youtube" else "dm" if c["platform"] in ("instagram", "facebook") and (age is None or age <= 7) else "manual"
            url = D.txt(cta.get("asset_url") or cta.get("gate_page"), 300) or "[link to add]"
            priv = D.txt(ctx["idea"].get("privacy_url"), 200)
            new.append({"platform": c["platform"], "comment_id": str(c["id"]), "handle": D.txt(c["handle"], 80), "keyword": cta["keyword"], "sent_at": "", "queued_at": D.today(),
                        "method": "manual", "status": "manual", "suggested_method": how,
                        "message": f"Here is the {D.txt(cta.get('asset_name') or cta.get('asset'), 80)}: {url}" + (f" Privacy: {priv}" if priv else "")})
            recent[(c["handle"], cta["keyword"])] = D.today()
            break
    cutoff = (dt.date.today() - dt.timedelta(days=90)).isoformat()
    kept = [e for e in entries if str(e.get("queued_at") or e.get("sent_at") or D.today())[:10] >= cutoff]
    if not new and newest == cursor and len(kept) == len(entries):
        return {"skipped": "no new keyword comments"}
    k.write(ctx, "sell/fulfilment.json", {"cursor": newest, "entries": kept + new})
    D.alert(ctx, "comment-cta-fulfilment", [f"{len(new)} keyword comments need the asset sent by hand: see sell/fulfilment.json (method suggested per entry; handles and comment ids only)"] if new else [])
    return {"summary": f"{len(new)} keyword comments queued for Charlie, nothing sent. " + "; ".join(notes)}


if __name__ == "__main__":
    k.run(main)
