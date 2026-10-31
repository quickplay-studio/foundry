"""Platform and Ad Compliance: GitHub implementation of departments/legal/compliance/platform-and-ad-compliance/SKILL.md.

Checks draft launch assets against a checklist kept in code (repeatable), reads each store and ad policy page fresh
with its date, and lets the free model add claims the patterns missed. It never submits, publishes or spends.
A failed read, no assets or a silent model is caution, never clear. Not legal advice.
"""
import datetime as dt
import json
import re
from urllib.parse import urlparse

from foundry import jobkit as k

PAGES = {  # label, url, search query, official hosts, word the page must contain
    "cap": ("CAP Code (non-broadcast)", "https://www.asa.org.uk/codes-and-rulings/advertising-codes/non-broadcast-code.html", "CAP Code non-broadcast advertising rules ASA", (".asa.org.uk",), "advert"),
    "cma": ("CMA pricing and reviews guidance", "", "CMA guidance unfair commercial practices drip pricing online reviews DMCC Act", (".gov.uk",), "price"),
    "apple": ("Apple App Store Review Guidelines", "https://developer.apple.com/app-store/review/guidelines/", "Apple App Store Review Guidelines", (".apple.com",), "guideline"),
    "google": ("Google Play Developer Policy Center", "https://play.google.com/about/developer-content-policy/", "Google Play Developer Policy Center", (".google.com",), "policy"),
    "meta": ("Meta Advertising Standards", "https://transparency.meta.com/policies/ad-standards/", "Meta Advertising Standards", (".meta.com", ".facebook.com"), "advert"),
    "gads": ("Google Ads policies", "https://support.google.com/adspolicy/answer/6008942", "Google Ads policies overview", (".google.com",), "polic"),
    "tiktok": ("TikTok advertising policies", "https://ads.tiktok.com/help/article/tiktok-advertising-policies-ad-creatives-landing-page", "TikTok advertising policies", (".tiktok.com",), "advert"),
}
PLANNED = {"apple": r"\bios\b|iphone|app store|apple", "google": r"android|google play|play store", "meta": r"\bmeta\b|facebook|instagram", "gads": r"google ads|adwords|search ads", "tiktok": r"tiktok"}
CHECKS = {
    "apple": ["Privacy policy link and data collection labels match", "Account deletion inside the app", "In-app purchase for digital goods, with subscription disclosure", "Sign-in options", "User-generated content: report, block, filter", "Kids category limits if children use it", "No misleading metadata"],
    "google": ["Data safety form matches the privacy policy", "Payments and subscriptions rules (Play Billing for digital goods)", "Families policy if children may use it", "No deceptive behaviour; listing and metadata rules"],
    "meta": ["Personalised ads and sensitive targeting limits", "Restricted categories: financial services verification, health, gambling, age-restricted", "Landing page matches the ad", "No prohibited claims"],
    "gads": ["Restricted categories and verification", "Landing page matches the ad", "No prohibited or misleading claims", "Personalised ads limits"],
    "tiktok": ["Ad creative and landing page policies", "Branded content disclosure"],
}
# id, pattern, rule, severity, required change
RULES = [
    ("superlative", r"\b(best|#1|number one|no\.? ?1|world'?s (best|first|leading)|leading|fastest|cheapest|most accurate)\b", "CAP Code section 3: objective claims need evidence on file", "caution", "Remove the claim or file the evidence"),
    ("free", r"\bfree\b", "CAP Code section 3 and DMCC Act: say what the free offer costs and when it ends", "caution", "State the conditions and the price after the trial next to the word free"),
    ("money", r"guaranteed (returns|profit|income)|get rich|earn £?\d|make money fast|passive income|double your", "CAP Code sections 3 and 14: money claims", "stop", "Remove the claim"),
    ("health", r"\b(cures?|treats|heals?|prevents|lose weight|burn fat|detox|clinically proven)\b", "CAP Code section 15 and health claims rules", "stop", "Remove the claim; only authorised claims allowed"),
    ("urgency", r"only \d+ left|limited time|hurry|ends (today|tonight|soon)|countdown|last chance", "DMCC Act: no fake urgency", "caution", "Remove it unless it is true and evidenced"),
    ("reviews", r"testimonial|\b\d(\.\d)? ?(stars?|/5)\b|5-star|customers love|\breviews?\b", "DMCC Act and CAP Code: genuine, not incentivised, evidence on file", "caution", "Use only real, unpaid reviews with consent on file"),
    ("price", r"was £|\d+% off|save £?\d|from £|only £", "DMCC Act: total price up front, genuine reference price", "caution", "Show the full price including VAT and fees; prove the earlier price"),
    ("comparison", r"better than|\bvs\.? |unlike [A-Z]|than (any|other)", "CAP Code section 3: comparisons must be verifiable", "caution", "Name what is compared and keep the evidence"),
    ("children", r"\bkids?\b|children|under 1[368]", "CAP Code section 5 and store families policies", "caution", "Check targeting, tone and the families policy"),
    ("marketing", r"newsletter|email list|\bsms\b|text message|subscribe", "UK GDPR and PECR: consent, unsubscribe, cookies", "caution", "Confirm consent wording and an unsubscribe on every message"),
    ("targeting", r"target(ing)? (people|users) (with|who have) (debt|health|depress|anxiet|religio)", "Meta and Google sensitive targeting limits", "caution", "Remove the sensitive attribute from targeting"),
]
INFLUENCER = r"influencer|creator brief|sponsored|gifted|affiliate|ambassador"
LABEL = r"#ad\b|#advert|#sponsored|paid partnership|\(ad\)|\bad:|#gifted"
ORDER = {"clear": 0, "caution": 1, "stop": 2}
NOTICE = "Not legal advice. Drafts are checked by Charlie or a solicitor before use."


def worse(a, b):
    return a if ORDER.get(a, 1) >= ORDER.get(b, 1) else b


def clean(t):
    return re.sub(r"\s+", " ", str(t)).strip()


def sentence(text, m):
    start = max(text.rfind(c, 0, m.start()) for c in ".!?\n") + 1
    ends = [i for i in (text.find(c, m.end()) for c in ".!?\n") if i >= 0]
    return clean(text[start:(min(ends) + 1 if ends else len(text))])[:160]


def read_pages(keys):
    out, day = {}, dt.date.today().isoformat()
    for key in keys:
        label, url, query, hosts, word = PAGES[key]
        text = k.fetch(url, 30000) if url else ""
        if len(text) < 200:
            for r in k.search(query, 3):
                u = r.get("url", "")
                if ("." + urlparse(u).netloc.lower()).endswith(hosts):
                    url, text = u, k.fetch(u, 30000)
                    if len(text) >= 200:
                        break
        ok = len(text) >= 200 and word in text.lower()
        out[key] = {"label": label, "url": url, "read_on": day, "ok": ok}
    return out


def collect(ctx):
    """Draft assets: paths in board.json, outputs of launch jobs, then anything under launch/. {rel path: text}."""
    rels = [a if isinstance(a, str) else str(a.get("path", "")) for a in (ctx["board"].get("assets") or []) if isinstance(a, (str, dict))]
    for j in ctx["board"].get("jobs", []):
        if isinstance(j, dict) and j.get("stage") == "launch":
            rels += [str(o) for o in j.get("outputs", [])]
    launch = ctx["folder"] / "launch"
    if launch.exists():
        rels += [str(p.relative_to(ctx["folder"])) for p in sorted(launch.rglob("*")) if p.suffix in (".md", ".html", ".txt")]
    out = {}
    for rel in rels:
        p = ctx["folder"] / rel
        if rel and p.suffix in (".md", ".html", ".txt", ".json") and p.is_file() and not re.search(r"index|queue|publish-log|credits", p.name) and rel not in out and len(out) < 15:
            out[rel] = p.read_text(encoding="utf-8", errors="ignore")[:5000]
    return out


def main(ctx):
    idea, brain = ctx["idea"], ctx["brain"]
    day = dt.date.today().isoformat()
    assets = collect(ctx)
    alltext = (json.dumps(idea.get("channels", "")) + " " + brain + " " + " ".join(assets.values())).lower()
    planned = [p for p, pat in PLANNED.items() if p != "tiktok" and re.search(pat, alltext)] + (["tiktok"] if re.search(PLANNED["tiktok"], alltext) else [])
    guessed = not [p for p in planned if p != "tiktok"]
    if guessed:
        planned = ["apple", "google", "meta", "gads"] + planned
    pages = read_pages(["cap", "cma"] + planned)
    rows = []
    for rel, text in assets.items():
        for rid, pat, rule, sev, change in RULES:
            m = re.search(pat, text, re.I)
            if m:
                rows.append({"asset": rel, "rule": rule, "claim": sentence(text, m), "change": change, "severity": sev})
        if (re.search(INFLUENCER, text + rel, re.I)) and not re.search(LABEL, text, re.I):
            rows.append({"asset": rel, "rule": "CAP Code section 2: marketing must be recognisable (label such as #ad)", "claim": "no disclosure label found", "change": "Add #ad or a paid partnership label at the start", "severity": "stop"})
    screen = k.read(ctx, "clear/regulatory-screen.json")
    for a in (screen.get("areas", []) if isinstance(screen, dict) else []):
        if isinstance(a, dict) and a.get("flag") in ("caution", "stop") and str(a.get("area", "")).startswith(("Financial", "Health", "Gambling", "Children")):
            rows.append({"asset": "all", "rule": f"Restricted category from the regulatory screen: {a['area']}", "claim": str(a.get("finding", ""))[:120], "change": "Platform verification and the specific CAP Code section apply; ASA Copy Advice or a solicitor first", "severity": str(a["flag"])})
    ans = k.ask(
        "You test advertising and store listing claims for a UK solo founder. Not legal advice. Find claims in the assets that break the CAP Code, the DMCC Act or store and ad platform rules and that the listed patterns missed: "
        + ", ".join(r[0] for r in RULES) + ". Quote the claim exactly as written. severity is caution for unsubstantiated or unclear claims and stop for a claim a platform would reject or that breaks the CAP Code. "
        "Return JSON only: {\"rows\": [{\"asset\": \"<path>\", \"rule\": \"...\", \"claim\": \"<exact quote>\", \"change\": \"...\", \"severity\": \"caution|stop\"}], \"flag\": \"clear|caution|stop\", \"reason\": \"<one sentence>\"}\n\nASSETS\n"
        + "\n".join(f"[{rel}]\n{text[:2000]}" for rel, text in assets.items())) if assets else None
    model_ok = isinstance(ans, dict)
    for r in (ans.get("rows", []) if model_ok and isinstance(ans.get("rows"), list) else []):
        if isinstance(r, dict) and str(r.get("asset")) in assets and clean(r.get("claim", "")).lower() in clean(assets[str(r["asset"])]).lower() and r.get("claim"):
            rows.append({"asset": str(r["asset"]), "rule": str(r.get("rule", ""))[:160], "claim": clean(r["claim"])[:160], "change": str(r.get("change", ""))[:160], "severity": "stop" if r.get("severity") == "stop" else "caution"})
    why, flag = [], "clear"
    if not assets:
        flag = "caution"
        why.append("no draft launch assets found in board.json or launch/, so nothing was checked")
    elif not model_ok:
        flag = "caution"
        why.append("no free model second opinion; the code checklist ran alone")
    unread = [p["label"] for p in pages.values() if not p["ok"]]
    if unread:
        flag = "caution"
        why.append("policy pages not read: " + ", ".join(unread))
    for r in rows:
        flag = worse(flag, r["severity"])
    n_stop, n_caution = sum(r["severity"] == "stop" for r in rows), sum(r["severity"] == "caution" for r in rows)
    if rows:
        why.append(f"{n_stop} stop and {n_caution} caution findings")
    if guessed:
        why.append("no platform named in the brief, so all four are checked")
    reason = "; ".join(why) or "All assets checked, every policy page read, no findings."
    status = {}
    for p in planned:
        s = "stop" if n_stop else ("caution" if n_caution else "clear")
        status[p] = {"status": s if pages[p]["ok"] else worse(s, "caution"), "verified": pages[p]["ok"], "source": pages[p]["url"], "read_on": pages[p]["read_on"]}
    cell = lambda v: str(v).replace("|", "/").replace("\n", " ")
    sources = [f"- {p['label']}: {p['url']} (read {p['read_on']})" if p["ok"] else f"- NOT READ: {p['label']}, {p['url'] or 'no page found'} (tried {p['read_on']})" for p in pages.values()]
    lines = [f"FLAG: {flag}", "", reason, "", NOTICE, "", "Nothing here submits, publishes or spends. Charlie approves every ad budget line and every store submission.", "",
             "## Fix list", "| Asset | Rule | Claim | Required change | Severity |", "|---|---|---|---|---|",
             *([f"| {cell(r['asset'])} | {cell(r['rule'])} | {cell(r['claim'])} | {cell(r['change'])} | {r['severity']} |" for r in rows] or ["| none | | | | |"]), "",
             "## Per-platform status", "| Platform | Status | Policy page read |", "|---|---|---|",
             *[f"| {pages[p]['label']} | {v['status']}{'' if v['verified'] else ' (policy unverified)'} | {v['source'] or 'none'} |" for p, v in status.items()], "",
             "## Platform checklists (Charlie ticks before submitting)", *[f"- [ ] {pages[p]['label']}: {c}" for p in planned for c in CHECKS.get(p, [])], "",
             "## Stays with Charlie", "- Approving each ad budget line and recording the campaign id after he pays.", "- Store developer accounts and their fees (check current amounts; nothing paid before revenue).",
             "- Answering a store rejection; ASA Copy Advice or a solicitor for a borderline claim.", "", "## Assets checked", *([f"- {rel}" for rel in assets] or ["- none"]), "", "## Sources read", *sources, "", f"Checked on {day}."]
    k.write(ctx, "clear/platform-and-ad-compliance.md", "\n".join(lines))
    k.write(ctx, "clear/platform-and-ad-compliance.json", {"flag": flag, "notice": NOTICE, "reason": reason, "checked_on": day, "assets_checked": list(assets), "rows": rows, "platforms": status,
                                                           "sources_read": [{"label": p["label"], "url": p["url"], "read_on": p["read_on"], "ok": p["ok"]} for p in pages.values()]})
    return {"summary": f"Platform and ad compliance: {flag}. {reason}"[:300], "flag": flag}


if __name__ == "__main__":
    k.run(main)
