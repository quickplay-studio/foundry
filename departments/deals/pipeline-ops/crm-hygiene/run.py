"""CRM Hygiene: GitHub implementation of departments/deals/pipeline-ops/crm-hygiene/SKILL.md.

Cleans sell/pipeline.csv in place with plain code (no model): dedupe by email, then company domain plus contact; normalise
dates, values, stages and company names; flag stalled or incomplete rows without changing a stage silently; auto dormant after
45 days. Merged-away rows go to sell/pipeline-archive.csv, one dated block to sell/hygiene-log.md. The optional one-way HubSpot
push uses HUBSPOT_TOKEN. proposal_sent detection needs the Gmail thread, so it is left to Charlie. The pipeline has no phone column.
"""
import datetime as dt
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import dealkit as D  # noqa: E402
from foundry import jobkit as k  # noqa: E402

DATES = ("expected_close", "next_step_date", "last_touch", "created", "updated")
SYN = {"demo booked": "meeting_booked", "meeting booked": "meeting_booked", "booked": "meeting_booked", "call booked": "meeting_booked", "discovery": "discovery_done", "discovery done": "discovery_done",
       "proposal out": "proposal_sent", "proposal sent": "proposal_sent", "negotiating": "negotiation", "verbal": "verbal_yes", "verbal yes": "verbal_yes", "closed won": "won",
       "closed lost": "lost", "qualified lead": "qualified", "lead": "new", "cold": "dormant", "on hold": "dormant"}
OURS = ("no_debrief", "stalled", "no_next_step", "no_value")


def clean_value(v):
    m = re.fullmatch(r"£?\s*([\d,]+(?:\.\d+)?)\s*([kK]?)", str(v).strip())
    if not m:
        return ""
    n = float(m.group(1).replace(",", "")) * (1000 if m.group(2) else 1)
    return f"{n:g}"


def clean_company(name):
    words = " ".join(str(name).split()).split(" ")
    return " ".join(w if (len(w) <= 4 and w.isupper()) or not (w.islower() or w.isupper()) else w.title() for w in words)


def merge(group):
    group.sort(key=lambda r: (D.parse_date(r.get("created")) or dt.date.max, r.get("id", "")))
    base, rest = dict(group[0]), sorted(group[1:], key=lambda r: D.parse_date(r.get("updated")) or dt.date.min)
    for r in rest:
        for c in D.COLS:
            if c not in ("id", "created", "notes") and r.get(c):
                base[c] = r[c]
    notes = [n.strip() for r in group for n in r.get("notes", "").split(";") if n.strip()]
    base["notes"] = "; ".join(dict.fromkeys(notes))
    return base, rest


def push_hubspot(rows, token):
    inputs = [{"idProperty": "email", "id": r["email"], "properties": {"email": r["email"], "firstname": r["contact"].split(" ")[0] if r["contact"] else "", "lastname": " ".join(r["contact"].split(" ")[1:]),
                                                                       "company": r["company"], "jobtitle": r["role"]}} for r in rows if r.get("email")]
    sent = 0
    try:
        for i in range(0, len(inputs), 100):
            resp = requests.post("https://api.hubapi.com/crm/v3/objects/contacts/batch/upsert", json={"inputs": inputs[i:i + 100]}, headers={"Authorization": f"Bearer {token}"}, timeout=60)
            if not resp.ok:
                return f"HubSpot push stopped after {sent} rows (HTTP {resp.status_code})"
            sent += len(inputs[i:i + 100])
    except Exception as exc:  # noqa: BLE001
        return f"HubSpot push stopped after {sent} rows ({type(exc).__name__})"
    return f"HubSpot: {sent} rows pushed one way"


def main(ctx):
    gate = D.gate(ctx)
    if gate:
        return gate
    rows, header = D.read_csv(ctx, "sell/pipeline.csv")
    if not header:
        return {"skipped": "no sell/pipeline.csv yet"}
    if header != D.COLS:
        return {"skipped": "pipeline.csv header differs from the contract: refusing to touch it"}
    before = {r["id"]: dict(r) for r in rows}
    groups, key_of = [], {}
    for r in rows:
        r["email"] = r["email"].strip().lower()
        keys = [("e", r["email"])] if r["email"] else []
        if r["contact"] and r["email"] and D.domain(r["email"]) not in D.FREEMAIL:
            keys.append(("n", D.domain(r["email"]), r["contact"].strip().lower()))
        hit = next((key_of[x] for x in keys if x in key_of), None)
        grp = hit if hit is not None else len(groups)
        if hit is None:
            groups.append([])
        groups[grp].append(r)
        key_of.update({x: grp for x in keys})
    kept, archived = [], []
    for g in groups:
        base, rest = merge(g) if len(g) > 1 else (g[0], [])
        kept.append(base)
        archived += [dict(r, merged_into=base["id"]) for r in rest]
    sup, today, flags = D.suppressed(ctx), dt.date.today(), {}
    meets = {m.get("deal_id"): m for m in (k.read(ctx, "sell/meetings.json", []) or []) if isinstance(m, dict)}
    for r in kept:
        for c in DATES:
            d = D.parse_date(r[c])
            r[c] = d.isoformat() if d else ""
        r["value_gbp"] = clean_value(r["value_gbp"])
        stage = " ".join(r["stage"].lower().replace("_", " ").split())
        r["stage"] = stage.replace(" ", "_") if stage.replace(" ", "_") in D.STAGES else SYN.get(stage, r["stage"])
        r["company"] = clean_company(r["company"])
        active = r["stage"] in D.ACTIVE
        if r["email"] in sup and active:
            r.update(stage="lost", lost_reason="never", flag="suppressed", next_step="", next_step_date="")
            D.add_note(r, "suppressed: never active again")
        ref = D.parse_date(r["last_touch"] or r["updated"] or r["created"])
        if active and ref and (today - ref).days > 45:
            r["stage"], active = "dormant", False
            D.add_note(r, "auto dormant")
        start = D.parse_dt((meets.get(r["id"]) or {}).get("start"))
        found = None
        if r["stage"] == "meeting_booked" and start and (dt.datetime.now(dt.timezone.utc) - start).days > 3 and not D.files(ctx, f"sell/debriefs/{r['id']}-*.json"):
            found = "no_debrief"
        elif r["stage"] == "proposal_sent" and (D.days_since(r["last_touch"]) or 0) > 21:
            found = "stalled"
        elif active and (not r["next_step"] or (D.parse_date(r["next_step_date"]) and D.parse_date(r["next_step_date"]) < today)):
            found = "no_next_step"
        elif r["stage"] == "won" and not r["value_gbp"]:
            found = "no_value"
        if r["flag"] in OURS or not r["flag"]:
            r["flag"] = found or ""
        if r["flag"] in OURS:
            flags[r["flag"]] = flags.get(r["flag"], 0) + 1
    changed = sum(1 for r in kept for c in D.COLS if before.get(r["id"], {}).get(c) != r[c])
    old_archive, _ = D.read_csv(ctx, "sell/pipeline-archive.csv")
    D.save_pipeline(ctx, kept)
    if archived or old_archive:
        D.write_csv(ctx, "sell/pipeline-archive.csv", old_archive + archived, D.COLS + ["merged_into"])
    token = k.secret("HUBSPOT_TOKEN")
    hub = push_hubspot(kept, token) if token else "HubSpot skipped: no HUBSPOT_TOKEN"
    log = k.read(ctx, "sell/hygiene-log.md", "") or "# Hygiene log\n"
    block = [f"## {D.today()}", f"- rows: {len(kept)} kept, {len(archived)} merged away to pipeline-archive.csv", f"- fields changed: {changed}",
             "- flags raised: " + (", ".join(f"{n} {f}" for f, n in sorted(flags.items())) or "none"), f"- {hub}", "- proposal_sent detection needs the Gmail thread: skipped"]
    k.write(ctx, "sell/hygiene-log.md", log.rstrip("\n") + "\n\n" + "\n".join(block))
    return {"summary": f"Cleaned {len(kept)} rows, merged {len(archived)}, {changed} fields changed, flags: " + (", ".join(f"{n} {f}" for f, n in sorted(flags.items())) or "none") + ". " + hub}


if __name__ == "__main__":
    k.run(main)
