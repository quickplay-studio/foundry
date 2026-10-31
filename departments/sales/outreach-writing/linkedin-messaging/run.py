"""LinkedIn Messaging: GitHub implementation of departments/sales/outreach-writing/linkedin-messaging/SKILL.md.

Writes one sequence file per ICP segment (connection note of 200 characters or fewer, then three DMs)
and today's queue of at most 15 tier A, corporate leads, each message citing one verified dossier fact.
The model drafts the templates; code lints them and falls back to plain defaults. Nothing is sent:
Charlie sends by hand from his own account, ticks the queue, and the next run logs the ticks to
sell/sent.csv with channel linkedin. PECR: treated like email, so corporate leads only, and DM 1 and
DM 3 end with an opt-out line. A "no" or "stop" goes to suppression.csv with reason linkedin-no.
"""
import csv
import datetime as dt
import io
import json
import re

from foundry import jobkit as k
from foundry import util

OPTOUT = "Reply no and I will stop."
DEFAULT = {"note": "Hi {{first_name}}, I saw that {{fact}}. Good to be connected. {{sender}}",
           "dm1": "Thanks for connecting, {{first_name}}. I saw that {{fact}}. {{offer}} Is this something you handle at {{company}}?",
           "dm2": "{{first_name}}, following up on what I saw at {{company}}: {{fact}}. {{proof}}",
           "dm3": "{{first_name}}, I will leave it there. If this ever becomes a priority at {{company}}, I am easy to find. {{sender}}"}
SIZE = {"{{first_name}}": "Alexandra", "{{company}}": "Acme Industrial Holdings", "{{sender}}": "Charlie", "{{fact}}": " ".join(["word"] * 14),
        "{{offer}}": " ".join(["word"] * 18), "{{proof}}": " ".join(["word"] * 25)}
LIMITS = {"note": 200, "dm1": 60, "dm2": 70, "dm3": 40}
GAPS = {"dm1": 1, "dm2": 5, "dm3": 10}  # days after the previous step (DM 2 and 3 count from DM 1)
EMOJI = re.compile("[" + chr(0x1F000) + "-" + chr(0x1FAFF) + chr(0x2600) + "-" + chr(0x27BF) + "]")
SENT_COLS = "lead_id,campaign_id,step,channel,sent_at,message_id,thread_id".split(",")
DASH = re.compile(r"\s*[" + chr(0x2013) + chr(0x2014) + r"]\s*")  # model text never carries dashes into files


def b2b(ctx):
    audit = k.read(ctx, "audit.json", {}) or {}
    return "b2b" in (str(ctx["idea"].get("business_model", "")).lower(), str(audit.get("business_model", "")).lower())


def table(ctx, rel):
    return list(csv.DictReader(io.StringIO(k.read(ctx, rel, "") or "")))


def get_icp(ctx):
    data = k.read(ctx, "sell/icp.json", None)
    if not isinstance(data, dict):
        data = None
        for block in reversed(re.findall(r"```json\s*(.*?)```", k.read(ctx, "sell/icp.md", "") or "", re.S)):
            try:
                data = json.loads(block)
                break
            except ValueError:
                continue
    return data if isinstance(data, dict) and isinstance(data.get("segments"), list) else None


def fill(tpl, vals):
    for tok, v in vals.items():
        tpl = tpl.replace(tok, v)
    return tpl


def lint(step, tpl):
    """Length is code: the worst-case expansion of the merge fields must fit the step's limit."""
    text, probs = fill(tpl, SIZE), []
    if step == "note" and len(text) > LIMITS["note"]:
        probs.append("note over 200 characters")
    if step != "note" and len(text.split()) + (len(OPTOUT.split()) if step in ("dm1", "dm3") else 0) > LIMITS[step]:
        probs.append(f"{step} over {LIMITS[step]} words")
    if step in ("note", "dm1", "dm2") and "{{fact}}" not in tpl:
        probs.append("no dossier fact")
    if re.search(r"http|www\.|hope this finds you well", tpl, re.I) or chr(33) in tpl or EMOJI.search(tpl) or DASH.search(tpl):
        probs.append("link, emoji, exclamation or dash")
    return probs


def main(ctx):
    if not b2b(ctx):
        return {"skipped": "no business buyer"}
    icp = get_icp(ctx)
    if not icp:
        return {"skipped": "no ICP yet (sell/icp.md): run icp-definition first"}
    today, idea = dt.date.today(), ctx["idea"]
    segs = [str(s["name"]) for s in icp["segments"] if isinstance(s, dict) and s.get("name")]
    sent = table(ctx, "sell/sent.csv")
    done = {(r["lead_id"], r["step"], r["sent_at"][:10]) for r in sent if r.get("channel") == "linkedin"}
    ticked = 0
    for m in re.finditer(r"^- \[[xX]\] (L\d+) \| .*step=(\w+)", k.read(ctx, "sell/linkedin-queue.md", "") or "", re.M):  # Charlie's ticks
        if (m.group(1), m.group(2), today.isoformat()) not in done:
            sent.append({"lead_id": m.group(1), "campaign_id": "", "step": m.group(2), "channel": "linkedin", "sent_at": today.isoformat(), "message_id": "", "thread_id": ""})
            ticked += 1
    if ticked:
        buf = io.StringIO()
        w = csv.DictWriter(buf, SENT_COLS, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(sent)
        k.write(ctx, "sell/sent.csv", buf.getvalue())
    pains = (re.search(r"## Pains(.*?)(\n## |\Z)", k.read(ctx, "sell/icp.md", "") or "", re.S) or [None, ""])[1].strip()[:800]
    mvp = (idea.get("mvp") or [""])[0] if isinstance(idea.get("mvp"), list) else ""
    offer = next((o for o in (str(icp.get("offer", "")), f"{idea.get('title', 'This')}: {mvp}. {idea.get('money', '')}") if o and len(o.split()) <= 18), " ".join(str(icp.get("offer", "")).split()[:18]))
    tpls, notes = {}, []
    for seg in segs:
        ans = k.ask("Draft a LinkedIn sequence for a solo UK founder selling to businesses. Plain, no emoji, no exclamation marks, no links, no pitch in the note. "
                    "Use only these merge fields: {{first_name}} {{company}} {{fact}} {{offer}} {{proof}} {{sender}}. {{fact}} is a short clause and must follow 'I saw that'. "
                    "Limits: note 200 characters; dm1 40 words (thanks, what the product does with the price, one question); dm2 50 words (one useful point or the proof line); dm3 25 words (polite close). "
                    "Return JSON only: {\"note\": \"...\", \"dm1\": \"...\", \"dm2\": \"...\", \"dm3\": \"...\"}\n\nSEGMENT " + seg + "\nPAINS\n" + pains)
        tpl = {}
        for step in LIMITS:
            cand = str(ans.get(step, "")) if isinstance(ans, dict) else ""
            bad = lint(step, cand) if cand else ["model gave none"]
            tpl[step] = cand if not bad else DEFAULT[step]
            if bad and cand:
                notes.append(f"{seg}/{step}: {', '.join(bad)}; default used")
        tpls[seg] = tpl
        rules = ["## Rules", "- The job writes, Charlie sends by hand from his own account. No browser extension, no automation, no scraping.",
                 "- At most 15 invites a day, well under LinkedIn's weekly limit. No emoji, no links in the note.",
                 "- PECR: direct messages are treated like email. Business roles at companies only, and Charlie says who he is.",
                 "- Stop at the first no or stop: add the person to `sell/suppression.csv` with reason `linkedin-no`.",
                 f"- DM 1 and DM 3 end with the opt-out line: {OPTOUT}", ""]
        body = [f"# LinkedIn sequence: {seg}", ""] + rules + ["Merge fields: {{first_name}} {{company}} {{fact}} {{offer}} {{proof}} {{sender}}. {{fact}} is one verified dossier fact.", ""]
        for step, title in (("note", "Connection note (day 0, 200 characters or fewer)"), ("dm1", "DM 1 (after acceptance, 60 words or fewer)"), ("dm2", "DM 2 (5 days later)"), ("dm3", "DM 3 (10 days after DM 1, then stop)")):
            body += [f"## {title}", tpl[step] + (f" {OPTOUT}" if step in ("dm1", "dm3") else ""), ""]
        k.write(ctx, f"sell/sequences/linkedin-{util.slugify(seg)}.md", "\n".join(body))
    proof = k.read(ctx, "sell/proof.json", {}) or {}
    queue, skipped = [], 0
    leads = [r for r in table(ctx, "sell/leads.csv") if r["tier"] == "A" and r["subscriber_type"] == "corporate" and r["suppressed"] != "yes" and r["linkedin_url"] and r["contact_name"]]
    for r in sorted(leads, key=lambda r: -int(r["fit_score"] or 0)):
        mine = sorted((s for s in sent if s["lead_id"] == r["id"] and s["channel"] == "linkedin"), key=lambda s: s["sent_at"])
        step = {"": "note", "note": "dm1", "dm1": "dm2", "dm2": "dm3"}.get(mine[-1]["step"] if mine else "", "")
        anchor = {"dm1": "note", "dm2": "dm1", "dm3": "dm1"}.get(step)  # DM 2 and DM 3 count from DM 1
        when = next((s["sent_at"][:10] for s in mine if s["step"] == anchor), "")
        try:
            due = not anchor or (today - dt.date.fromisoformat(when)).days >= GAPS[step]
        except ValueError:
            due = False
        fact = re.search(r"^- (.+?) \(https?://", k.read(ctx, f"sell/dossiers/{r['id']}.md", "") or "", re.M)
        seg = (proof.get("leads") or {}).get(r["id"], r["segment"]) if isinstance(proof, dict) else r["segment"]
        line = ((proof.get("segments") or {}).get(seg, {}).get("primary") or {}).get("line", "") if isinstance(proof, dict) else ""
        if not step or not due or r["segment"] not in tpls:
            continue
        if not fact or (step == "dm2" and not line):
            skipped += 1
            continue
        clause = " ".join(fact.group(1).rstrip(".").split()[:14])
        text = fill(tpls[r["segment"]][step], {"{{first_name}}": r["contact_name"].split()[0], "{{company}}": r["company"], "{{sender}}": "Charlie",
                                                "{{fact}}": clause, "{{offer}}": offer, "{{proof}}": line}) + (f" {OPTOUT}" if step in ("dm1", "dm3") else "")
        if (step == "note" and len(text) > 200) or clause not in text and step in ("note", "dm1", "dm2"):
            skipped += 1  # too long or no dossier fact: do not queue
            continue
        queue.append((r, step, text))
        if len(queue) >= 15:
            break
    lines = [f"# LinkedIn queue {today.isoformat()}", "", "Charlie sends each message by hand from his own account, then ticks the box. The next run logs ticks to `sell/sent.csv` with channel linkedin. DM 1 only if the invite was accepted.", ""]
    for r, step, text in queue:
        lines += [f"- [ ] {r['id']} | {r['contact_name']} | {r['linkedin_url']} | step={step}", f"  > {text}"]
    if not queue:
        lines.append("Nothing due today: no tier A corporate lead with a LinkedIn URL, a dossier fact and a step due.")
    k.write(ctx, "sell/linkedin-queue.md", "\n".join(lines))
    return {"summary": f"LinkedIn: {len(segs)} segment sequences, {len(queue)} messages queued for Charlie, {skipped} leads skipped (no dossier fact, no proof line or over length)." + (f" Lint: {len(notes)} defaults used." if notes else ""), "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
