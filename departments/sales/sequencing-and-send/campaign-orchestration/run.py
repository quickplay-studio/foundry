"""Campaign Orchestration: GitHub implementation of departments/sales/sequencing-and-send/campaign-orchestration/SKILL.md.

One campaign per segment per tier (A and B; C and X get none) in sell/campaigns.json, status draft only:
campaign-launch is the only job that goes further, and even it stops at an approval file. Deterministic:
the same inputs give the same file. PECR in code: lead_ids holds only corporate subscribers with a
valid or likely, non-blank email who are not suppressed; everyone else can only get non-email touches
(non_email_lead_ids) or waits. Stop rules cover every channel. Cohorts start on Tuesdays in sizes that
keep daily sends under the deliverability cap, and a lead joins one cohort once. Campaigns already
approved or live are kept as they are, and new leads go into a new campaign with a numbered suffix.
"""
import csv
import datetime as dt
import io
import re

from foundry import jobkit as k
from foundry import util

WINDOW = "Tue-Thu 08:00-10:00 Europe/London"
STOP = ["reply", "unsubscribe", "bounce", "meeting"]
A_PLAN = [(0, "email", 1), (1, "linkedin", "connect"), (3, "email", 2), (5, "linkedin", "dm"), (8, "email", 3), (10, "call", "call"), (15, "email", 4)]
B_PLAN = [(0, "email", 1), (1, "linkedin", "connect"), (3, "email", 2), (8, "email", 3), (15, "email", 4)]


def b2b(ctx):
    audit = k.read(ctx, "audit.json", {}) or {}
    return "b2b" in (str(ctx["idea"].get("business_model", "")).lower(), str(audit.get("business_model", "")).lower())


def table(ctx, rel):
    return list(csv.DictReader(io.StringIO(k.read(ctx, rel, "") or "")))


def asset(ctx, kind, seg):
    """Relative path under sell/ of the sequence file for this segment, or ''."""
    for stem in dict.fromkeys((util.slugify(seg), re.sub(r"[^a-z0-9]+", "-", seg.lower()).strip("-"), seg.lower(), seg)):
        if (ctx["folder"] / "sell" / "sequences" / f"{kind}-{stem}.md").exists():
            return f"sequences/{kind}-{stem}.md"
    return ""


def shift(day):
    """Cohorts start on a Tuesday; a weekend touch moves to the Monday."""
    wd = (1 + day) % 7
    return day + (2 if wd == 5 else 1 if wd == 6 else 0)


def main(ctx):
    if not b2b(ctx):
        return {"skipped": "no business buyer"}
    leads = table(ctx, "sell/leads.csv")
    if not leads:
        return {"skipped": "no sell/leads.csv rows yet: run list-building and fit-scoring first"}
    deliv = k.read(ctx, "sell/deliverability.json", {}) or {}
    cap = int(deliv["daily_cap"]) if isinstance(deliv, dict) and isinstance(deliv.get("daily_cap"), (int, float)) else None
    assumed = cap is None
    cap = 5 if assumed else cap  # the first warm-up step when deliverability has not run
    old = k.read(ctx, "sell/campaigns.json", {}) or {}
    keep = [c for c in old.get("campaigns", []) if isinstance(c, dict) and c.get("status") in ("approved", "live")] if isinstance(old, dict) else []
    frozen = {i for c in keep for i in c.get("lead_ids", []) + c.get("non_email_lead_ids", [])}
    plans, missing, built = [], [], []
    for seg in sorted({r["segment"] for r in leads if r["segment"]}):
        for tier, plan in (("A", A_PLAN), ("B", B_PLAN)):
            mine = sorted((r for r in leads if r["segment"] == seg and r["tier"] == tier and r["suppressed"] != "yes" and r["id"] not in frozen),
                          key=lambda r: (-int(r["fit_score"] or 0), r["id"]))
            email = [r["id"] for r in mine if r["subscriber_type"] == "corporate" and r["email"] and r["email_status"] in ("valid", "likely")]
            other = [r["id"] for r in mine if r["id"] not in email and ((r["linkedin_url"] and r["subscriber_type"] == "corporate") or (r["phone"] and tier == "A"))]
            if email or other:
                plans.append((seg, tier, plan, email, other))
    n_email = max(1, sum(1 for p in plans if p[3]))
    for seg, tier, plan, email, other in plans:
        files = {kind: asset(ctx, kind, seg) for kind in ("email", "linkedin", "call", "video")}
        gone = [f"{kind}-{util.slugify(seg)}" for kind, path in files.items() if not path and (kind in ("email", "linkedin") or (tier == "A" and kind in ("call", "video")))]
        missing += gone
        touches = []
        for day, channel, step in plan:
            if not files[channel]:
                continue
            t = {"day": shift(day), "channel": channel, "step": step}
            if channel != "email":
                t["by"] = "charlie"
            if channel == "call":
                t["after"] = "TPS and CTPS screening"
            if channel == "email" and step == 3 and tier == "A" and files["video"]:
                t["video"] = True
            touches.append(t)
        base = f"{util.slugify(seg)}-{tier}"
        taken = {c.get("id") for c in keep}
        cid, n = base, 1
        while cid in taken:
            n += 1
            cid = f"{base}-{n}"
        camp_cap = max(1, cap // n_email)
        size = max(1, camp_cap // 2)  # weekly cohorts overlap on at most two email days
        built.append({"id": cid, "segment": seg, "tier": tier, "sequence": files["email"], "touches": touches, "lead_ids": email, "non_email_lead_ids": other,
                      "cohort_size": size, "cohorts": [{"number": i + 1, "lead_ids": email[s:s + size]} for i, s in enumerate(range(0, len(email), size))],
                      "stop_on": STOP, "daily_cap": camp_cap, "window": WINDOW, "status": "draft"})
    if not built and not keep:
        return {"skipped": "no tier A or B lead can take a touch yet (needs fit-scoring, and email-verification for email touches)"}
    k.write(ctx, "sell/campaigns.json", {"slug": ctx["slug"], "generated": dt.date.today().isoformat(), "campaigns": keep + built,
                                         "missing_assets": sorted(set(missing)), "daily_cap_assumed": assumed})
    emailed = sum(len(c["lead_ids"]) for c in built)
    return {"summary": f"{len(built)} draft campaigns ({emailed} email leads, cap {cap} a day{', assumed: no deliverability.json yet' if assumed else ''}), {len(keep)} approved or live kept, {len(set(missing))} missing assets.", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
