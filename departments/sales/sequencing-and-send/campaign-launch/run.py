"""Campaign Launch: GitHub implementation of departments/sales/sequencing-and-send/campaign-launch/SKILL.md.

Runs the PECR and deliverability preflight on every draft campaign, renders each lead's emails from the
sequence file and writes sell/send-queue.csv and sell/launch-pr.md (title, counts, preflight table,
three samples, cap, window, kill rule), then STOPS. Nothing is sent and nothing is approved: campaigns.json
keeps status draft and gains a `launch` block whose on_merge says status approved, which Charlie's
merge applies. PECR in code: only corporate subscribers with a valid or likely business email who are not
suppressed are queued (an individual address is never queued); every email carries the sender, the venture
and the reply address plus the unsubscribe line, plain text, no pixel. Seed copies for Charlie are queued
with status seed. The Gmail secrets are only checked for presence; the scheduled sender does the sending.
"""
import csv
import datetime as dt
import io
import re

from foundry import jobkit as k

QUEUE = "lead_id,campaign_id,step,send_after,to,subject,body,status".split(",")
FREEMAIL = re.compile(r"(gmail|googlemail|outlook|hotmail|live|msn|yahoo|icloud|aol)\.|^me\.com$")
UNSUB = "I found your address on {{source_note}}, and I write to businesses only. If you would rather not hear from me, reply 'no' and I will remove you today."
KILL = "Pause at a 3 percent bounce rate on the last 50 sends, or on any spam complaint."


def b2b(ctx):
    audit = k.read(ctx, "audit.json", {}) or {}
    return "b2b" in (str(ctx["idea"].get("business_model", "")).lower(), str(audit.get("business_model", "")).lower())


def table(ctx, rel):
    return list(csv.DictReader(io.StringIO(k.read(ctx, rel, "") or "")))


def parse(text):
    steps = {}
    for m in re.finditer(r"(?ms)^## Email (\d+)\s*\(day (\d+)\)\s*\n(.*?)(?=^## Email \d+|\Z)", text):
        sm = re.match(r"\s*Subject:\s*(.*)\n", m.group(3))
        steps[int(m.group(1))] = (int(m.group(2)), sm.group(1).strip() if sm else "", (m.group(3)[sm.end():] if sm else m.group(3)).strip())
    return steps


def source_note(lead):
    pub = re.search(r"email published at https?://([^/\s]+)", lead["notes"])
    if pub:
        return f"your website, {pub.group(1)}"
    if "hunter" in lead["notes"].lower():
        return "a business email finder"
    return "public business records" + (f" ({re.sub(r'^https?://', '', lead['source_url']).split('/')[0]})" if lead["source_url"] else "")


def after(d, holidays):
    """The next Tuesday to Thursday that is not a holiday."""
    d += dt.timedelta(days=1)
    while d.weekday() not in (1, 2, 3) or d.isoformat() in holidays:
        d += dt.timedelta(days=1)
    return d


def allowed_day(d, holidays):
    """Tue to Thu only: Mon moves on, Fri and the weekend move back; a holiday moves to the next open day."""
    d += dt.timedelta(days={0: 1, 4: -1, 5: -2, 6: -3}.get(d.weekday(), 0))
    return d if d.isoformat() not in holidays else after(d, holidays)


def stamp(day, n):
    """The n-th send of a day: 08:00 window first (about 4 minute gaps, 30 sends), then 13:00."""
    minute = (8 * 60 + n * 4) if n < 30 else (13 * 60 + (n - 30) * 4)
    t = dt.datetime(day.year, day.month, day.day, minute // 60 % 24, minute % 60)
    try:
        from zoneinfo import ZoneInfo
        t = t.replace(tzinfo=ZoneInfo("Europe/London"))
    except Exception:  # noqa: BLE001
        pass
    return t.isoformat()


def eligible(c, leads, supp, seen):
    """Recipients from lead_ids only (never non_email_lead_ids): corporate, clean business address, valid or likely, not suppressed."""
    who, out = [], {"not corporate": 0, "bad or personal address": 0, "email status": 0, "suppressed": 0, "duplicate address": 0}
    for lid in c.get("lead_ids", []):
        r = leads.get(lid)
        if not r:
            continue
        em = r["email"].lower().strip()
        if r["subscriber_type"] != "corporate":
            out["not corporate"] += 1
        elif not re.match(r"^[\w.+'-]+@([\w-]+\.)+\w{2,}$", em) or FREEMAIL.search(em.split("@")[-1]):
            out["bad or personal address"] += 1
        elif r["email_status"] not in ("valid", "likely"):
            out["email status"] += 1
        elif r["suppressed"] == "yes" or em in supp or em.split("@")[-1] in supp or (r["domain"] and r["domain"] in supp):
            out["suppressed"] += 1
        elif em in seen:
            out["duplicate address"] += 1
        else:
            seen.add(em)
            who.append(r)
    return who, {a: n for a, n in out.items() if n}


def main(ctx):
    if not b2b(ctx):
        return {"skipped": "no business buyer"}
    camps = k.read(ctx, "sell/campaigns.json", {}) or {}
    drafts = [c for c in camps.get("campaigns", []) if isinstance(c, dict) and c.get("status") == "draft"] if isinstance(camps, dict) else []
    if not drafts:
        return {"skipped": "no draft campaign in sell/campaigns.json: run campaign-orchestration first"}
    today, slug, idea = dt.date.today(), ctx["slug"], ctx["idea"]
    leads = {r["id"]: r for r in table(ctx, "sell/leads.csv")}
    supp = set()
    for rel, col in (("sell/suppression.csv", "email_or_domain"), ("sell/suppress.csv", "email")):  # Deals writes suppress.csv
        supp |= {str(r.get(col, "")).lower().strip().lstrip("@") for r in table(ctx, rel) if r.get(col)}
    deliv = k.read(ctx, "sell/deliverability.json", {}) or {}
    deliv = deliv if isinstance(deliv, dict) else {}
    proof = k.read(ctx, "sell/proof.json", {}) or {}
    holidays = set((k.read(ctx, "sell/send-windows.json", {}) or {}).get("skip_dates", []))
    reply = next(iter(re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", ctx["brain"])), "")
    sender = (re.search(r"Operator: ([^,.]+)", ctx.get("company", "")) or [None, "Charlie"])[1].strip()
    privacy = next(iter(re.findall(r"https?://\S*privacy\S*", ctx["brain"] + " " + str(idea.get("privacy_url", "")))), "").rstrip(".,)")
    venture, cap = str(idea.get("title", slug)), int(deliv["daily_cap"]) if isinstance(deliv.get("daily_cap"), (int, float)) else 0
    glob = []
    if not deliv:
        glob.append("no deliverability.json: run deliverability (needs sell/mailboxes.json)")
    else:
        glob += ["deliverability pause is on"] if deliv.get("pause") is not False else []
        glob += ["SPF, DKIM or DMARC not passing"] if any(m.get(f) not in ("pass", "skip") for m in deliv.get("mailboxes", []) if isinstance(m, dict) for f in ("spf", "dkim", "dmarc")) else []
        glob += ["daily cap is 0 (warm-up, spam test or DNS fix pending)"] if cap <= 0 else []
    glob += [] if reply else ["no reply address in brain.md"]
    start = today + dt.timedelta(days=(1 - today.weekday()) % 7 or 7)  # cohort 1 starts on the next Tuesday that is not a holiday
    while start.isoformat() in holidays:
        start += dt.timedelta(days=7)
    rows, load, domains, results, samples, emailed = [], {}, set(), [], [], set()
    for c in drafts:
        fails = list(glob)
        seq = parse(k.read(ctx, "sell/" + str(c["sequence"]), "") or "") if c.get("sequence") else {}
        if not seq:
            fails.append(f"sequence file missing or unreadable: {c.get('sequence') or 'none'}")
        for n, (_, _, body) in seq.items():
            fails += [f"email {n} has no unsubscribe token"] if "{{unsubscribe}}" not in body else []
            fails += [f"email {n} is not plain text"] if re.search(r"<[a-zA-Z/][^>]*>|tracking pixel", body) else []
            if n == 1 and (("{{privacy_url}}" in body and not privacy) or re.search(r"https?://", body.replace("{{privacy_url}}", ""))):
                fails.append("email 1 has no privacy URL (Legal privacy-policy) or carries a link")
        who, excluded = eligible(c, leads, supp, set(emailed))
        fails += [] if who else ["no eligible recipient left"]
        built, my_load, my_domains = [], dict(load), set(domains)
        days = {t["step"]: t["day"] for t in c.get("touches", []) if t.get("channel") == "email"}
        size = max(1, int(c.get("cohort_size") or len(who) or 1))
        for i, r in enumerate(who if not fails else []):
            seg = (proof.get("leads") or {}).get(r["id"], r["segment"]) if isinstance(proof, dict) else r["segment"]
            line = (((proof.get("segments") or {}).get(seg) or {}).get("primary") or {}).get("line", "") if isinstance(proof, dict) else ""
            opener = (re.search(r"## Opener\s*\n(.+)", k.read(ctx, f"sell/dossiers/{r['id']}.md", "") or "") or [None, ""])[1].strip()
            note = source_note(r)
            vals = {"{{first_name}}": r["contact_name"].split()[0] if r["contact_name"] else "Hello", "{{company}}": r["company"], "{{proof}}": line,
                    "{{opener}}": opener if opener and not opener.startswith("(none") else f"I am writing to a small number of {r['segment'].lower() or 'local'} businesses.",
                    "{{sender}}": sender, "{{privacy_url}}": privacy, "{{venture}}": venture, "{{reply_address}}": reply, "{{source_note}}": note,
                    "{{unsubscribe}}": f"{sender}, {venture}, {reply}\n" + UNSUB.replace("{{source_note}}", note)}
            first_subject = ""
            for n, (hday, subj, body) in sorted(seq.items()):
                text, subject = body, subj
                for tok, v in vals.items():
                    text, subject = text.replace(tok, v), subject.replace(tok, v)
                text = text if line else "\n".join(ln for ln in text.split("\n") if "{{proof}}" not in ln)  # no proof line yet: drop it, never invent one
                first_subject = first_subject or subject
                if re.search(r"\{\{\w+\}\}", text + subject) or reply not in text or sender not in text or "reply 'no'" not in text:
                    fails.append(f"email {n} did not render cleanly (unresolved field, or sender, reply address or unsubscribe line missing)")
                    break
                dom = r["email"].split("@")[-1].lower()
                day = allowed_day(start + dt.timedelta(days=7 * (i // size) + days.get(n, hday)), holidays)
                while (day, dom) in my_domains:  # one send a day per recipient domain
                    day = after(day, holidays)
                my_domains.add((day, dom))
                my_load[day] = my_load.get(day, 0) + 1
                built.append({"lead_id": r["id"], "campaign_id": c["id"], "step": n, "send_after": stamp(day, my_load[day] - 1), "to": r["email"].lower().strip(),
                              "subject": subject if n == 1 else "Re: " + first_subject, "body": text, "status": "awaiting-approval"})
            if fails:
                break
        over = next((d.isoformat() for d, v in my_load.items() if cap and v > cap), "")
        fails += [f"daily volume would pass the warm-up cap of {cap} on {over}"] if over and not fails else []
        if fails:
            c["launch"] = {"preflight": "fail", "failures": fails[:8], "checked_on": today.isoformat()}
        else:
            seeds = [dict(b, lead_id=f"SEED-{c['id']}", send_after=stamp(today, 0), to=reply, status="seed") for b in built if b["lead_id"] == who[0]["id"]]
            rows += built + seeds
            emailed |= {b["to"] for b in built}
            load, domains = my_load, my_domains
            samples += [b for b in built if b["lead_id"] == who[0]["id"]][:3] if not samples else []
            c["launch"] = {"preflight": "pass", "recipients": len(who), "excluded": excluded, "queued": len(built), "seed_rows": len(seeds),
                           "pr_title": f"launch: {slug} campaign {c['id']}", "on_merge": {"status": "approved"}, "checked_on": today.isoformat()}
        results.append((c, fails))
    out = io.StringIO()
    w = csv.DictWriter(out, QUEUE, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    k.write(ctx, "sell/send-queue.csv", out.getvalue())
    k.write(ctx, "sell/campaigns.json", camps)
    if not (ctx["folder"] / "sell" / "sent.csv").exists():
        k.write(ctx, "sell/sent.csv", "lead_id,campaign_id,step,channel,sent_at,message_id,thread_id")
    ok = [c for c, f in results if not f]
    gmail = all(k.secret(n) for n in ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN"))
    pr = [f"# {'; '.join(c['launch']['pr_title'] for c in ok) or 'launch: preflight failed'}", "",
          "Nothing has been sent or approved. Merging approves: set `status` to `approved` for the passing campaigns in `sell/campaigns.json` (each has `launch.on_merge`).", "",
          "## Preflight", "| Campaign | Result | Recipients | Queued | Failures |", "|---|---|---|---|---|",
          *[f"| {c['id']} | {c['launch']['preflight']} | {c['launch'].get('recipients', 0)} | {c['launch'].get('queued', 0)} | {'; '.join(f) or 'none'} |" for c, f in results], "",
          f"Daily cap: {cap}. Send window: {(ok[0].get('window') if ok else '') or 'Tue-Thu 08:00-10:00 Europe/London'}. Kill rule: {KILL}",
          "Gmail secrets: " + ("present." if gmail else "missing, so the scheduled sender cannot send until Charlie adds GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET and GMAIL_REFRESH_TOKEN."), "",
          "## Rendered samples", *([f"### {s['campaign_id']} step {s['step']} to {s['lead_id']}\nSubject: {s['subject']}\n\n{s['body']}\n" for s in samples] or ["No samples: no campaign passed."])]
    k.write(ctx, "sell/launch-pr.md", "\n".join(pr))
    queued = len([r for r in rows if r["status"] != "seed"])
    return {"summary": f"Launch preflight: {len(ok)} of {len(results)} campaigns pass, {queued} emails queued awaiting Charlie's approval, nothing sent." + ("" if gmail else " Gmail secrets missing."),
            "flag": "ok" if ok and len(ok) == len(results) else "caution"}


if __name__ == "__main__":
    k.run(main)
