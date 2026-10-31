"""Deliverability: GitHub implementation of departments/sales/sequencing-and-send/deliverability/SKILL.md.

Reads Charlie's sell/mailboxes.json (never creates a mailbox), checks SPF, DKIM and DMARC through Google
DNS over HTTPS (skipped for gmail.com, which Google signs), ramps the daily cap by days since first
send (5, 10, 20, 30, then 40), holds the cap while bounces are 2 percent or more, and pauses at 3 percent
on the last 50 sends, on any spam complaint or on a Gmail warning. A pause stays until Charlie edits
deliverability.json. A mailbox with no spam score of 8 or more recorded is held at cap 0. The pause is
reported as a caution flag, never stop. Read-only on sent.csv, replies and bounces.
"""
import csv
import datetime as dt
import io
import re

import requests

from foundry import jobkit as k

CAPS = [(7, 5), (14, 10), (21, 20), (28, 30), (10 ** 6, 40)]
SPAM = re.compile(r"this is spam|reported? (you |this )?(as )?spam|spam complaint|marked (as )?spam", re.I)


def b2b(ctx):
    audit = k.read(ctx, "audit.json", {}) or {}
    return "b2b" in (str(ctx["idea"].get("business_model", "")).lower(), str(audit.get("business_model", "")).lower())


def table(ctx, rel):
    return list(csv.DictReader(io.StringIO(k.read(ctx, rel, "") or "")))


def doh(name, rtype):
    """List of answer strings from Google DoH, or None when the lookup itself failed."""
    try:
        r = requests.get("https://dns.google/resolve", params={"name": name, "type": rtype}, timeout=15)
        d = r.json() if r.ok else {}
    except Exception:  # noqa: BLE001
        return None
    if "Status" not in d:
        return None
    return [str(a.get("data", "")).strip('"').replace('" "', "").lower() for a in d.get("Answer") or []]


def step_for(day):
    return next(i for i, (top, _) in enumerate(CAPS) if day <= top)


def main(ctx):
    if not b2b(ctx):
        return {"skipped": "no business buyer"}
    boxes = k.read(ctx, "sell/mailboxes.json", None)
    if not isinstance(boxes, list) or not boxes:
        return {"skipped": "no sending mailbox: Charlie lists an owned mailbox in sell/mailboxes.json"}
    today = dt.date.today()
    sends = [s for s in sorted(table(ctx, "sell/sent.csv"), key=lambda s: s.get("sent_at", "")) if s.get("channel", "email") in ("email", "")][-50:]
    ids = {s["lead_id"] for s in sends}
    hard = sum(1 for b in table(ctx, "sell/bounces.csv") if b.get("type", "").lower() == "hard" and b.get("lead_id") in ids)
    rate = round(hard / len(sends), 4) if sends else 0.0
    replies = table(ctx, "sell/replies.csv") + [r for r in (k.read(ctx, "sell/replies.json", []) or []) if isinstance(r, dict)]
    complaint = any(SPAM.search(" ".join(str(v) for v in r.values())) for r in replies)
    prior = k.read(ctx, "sell/deliverability.json", {}) or {}
    alerts = [a for a in prior.get("alerts", []) if isinstance(a, str)][-20:] if isinstance(prior, dict) else []
    out, reasons = [], []
    for b in boxes:
        if not isinstance(b, dict) or "@" not in str(b.get("address", "")):
            continue
        addr = str(b["address"]).lower()
        dom = str(b.get("domain") or addr.split("@")[1]).lower()
        row = {"address": addr, "spf": "skip", "dkim": "skip", "dmarc": "skip", "fixes": []}
        if dom not in ("gmail.com", "googlemail.com"):
            mx = " ".join(doh(dom, "MX") or [])
            prov = "google" if "google" in mx else "microsoft" if "outlook" in mx else "other"
            include = {"google": "include:_spf.google.com", "microsoft": "include:spf.protection.outlook.com"}.get(prov, "")
            txt = doh(dom, "TXT")
            spf = next((t for t in txt or [] if t.startswith("v=spf1")), "")
            row["spf"] = "unknown" if txt is None else "pass" if spf and include in spf else "fail"
            if row["spf"] == "fail":
                row["fixes"].append(f"TXT at {dom}: v=spf1 {include} ~all".replace("  ", " "))
            sel = doh(f"google._domainkey.{dom}", "TXT") if prov == "google" else None
            row["dkim"] = "pass" if sel and any("v=dkim1" in t for t in sel) else "fail" if prov == "google" and sel is not None else "unknown"
            if row["dkim"] == "fail":
                row["fixes"].append(f"Turn on DKIM in Google Workspace and add the TXT at google._domainkey.{dom}")
            dm = doh(f"_dmarc.{dom}", "TXT")
            row["dmarc"] = "unknown" if dm is None else "pass" if any(t.startswith("v=dmarc1") for t in dm) else "fail"
            if row["dmarc"] == "fail":
                row["fixes"].append(f"TXT at _dmarc.{dom}: v=DMARC1; p=none; rua=mailto:{addr} (move to quarantine after a clean fortnight)")
        try:
            day = max(1, (today - dt.date.fromisoformat(str(b.get("first_send", "")))).days + 1)
        except ValueError:
            day = 1
        idx = step_for(day)
        cap = CAPS[max(idx - 1, 0) if rate >= 0.02 else idx][1]  # hold the step while bounces are 2 percent or more
        if isinstance(b.get("daily_limit"), int):
            cap = min(cap, b["daily_limit"])
        score = b.get("spam_score")
        status = "ok"
        if "fail" in (row["spf"], row["dkim"], row["dmarc"]):
            status = "fix-dns"
        elif not isinstance(score, (int, float)) or score < 8:
            status = "needs-spam-test" if not isinstance(score, (int, float)) else "blocked-spam-score"
        if b.get("gmail_warning"):
            reasons.append(f"{addr}: Gmail warning recorded by Charlie")
        row.update({"warm_day": day, "daily_cap": cap if status == "ok" else 0, "bounce_rate": rate, "spam_score": score if isinstance(score, (int, float)) else None, "status": status})
        out.append(row)
    if not out:
        return {"skipped": "sell/mailboxes.json has no usable address"}
    if rate >= 0.03:
        reasons.append(f"bounce rate {rate:.1%} on the last {len(sends)} sends")
    if complaint:
        reasons.append("a reply says this is spam")
    pause = bool(reasons) or bool(isinstance(prior, dict) and prior.get("pause") is True)
    for r in reasons:
        line = f"{today.isoformat()} PAUSE: {r}"
        if line not in alerts:
            alerts.append(line)
    cap_total = 0 if pause else sum(r["daily_cap"] for r in out)
    k.write(ctx, "sell/deliverability.json", {"checked_on": today.isoformat(), "mailboxes": out, "daily_cap": cap_total, "pause": pause,
                                              "rotation": [r["address"] for r in out if r["status"] == "ok"], "alerts": alerts[-20:]})
    bad = [f"{r['address']} {r['status']}" for r in out if r["status"] != "ok"]
    return {"summary": f"Deliverability: daily cap {cap_total}, {'PAUSED' if pause else 'running'}, bounce rate {rate:.1%} on {len(sends)} sends." + (f" Not ready: {'; '.join(bad)}." if bad else ""),
            "flag": "caution" if pause or bad else "ok"}


if __name__ == "__main__":
    k.run(main)
