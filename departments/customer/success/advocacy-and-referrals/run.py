"""Advocacy and Referrals: GitHub implementation of departments/customer/success/advocacy-and-referrals/SKILL.md.

Picks up to 10 happy, settled users, drafts one honest ask each (review, referral or testimonial) and
drafts case studies from quotes Charlie has recorded. No reward is ever offered for a review. Asks are
never sent: Charlie sends them from support/advocacy.md. user_id only, no contact details.
"""
import re
from datetime import datetime, timedelta, timezone

import requests

from foundry import jobkit as k, util

REWARD = r"free|discount|reward|credit|voucher|gift|prize|£\s?\d|cash|bonus|% off|win\b"
SENSITIVE = r"money|£|salary|debt|health|doctor|medical|diagnos|therapy|child|children|kids|son\b|daughter"
FALLBACK = {"review": "Thank you for using {t} for {n} days. If it has helped, would you leave an honest review, good or bad? {link}",
            "referral": "Thank you for sticking with {t} for {n} days. If you know someone who would find it useful, this link is yours to share: {link}",
            "testimonial": "Thank you for the kind words about {t}. May I quote you, in your own words, on the site? Say no if you prefer. {link}"}


def d(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def hogql(query):
    key, pid = k.secret("POSTHOG_API_KEY"), k.secret("POSTHOG_PROJECT_ID")
    for host in ("us", "eu") if key and pid else ():
        try:
            r = requests.post(f"https://{host}.posthog.com/api/projects/{pid}/query/", json={"query": {"kind": "HogQLQuery", "query": query}},
                              headers={"Authorization": f"Bearer {key}"}, timeout=60)
            if r.ok:
                return r.json().get("results", [])
        except Exception:  # noqa: BLE001
            continue
    return None


def ask_ok(body, kind):
    """The hard rules in code: short, no reward anywhere, an honest review only."""
    low = body.lower()
    return len(body.split()) <= 60 and not re.search(REWARD, low) and (kind not in ("review",) or "honest" in low)


def main(ctx):
    today = datetime.now(timezone.utc).date()
    health = k.read(ctx, "support/health.json", {}) or {}
    adv = k.read(ctx, "support/advocacy.json", None)
    adv = adv if isinstance(adv, dict) else {}
    adv.setdefault("asks", []), adv.setdefault("proof", []), adv.setdefault("referrals", {"clicks": 0, "signups": 0, "paid": 0})
    ev = k.read(ctx, "support/events.json", {}) or {}
    names = [ev.get("signup", "signed_up"), ev.get("paid", "subscription_started")]
    if all(re.fullmatch(r"[A-Za-z0-9_]{2,40}", str(n)) for n in names):
        got = hogql(f"SELECT countIf(event = '$pageview'), countIf(event = '{names[0]}'), countIf(event = '{names[1]}') FROM events WHERE properties.ref IS NOT NULL AND timestamp > now() - INTERVAL 90 DAY")
        if got and len(got[0]) == 3:
            adv["referrals"] = dict(zip(("clicks", "signups", "paid"), (int(x or 0) for x in got[0])))
    tickets = [t for t in (k.read(ctx, "support/tickets.json", {}) or {}).get("tickets", []) if isinstance(t, dict) and t.get("user_id")]
    busy = {t["user_id"] for t in tickets if (d(t.get("received")) or today) >= today - timedelta(days=60) and (t.get("sentiment", 0) <= -1 or t.get("status") == "open")}
    praise = {t["user_id"] for t in tickets if t.get("category") == "praise"}
    asked = {a.get("user_id") for a in adv["asks"] if not a.get("sent") or (d(a.get("sent")) or today) >= today - timedelta(days=90)}
    folder = ctx["folder"] / "support" / "health-history"
    greens = {}
    for p in sorted(folder.glob("*.json")) if folder.exists() else []:
        if d(p.stem) and (today - d(p.stem)).days <= 30:
            for a in (util.read_json(p, {}) or {}).get("accounts", []):
                if isinstance(a, dict):
                    greens[a.get("user_id")] = greens.get(a.get("user_id"), True) and a.get("band") == "green"
    eligible = [a for a in health.get("accounts", []) if isinstance(a, dict) and a.get("band") == "green" and a.get("tenure_days", 0) >= 30 and "not-activated" not in a.get("flags", [])
                and a["user_id"] not in busy | asked and greens.get(a["user_id"], True)]
    eligible.sort(key=lambda a: (a["user_id"] not in praise, not a.get("plan"), -a.get("score", 0)))
    picks, title = eligible[:10], ctx["idea"].get("title", "the app")
    site = str(ctx["idea"].get("url") or "{site}").rstrip("/")
    rev = re.search(r"https?://\S+", next((ln for ln in ctx["brain"].splitlines() if re.search(r"review|trustpilot|app store|play store", ln, re.I) and "http" in ln), ""))
    links = {"review": rev.group(0).rstrip(".,)") if rev else "{review_link}", "testimonial": "{tally_form_link}"}
    for a in picks:
        a["kind"] = "testimonial" if a["user_id"] in praise else "review" if a.get("tenure_days", 0) >= 90 else "referral"
        a["link"] = f"{site}?ref={util.slugify(a['user_id'])[:12]}" if a["kind"] == "referral" else links[a["kind"]]
    ans = k.ask('Write one ask per user in plain UK English, 60 words or fewer, no exclamation marks: thank them for something specific, make one ask, include their link. Ask for an honest review, never a positive one. '
                'Never offer a reward, discount or free time. Return JSON only: {"drafts": [{"user_id": "<id>", "body": "..."}]}\n'
                f"PRODUCT: {title}. {str(ctx['idea'].get('problem', ''))[:200]}\nUSERS: {[(a['user_id'], a['kind'], a.get('tenure_days'), a['link']) for a in picks]}") if picks else None
    made = {str(x.get("user_id")): str(x.get("body", "")) for x in (ans.get("drafts") if isinstance(ans, dict) and isinstance(ans.get("drafts"), list) else []) if isinstance(x, dict)}
    drafts = []
    for a in picks:
        body = made.get(a["user_id"], "").replace(chr(33), ".")
        if not (body and a["link"] in body and ask_ok(body, a["kind"])):
            body = FALLBACK[a["kind"]].format(t=title, n=a.get("tenure_days", 30), link=a["link"])
        drafts.append((a, body))
        adv["asks"].append({"user_id": a["user_id"], "type": a["kind"], "sent": None, "outcome": "drafted"})
    cases = []
    for pr in [p for p in adv["proof"] if isinstance(p, dict) and p.get("permission") == "pending" and p.get("quote")][:3]:
        q = str(pr["quote"]).strip()
        if re.search(SENSITIVE, q.lower()):
            cases.append((pr.get("user_id"), None, "refused: money, health or children detail"))
            continue
        res = k.ask('Draft a case study of 150 words or fewer from this quote only. Use the quote verbatim, add no claim, number or detail the person did not say. Return JSON only: {"case_study": "..."}\n' + f"QUOTE: {q}")
        text = str(res.get("case_study", "")) if isinstance(res, dict) else ""
        extra = set(re.findall(r"\d+", text)) - set(re.findall(r"\d+", q))
        cases.append((pr.get("user_id"), text if text and q in text and len(text.split()) <= 150 and not extra else None, "permission pending"))
    md = [f"# Advocacy {util.today()}", "", "Asks are never sent by this job. Charlie sends each one and confirms permission for every named quote.", ""]
    md += ["## Drafted asks", *([f"### {a['user_id']} ({a['kind']}, {a.get('tenure_days')} days, score {a.get('score')})\n\n{b}\n" for a, b in drafts] or ["none eligible", ""])]
    md += ["## Case study drafts", *([f"### {u} ({why})\n\n{t or 'not drafted: it failed the verbatim check or the topic is off limits'}\n" for u, t, why in cases] or ["none", ""])]
    md += ["## Proof bank", *([f"- {p.get('user_id')}: \"{p.get('quote')}\" ({p.get('source', '')}, permission {p.get('permission')})" for p in adv["proof"] if isinstance(p, dict)] or ["- empty"]), "",
           f"Referrals, last 90 days: {adv['referrals']['clicks']} clicks, {adv['referrals']['signups']} sign-ups, {adv['referrals']['paid']} paid."]
    adv["updated"] = util.now()
    k.write(ctx, "support/advocacy.json", adv)
    k.write(ctx, "support/advocacy.md", "\n".join(md))
    return {"summary": (f"Advocacy: {len(drafts)} asks drafted, none sent." if drafts else "Advocacy: none eligible yet.") + f" {len(cases)} case study drafts.", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
