"""Email Verification: GitHub implementation of departments/sales/enrichment/email-verification/SKILL.md.

Syntax, then domain (Google DNS over HTTPS), then the disposable list beside this file and free-mail
domains (personal addresses fail the PECR rule), then the Hunter verifier on tier A then B while free
credits last (HUNTER_API_KEY, stops at 80 percent). No SMTP probing. Hard bounces, or two soft bounces
in a row, set email_status=bounced and join sell/suppression.csv. A DNS lookup that cannot be answered
leaves the row unchecked rather than marking it invalid. Campaign-launch sends only to valid and likely.
"""
import csv
import datetime as dt
import io
import re
from pathlib import Path

import requests

from foundry import jobkit as k

LEAD_COLS = ("id,company,company_number,domain,website,segment,subscriber_type,contact_name,role,email,email_basis,phone,linkedin_url,"
             "source,source_url,collected_on,email_status,verified_on,fit_score,tier,fit_reason,suppressed,notes").split(",")
SYNTAX = re.compile(r"^[a-z0-9._%+'-]+@([a-z0-9-]+\.)+[a-z]{2,}$")
FREEMAIL = re.compile(r"(gmail|googlemail|outlook|hotmail|live|msn|yahoo|icloud|aol)\.|^me\.com$")
HUNTER_MAP = {"valid": "valid", "accept_all": "risky", "invalid": "invalid", "disposable": "invalid", "webmail": "invalid", "unknown": "likely"}
MAX_CHECKS = 400


def b2b(ctx):
    audit = k.read(ctx, "audit.json", {}) or {}
    return "b2b" in (str(ctx["idea"].get("business_model", "")).lower(), str(audit.get("business_model", "")).lower())


def table(ctx, rel):
    return list(csv.DictReader(io.StringIO(k.read(ctx, rel, "") or "")))


def jget(url, **kw):
    try:
        r = requests.get(url, timeout=15, **kw)
        return r.json() if r.ok else {}
    except Exception:  # noqa: BLE001
        return {}


def has_records(dom, rtype, cache):
    """True or False from Google DoH, None when the lookup itself failed."""
    if (dom, rtype) not in cache:
        d = jget("https://dns.google/resolve", params={"name": dom, "type": rtype})
        cache[(dom, rtype)] = bool(d.get("Answer")) if isinstance(d, dict) and "Status" in d else None
    return cache[(dom, rtype)]


def domain_state(dom, cache):
    mx = has_records(dom, "MX", cache)
    if mx is None:
        return None
    return True if mx else has_records(dom, "A", cache)


def hunter_room(key):
    d = (jget("https://api.hunter.io/v2/account", params={"api_key": key}).get("data") or {}).get("requests", {}).get("verifications", {})
    used, avail = d.get("used"), d.get("available")
    return isinstance(used, int) and isinstance(avail, int) and avail > 0 and used / avail < 0.8


def hard_bounces(ctx):
    seen = {}
    for b in sorted(table(ctx, "sell/bounces.csv"), key=lambda r: r.get("date", "")):
        seen.setdefault(b.get("email", "").lower().strip(), []).append((b.get("type", "").lower(), b.get("lead_id", "")))
    return {e: v for e, v in seen.items() if e and (any(t == "hard" for t, _ in v) or [t for t, _ in v][-2:] == ["soft", "soft"])}


def main(ctx):
    if not b2b(ctx):
        return {"skipped": "no business buyer"}
    leads = table(ctx, "sell/leads.csv")
    if not leads:
        return {"skipped": "no sell/leads.csv rows yet: run list-building first"}
    today, hunter, cache = dt.date.today(), k.secret("HUNTER_API_KEY"), {}
    try:
        disposable = {d.strip().lower() for d in (Path(__file__).parent / "disposable-domains.txt").read_text(encoding="utf-8").splitlines() if d.strip()}
    except OSError:
        disposable = set()
    counts = dict.fromkeys(("valid", "likely", "risky", "invalid", "bounced"), 0)
    checked = credits = unchecked = 0
    supp = table(ctx, "sell/suppression.csv")
    known = {r.get("email_or_domain", "").lower() for r in supp}
    bounced = hard_bounces(ctx)
    for r in leads:  # bounces first: they beat any earlier status
        if r["email"] and r["email"].lower() in bounced:
            r["email_status"], r["verified_on"] = "bounced", today.isoformat()
            if r["email"].lower() not in known:
                supp.append({"email_or_domain": r["email"].lower(), "added_on": today.isoformat(), "reason": "bounce"})
                known.add(r["email"].lower())
    order = sorted((r for r in leads if r["email"] and r["email_status"] != "bounced" and r["suppressed"] != "yes"), key=lambda r: (r["tier"] not in ("A", "B"), r["tier"]))
    for r in order:
        try:
            stale = (today - dt.date.fromisoformat(r["verified_on"])).days > 30
        except ValueError:
            stale = True
        if not (r["email_status"] == "" or stale) or checked >= MAX_CHECKS:
            continue
        email = re.sub(r"\s", "", r["email"].lower()).strip(".,;:<>()\"'")
        dom = email.split("@")[-1]
        status = None
        if not SYNTAX.match(email):
            status = "invalid"
        elif FREEMAIL.search(dom) or dom in disposable:
            status = "invalid"  # personal or throwaway: fails PECR for B2B
        else:
            state = domain_state(dom, cache)
            if state is None:
                unchecked += 1
                continue
            status = "likely" if state else "invalid"
            if status == "likely" and hunter and r["tier"] in ("A", "B") and hunter_room(hunter):
                d = jget("https://api.hunter.io/v2/email-verifier", params={"email": email, "api_key": hunter}).get("data") or {}
                credits += 1
                status = HUNTER_MAP.get(str(d.get("status", "unknown")), "likely")
        r["email"], r["email_status"], r["verified_on"] = email, status, today.isoformat()
        checked += 1
    for r in leads:
        if r["email_status"] in counts:
            counts[r["email_status"]] += 1
    out = io.StringIO()
    w = csv.DictWriter(out, LEAD_COLS, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(leads)
    k.write(ctx, "sell/leads.csv", out.getvalue())
    sup = io.StringIO()
    w = csv.DictWriter(sup, ["email_or_domain", "added_on", "reason"], lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(supp)
    k.write(ctx, "sell/suppression.csv", sup.getvalue())
    k.write(ctx, "sell/verification.json", {"checked": checked, **counts, "hunter_credits_used": credits, "date": today.isoformat()})
    note = ("" if hunter else " Hunter step skipped: HUNTER_API_KEY missing.") + (f" {unchecked} left unchecked: DNS did not answer." if unchecked else "")
    return {"summary": f"Verified {checked}: {counts['valid']} valid, {counts['likely']} likely, {counts['risky']} risky, {counts['invalid']} invalid, {counts['bounced']} bounced.{note}", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
