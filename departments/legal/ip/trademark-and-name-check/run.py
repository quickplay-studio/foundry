"""Trademark and Name Check: GitHub implementation of departments/legal/ip/trademark-and-name-check/SKILL.md.

A screening search, not clearance. Variants are made in code; the free model adds translations and judges web hits.
Registers that cannot be read (UK IPO, EUIPO, WIPO, Google Play) become unverified with the exact searches listed,
never green. Keyed or live API calls (Companies House, iTunes, RDAP, GitHub) run only when their secret is present,
so tests stay offline. It never buys a domain or files a mark. Not legal advice.
"""
import datetime as dt
import difflib
import json
import re
from urllib.parse import urlparse

import requests

from foundry import jobkit as k

CLASSES = [(9, "software and apps", r"app|software|ios|android|download"), (42, "software as a service", r"saas|web app|platform|dashboard|api|tool|software"),
           (35, "online services and advice", r"service|advice|marketplace|shop|store|agency"), (36, "finance", r"invest|payment|money|budget|bank|loan|insur|spend"),
           (41, "education and entertainment", r"learn|course|education|video|channel|entertain|game"), (44, "health", r"health|medical|fitness|wellbeing|nutrition")]
SWAPS = (("ph", "f"), ("f", "ph"), ("ck", "k"), ("c", "k"), ("k", "c"), ("s", "z"), ("y", "i"), ("ee", "ea"), ("er", "or"))
TLDS = ("com", "co.uk", "app")
RANK = {"green": 0, "amber": 1, "red": 2}
NOTICE = "Not legal advice. Drafts are checked by Charlie or a solicitor before use. This is a screening search, not clearance."


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def phon(s):
    """Simplified Metaphone: sounds-alike key."""
    s = re.sub(r"[^a-z]", "", str(s).lower())
    s = re.sub(r"c(?=[eiy])", "s", s)
    for a, b in (("ph", "f"), ("ck", "k"), ("kn", "n"), ("wr", "r"), ("gh", ""), ("x", "ks"), ("q", "k"), ("z", "s"), ("c", "k"), ("y", "i"), ("w", "v")):
        s = s.replace(a, b)
    s = re.sub(r"(.)\1+", r"\1", s)
    return s[:1] + re.sub(r"[aeiou]", "", s[1:])


def sim(a, b):
    a, b = norm(re.sub(r"\b(limited|ltd|llp|plc|inc)\b", "", str(a).lower())), norm(b)
    if not a or not b:
        return 0.0
    return 1.0 if a == b or phon(a) == phon(b) else difflib.SequenceMatcher(None, a, b).ratio()


def variants(name, translations=()):
    words, out = name.split(), [name]
    out += ["".join(words), " ".join(words), "-".join(words), name + "s" if not name.endswith("s") else name[:-1]]
    joined = "".join(words).lower()
    out += [joined.replace(a, b, 1) for a, b in SWAPS if a in joined] + [re.sub(r"(.)\1", r"\1", joined, count=1)]
    out += [str(t)[:40] for t in translations]
    seen, res = set(), []
    for v in out:
        if v and v.lower() not in seen:
            seen.add(v.lower())
            res.append(v)
    return res[:14]


def score(s):
    return "red" if s >= 0.92 else "amber" if s >= 0.75 else None


def get(url, **kw):
    try:
        return requests.get(url, timeout=15, **kw)
    except Exception:  # noqa: BLE001
        return None


def check(name, vs, live, ch_key, token, day, full):
    """Hits and unverified notes for one name. Each hit: register, query, class, hit, owner, status, score."""
    hits, unver, used = [], [], []
    def mk(reg, q, cls, found, owner, status, sc):
        if not any(h["register"] == reg and h["hit"] == found for h in hits):  # one row per hit, not per variant
            hits.append({"register": reg, "query": q, "class": cls, "hit": found, "owner": owner, "status": status, "score": sc})

    if ch_key:
        used.append(f"Companies House Public Data API (searched {day})")
        for v in vs[:6 if full else 2]:
            r = get("https://api.company-information.service.gov.uk/search/companies", params={"q": v, "items_per_page": 5}, auth=(ch_key, ""))
            if r is None or not r.ok:
                unver.append(f"Companies House search for '{v}' failed")
                continue
            for it in r.json().get("items", []):
                s, live_co = sim(it.get("title", ""), name), it.get("company_status") == "active"
                sc = "red" if s >= 0.92 and live_co else "amber" if s >= 0.75 or (s >= 0.92 and not live_co) else None
                if sc:
                    mk("Companies House", v, "n/a", f"{it.get('title')} ({it.get('company_number')})", "company", it.get("company_status", ""), sc)
    else:
        unver.append("Companies House: COMPANIES_HOUSE_API_KEY missing; search https://find-and-update.company-information.service.gov.uk/ for each variant by hand")
    if live:
        used.append(f"RDAP via rdap.org, iTunes Search API, GitHub API (called {day})")
        d = norm(name)
        taken = []
        for tld in TLDS:
            r = get(f"https://rdap.org/domain/{d}.{tld}")
            if r is None or r.status_code not in (200, 404):
                unver.append(f"RDAP lookup for {d}.{tld} failed")
            elif r.status_code == 200:
                taken.append(tld)
                mk("Domain (RDAP)", f"{d}.{tld}", "n/a", "registered", "unknown", "taken", "amber")
        for cc in ("gb", "us") if full else ("gb",):
            r = get("https://itunes.apple.com/search", params={"term": name, "entity": "software", "country": cc, "limit": 8})
            if r is None or not r.ok:
                unver.append(f"iTunes search ({cc}) failed")
                continue
            for it in r.json().get("results", []):
                sc = score(sim(it.get("trackName", ""), name))
                if sc:
                    mk("iTunes (App Store)", f"{name} ({cc})", "9", it.get("trackName", ""), it.get("sellerName", ""), "live", sc)
        r = get(f"https://api.github.com/users/{d}", headers={"Authorization": f"Bearer {token}"})
        if r is None or r.status_code not in (200, 404):
            unver.append(f"GitHub name check for {d} failed")
        elif r.status_code == 200:
            mk("GitHub user or organisation", d, "n/a", "name taken", "unknown", "taken", "amber")
    else:
        unver.append("Domains (RDAP), iTunes and GitHub name checks only run on the Actions runner (GH_TOKEN present); check .com, .co.uk and .app, the App Store and GitHub by hand")
    return hits, unver, used


def main(ctx):
    idea, brain = ctx["idea"], ctx["brain"]
    day = dt.date.today().isoformat()
    title = str(idea.get("name") or idea.get("title") or ctx["slug"])
    if ":" in title and not idea.get("name"):
        a, b = [x.strip() for x in title.split(":", 1)]
        title = b if 0 < len(b.split()) <= 4 else a
    backups = idea.get("backup_names") or idea.get("alt_names") or (re.search(r"backup names?\s*[:\-]\s*(.+)", brain, re.I) or [None, ""])[1]
    backups = [b.strip() for b in (re.split(r"[;,]", backups) if isinstance(backups, str) else backups) if isinstance(b, str) and b.strip()][:2]
    text = (json.dumps(idea, ensure_ascii=False) + " " + brain).lower()
    classes = sorted({c for c, _, pat in CLASSES if re.search(pat, text)} | ({9, 42} if str(idea.get("kind", "app")).lower() in ("app", "saas", "service") else set()))
    cnames = ", ".join(f"{c} ({n})" for c, n, _ in CLASSES if c in classes) or "to set from the goods and services"
    eu = bool(re.search(r"\beu\b|europe|germany|france|spain|ireland|netherlands", text))
    token, ch_key = k.secret("GH_TOKEN"), k.secret("COMPANIES_HOUSE_API_KEY")
    rows = k.search(f'"{title}" {idea.get("kind", "")} {str(idea.get("problem", ""))[:60]}', 5)
    ans = k.ask("You help screen a business name for a UK solo founder. Not legal advice. Give obvious translations of the name, and judge each web result: is it a business or product trading under this or a very similar name in the same field? "
                "Return JSON only: {\"translations\": [\"...\"], \"passing_off\": [{\"url\": \"...\", \"name\": \"...\", \"same_field\": true, \"identical\": false}], \"reason\": \"<one sentence>\"}\n\nNAME\n" + title + "\n\nPRODUCT\n"
                + json.dumps({key: idea.get(key) for key in ("kind", "problem", "who")}, ensure_ascii=False)[:600] + "\n\nWEB RESULTS\n" + "\n".join(f"{r.get('url')} | {r.get('title')} | {str(r.get('content'))[:200]}" for r in rows))
    ans = ans if isinstance(ans, dict) else {}
    tr = [t for t in ans.get("translations", []) if isinstance(t, str)] if isinstance(ans.get("translations"), list) else []
    live = bool(token)
    results = {}
    for n in [title] + backups:
        results[n] = check(n, variants(n, tr if n == title else ()), live, ch_key, token, day, n == title)
    hits, unver = list(results[title][0]), list(results[title][1])
    for h in hits:
        h["name"] = title
    used = list(results[title][2])
    for n in backups:
        hits += [dict(h, name=n) for h in results[n][0]]
    if not rows or not isinstance(ans.get("passing_off"), list):
        unver.append("Passing off: no web search or model answer this run; search the name plus the product category by hand")
    else:
        used.append(f"Web search for passing off (searched {day})")
        for p in ans["passing_off"]:
            if isinstance(p, dict) and p.get("url") in [r.get("url") for r in rows]:
                sc = "red" if p.get("identical") is True and p.get("same_field") is True else "amber"
                hits.append({"register": "Web (passing off)", "query": title, "class": "n/a", "hit": str(p.get("name", ""))[:60], "owner": urlparse(str(p["url"])).netloc, "status": "trading", "score": sc, "name": title})
    searches = [f"UK IPO 'Search for a trade mark' (https://www.gov.uk/search-for-trademark): '{v}' exact and similar sounding, classes {', '.join(map(str, classes))}" for v in variants(title, tr)[:6]]
    unver += ["UK IPO register is a dynamic form that cannot be read by fetch: run these searches by hand"] + searches
    unver += ["EUIPO eSearch plus and the WIPO Global Brand Database: run by hand (EU is a market)"] if eu else ["EUIPO and WIPO: not required, the brain names no EU market"]
    unver.append("Google Play has no API and its search page is not reliably readable: search https://play.google.com/store/search?c=apps by hand")
    count = lambda n, sc: sum(1 for h in hits if h["name"] == n and h["score"] == sc)
    ranking = sorted([title] + backups, key=lambda n: (count(n, "red"), count(n, "amber"), 0 if n == title else 1))
    flag = "stop" if count(title, "red") else "caution"
    reds, ambers = count(title, "red"), count(title, "amber")
    reason = f"{reds} red and {ambers} amber hits for {title}; {len(unver)} unverified notes" + ("; best backup: " + (ranking[0] if ranking[0] != title else "none better") if flag == "stop" and backups else "") + ("; COMPANIES_HOUSE_API_KEY missing, Companies House skipped" if not ch_key else "") + ". The UK IPO register was not read, so the flag cannot be clear."
    cell = lambda v: str(v).replace("|", "/").replace("\n", " ")
    lines = [f"FLAG: {flag}", "", reason, "", NOTICE, "", f"Classes: {cnames}.", "", "## Names ranked", *[f"{i}. {n}: {count(n, 'red')} red, {count(n, 'amber')} amber" for i, n in enumerate(ranking, 1)], "",
             "## Hits", "| Register | Query | Class | Hit | Owner | Status | Score |", "|---|---|---|---|---|---|---|",
             *([f"| {cell(h['register'])} | {cell(h['query'])} | {h['class']} | {cell(h['hit'])} | {cell(h['owner'])} | {cell(h['status'])} | {h['score']} |" for h in sorted(hits, key=lambda h: -RANK[h["score"]]) if h["name"] == title] or ["| none found | | | | | | |"]), "",
             "## Unverified checks", *[f"- {u}" for u in unver], "", "## Domain prices", "- Not read: no registrar API. Charlie checks prices and buys nothing here.", "",
             "## Sources", *[f"- {u}" for u in used], "- Registers listed above were not read.", "", f"Checked on {day}."]
    k.write(ctx, "clear/name-check.md", "\n".join(lines))
    k.write(ctx, "clear/name-check.json", {"name": title, "flag": flag, "notice": NOTICE, "hits": hits, "unverified": unver, "reason": reason, "checked_on": day, "variants": variants(title, tr), "classes": classes,
                                           "ranking": ranking, "sources_used": used})
    return {"summary": f"Name check for {title}: {flag}. {reason}"[:300], "flag": flag}


if __name__ == "__main__":
    k.run(main)
