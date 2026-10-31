"""Video Prospecting: GitHub implementation of departments/sales/outreach-writing/video-prospecting/SKILL.md.

Scripts for personalised videos, at most 10 tier A prospects a week, highest fit_score first, each with a
verified dossier fact or a live trigger. Spoken length is code-checked (110 to 150 words target, hard
ceiling 190, bracketed screen cues not counted) and the script must quote the dossier fact, else a plain
default is used. Charlie speaks and appears: no AI voice, no face clone. The send line sits in an email
wrapper that keeps the sender identity and the unsubscribe footer, for corporate leads with a valid or
likely address only. Written to sell/sequences/video-<segment>.md; Charlie records and sends.
"""
import csv
import datetime as dt
import io
import re

from foundry import jobkit as k
from foundry import util

WEEK_CAP, CEILING = 10, 190
UNSUB = "I found your address on {{source_note}}, and I write to businesses only. If you would rather not hear from me, reply 'no' and I will remove you today."
SKELETON = ["Structure (seconds): name and company (5), one verified fact from the dossier with their page on screen (10), the problem in their words (10), what the product does and the price with the demo on screen (20), one ask (10), sign-off with name.",
            "Screen cues go in square brackets: which of their pages to show, which of ours. Spoken words only count towards the limit: 110 to 150 target, 190 hard ceiling.",
            "Charlie speaks and appears. No AI voice, no face clone. Each script below is written for one prospect from a verified fact, so it is not a template. If one video is reused for many people it is a template and must say so on screen.",
            "Hosting: a free video plan Charlie already has, or an unlisted YouTube video. No tracking pixels."]
DASH = re.compile(r"\s*[" + chr(0x2013) + chr(0x2014) + r"]\s*")  # model text never carries dashes into files


def b2b(ctx):
    audit = k.read(ctx, "audit.json", {}) or {}
    return "b2b" in (str(ctx["idea"].get("business_model", "")).lower(), str(audit.get("business_model", "")).lower())


def table(ctx, rel):
    return list(csv.DictReader(io.StringIO(k.read(ctx, rel, "") or "")))


def plain(text, n=1500):
    return DASH.sub(", ", str(text or "")).replace(chr(33), ".").strip()[:n]


def spoken(script):
    """Words Charlie says: drop bracketed cues and the 'Beat N (Ns):' labels."""
    return len(re.sub(r"\[[^\]]*\]|^Beat \d+ \(\d+s\):", " ", script, flags=re.M).split())


def default(first, company, fact, idea, mvp, money):
    return "\n".join([
        f"Beat 1 (5s): [Show: your face, then their homepage] Hi {first}, it is Charlie, from {idea.get('title', 'my business')}, here in London.",
        f"Beat 2 (10s): [Show: the page where you found it] I saw that {fact}. That is why I thought of {company}.",
        f"Beat 3 (10s): The problem I work on is this: {str(idea.get('problem', 'a slow manual task')).rstrip('.')}. I may be wrong about how it looks at {company}, so please tell me if I am.",
        f"Beat 4 (20s): [Show: our demo or product page] {idea.get('title', 'It')} {mvp.rstrip('.').lower()}. The price is {money}. It is built for a small business that cannot spare time on this, and it is simple to try before you commit to anything.",
        f"Beat 5 (10s): If that sounds useful, could we have a 15 minute call this week? Or just reply with a yes or a no, and either answer is fine with me.",
        f"Beat 6 (5s): Thanks for watching, {first}. I am Charlie. Speak soon."])


def main(ctx):
    if not b2b(ctx):
        return {"skipped": "no business buyer"}
    leads = [r for r in table(ctx, "sell/leads.csv") if r["tier"] == "A" and r["subscriber_type"] == "corporate" and r["email_status"] in ("valid", "likely") and r["suppressed"] != "yes" and r["contact_name"]]
    if not leads:
        return {"skipped": "no tier A corporate lead with a valid or likely address yet"}
    today, idea = dt.date.today(), ctx["idea"]
    week = "%d-W%02d" % today.isocalendar()[:2]
    state = k.read(ctx, "sell/video-state.json", {}) or {}
    scripted = state.get("scripted", {}) if isinstance(state.get("scripted"), dict) else {}
    room = WEEK_CAP - sum(1 for v in scripted.values() if v.get("week") == week)
    live = {t.get("company_number") or t.get("domain") for t in table(ctx, "sell/triggers.csv") if t.get("expires_on", "") >= today.isoformat()}
    mvp = (idea.get("mvp") or ["does one job"])[0] if isinstance(idea.get("mvp"), list) else "does one job"
    money = str(idea.get("money", "")).rstrip(".") or "a simple monthly price"
    picks = []
    for r in sorted(leads, key=lambda r: -int(r["fit_score"] or 0)):
        dossier = k.read(ctx, f"sell/dossiers/{r['id']}.md", "") or ""
        fact = re.search(r"^- (.+?) \(https?://", dossier, re.M)
        if r["id"] not in scripted and (fact or r["company_number"] in live or r["domain"] in live):
            picks.append((r, fact.group(1).rstrip(".") if fact else ""))
    picks = [p for p in picks if p[1]][:max(room, 0)]  # a verified dossier fact is what the script quotes
    by_seg, notes = {}, 0
    for r, fact in picks:
        first = r["contact_name"].split()[0]
        ans = k.ask("Write a spoken video script of 110 to 150 words for a solo UK founder, Charlie, to record for one business prospect. Plain, no hype, no exclamation marks. "
                    "Beats in order, each on its own line starting 'Beat N (Ns):': name and company (5s), the verified fact quoted exactly (10s), the problem in their words (10s), what the product does and the price (20s), one ask (10s), sign-off (5s). "
                    "Put screen cues in square brackets. Return JSON only: {\"script\": \"...\"}\n\nPROSPECT " + f"{first}, {r['company']}\nFACT (quote exactly) {fact}\nPRODUCT {idea.get('title', '')}: {mvp}\nPRICE {money}\nPROBLEM {idea.get('problem', '')}")
        script = plain(ans.get("script")) if isinstance(ans, dict) and isinstance(ans.get("script"), str) else ""
        if not script or spoken(script) > CEILING or spoken(script) < 90 or fact.lower() not in script.lower():
            script, notes = default(first, r["company"], fact, idea, mvp, money), notes + 1
        body = [f"## {r['id']}", f"Prospect: {r['contact_name']}, {r['company']}. Fit score {r['fit_score']}. Template: no, written for this person from a verified dossier fact.",
                f"Spoken words: {spoken(script)} (target 110 to 150, ceiling {CEILING}).", "", script, ""]
        by_seg.setdefault(r["segment"] or "general", []).append((r["id"], "\n".join(body)))
        scripted[r["id"]] = {"week": week, "date": today.isoformat()}
    if not by_seg:
        return {"skipped": f"no tier A prospect left to script this week (cap {WEEK_CAP} a week, each needs a verified dossier fact)"}
    suppressed = {r["id"] for r in table(ctx, "sell/leads.csv") if r["suppressed"] == "yes"}
    for seg, new in by_seg.items():
        path = f"sell/sequences/video-{util.slugify(seg)}.md"
        old = {m.group(1): m.group(0) for m in re.finditer(r"(?ms)^## (L\d+)\b.*?(?=^## L\d+\b|\Z)", k.read(ctx, path, "") or "")}
        head = [f"# Video prospecting: {seg}", "", "For corporate subscribers only (PECR). The video link goes out in email 3 or LinkedIn DM 2.", "", "## Skeleton", *SKELETON, "",
                "## Send line", "I recorded a short video for you, {{first_name}}: {{video_link}}", "",
                "## Email wrapper (marketing: sender identity and the unsubscribe footer stay)", "Subject: a short video for you",
                "Hello {{first_name}},", "", "{{send_line}}", "", "{{sender}}, {{venture}}, {{reply_address}}", "", "{{unsubscribe}}",
                f"where {{{{unsubscribe}}}} reads: {UNSUB}", ""]
        merged = {i: t for i, t in old.items() if i not in suppressed}
        merged.update({i: t for i, t in new})
        k.write(ctx, path, "\n".join(head) + "\n" + "\n".join(t.rstrip("\n") + "\n" for _, t in sorted(merged.items())))
    k.write(ctx, "sell/video-state.json", {"scripted": scripted})
    return {"summary": f"Video scripts for {len(picks)} tier A prospects across {len(by_seg)} segments ({WEEK_CAP} a week cap). Charlie records and sends; {notes} used the plain default.", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
