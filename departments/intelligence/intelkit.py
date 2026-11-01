"""Shared helpers for the intelligence run.py scripts: free public APIs, text checks and small statistics.

Stdlib plus requests. Network helpers return None or [] on any failure and stay offline under pytest,
so a script never raises because a source is down. Scripts import this with a sys.path line, see any run.py.
"""
import base64
import csv
import hashlib
import html
import json
import os
import re
import statistics
import sys
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path
from datetime import datetime, timezone
from urllib import robotparser
from urllib.parse import urlparse

import requests

from foundry import jobkit as k
from foundry import util

UA = "foundry-research-bot/1.0 (public business data only; https://github.com/quickplay-studio/foundry)"
CH = "https://api.company-information.service.gov.uk"


def offline():
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def get(url, params=None, headers=None, timeout=20, wait=0):
    """GET returning the response, or None on any failure (and always None under pytest)."""
    if offline():
        return None
    try:
        return requests.get(url, params=params, headers={"User-Agent": UA, **(headers or {})}, timeout=timeout)
    except Exception:  # noqa: BLE001
        return None
    finally:
        time.sleep(wait)


def get_json(url, params=None, headers=None, wait=0, timeout=20):
    r = get(url, params, headers, timeout, wait)
    if r is None or not r.ok:
        return None
    try:
        return r.json()
    except ValueError:
        return None


# small coercions: a model may answer with the wrong type, never trust its shape
def lst(x):
    return x if isinstance(x, list) else []


def dct(x):
    return x if isinstance(x, dict) else {}


def txt(x, n=300):
    return re.sub(r"\s+", " ", str(x)).strip()[:n] if x not in (None, "") else ""


def num(x, default=None):
    try:
        return float(str(x).replace(",", "").replace("£", "").strip())
    except ValueError:
        return default


def domain(url):
    return urlparse(url if "//" in url else "//" + url).netloc.lower().removeprefix("www.")


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w£$€%.]+", " ", str(s).lower())).strip()


def contains(hay, needle):
    n = norm(needle)
    return len(n) > 2 and n in norm(hay)


def strip_html(raw):
    raw = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()


def keywords(text, n=6):
    stop = {"that", "this", "with", "from", "have", "does", "they", "their", "there", "which", "about", "into", "than", "then", "when", "what", "will", "your", "competitor", "competitors", "nobody", "charges", "offers", "does", "app", "apps"}
    seen = []
    for w in re.findall(r"[a-z][a-z\-]{3,}", str(text).lower()):
        if w not in stop and w not in seen:
            seen.append(w)
    return seen[:n]


PERIODS = {"month": "month", "mo": "month", "year": "year", "yr": "year", "annum": "year", "week": "week", "wk": "week", "user": "seat", "seat": "seat"}


def gbp_month(price, period):
    """Monthly GBP: annual over 12, weekly x 52 / 12, a one-off spread over 12 months, per seat as monthly; None for usage or unclear."""
    return None if period in ("usage", "unclear") else round({"year": price / 12, "week": price * 52 / 12, "one-off": price / 12}.get(period, price), 2)


def unit_price(money):
    """A unit price in pounds a month that a money line hopes for, or None when it only gives a revenue target."""
    for m in re.finditer(r"£\s?(\d[\d,]*(?:\.\d+)?)\s*(?:/|per|a)?\s*(month|mo|year|yr|annum|week)?", str(money), re.I):
        v, unit = float(m.group(1).replace(",", "")), (m.group(2) or "").lower()
        if v < 200 and (unit or re.search(r"subscription|monthly|/m\b", str(money), re.I)):
            return gbp_month(v, PERIODS.get(unit, "month"))
    return None


def is_b2b(ctx):
    if str(ctx["idea"].get("business_model", "")).lower() == "b2b":
        return True
    return str(dct(k.read(ctx, "audit.json", {})).get("business_model", "")).lower() == "b2b"


def quartiles(vals):
    v = sorted(vals)
    if not v:
        return None
    if len(v) == 1:
        return dict(min=v[0], p25=v[0], median=v[0], p75=v[0], max=v[0])
    q = statistics.quantiles(v, n=4, method="inclusive")
    return dict(min=v[0], p25=q[0], median=q[1], p75=q[2], max=v[-1])


def cell(x):
    return txt(x, 160).replace("|", "/")


def table(head, rows):
    return ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(cell(c) for c in r) + " |" for r in rows]


def cap_words(text, limit):
    """Keep whole lines until the word limit, so a page never overruns its skill's size rule."""
    out, used = [], 0
    for line in text.splitlines():
        used += len(line.split())
        if used > limit:
            out.append("(trimmed to fit the size limit)")
            break
        out.append(line)
    return "\n".join(out)


def finger(url):
    u = re.sub(r"[?&](utm_[a-z]+|fbclid|gclid|ref)=[^&]*", "", str(url).lower().split("#")[0]).rstrip("/?&")
    return hashlib.sha1(u.encode()).hexdigest()[:16]


def read_csv(ctx, rel):
    path = ctx["folder"] / rel
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_jsonl(ctx, rel):
    text = k.read(ctx, rel, "") or ""
    out = []
    for line in text.splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def append_jsonl(ctx, rel, rows):
    """Append-only file: read what is there, add the rows, write the whole file once."""
    text = (k.read(ctx, rel, "") or "").rstrip("\n")
    lines = ([text] if text else []) + [json.dumps(r, ensure_ascii=False) for r in rows]
    k.write(ctx, rel, "\n".join(lines))


def accounts(ctx, limit=5, done_rel=None):
    """Target accounts from sell/accounts.csv (domain, company_number, company), else sell/market-map.csv. Skips finished ones."""
    rows = read_csv(ctx, "sell/accounts.csv") or read_csv(ctx, "sell/market-map.csv")
    out = []
    for r in rows:
        name = txt(r.get("company") or r.get("name"), 120)
        if not name:
            continue
        slug = util.slugify(name)
        if done_rel and (ctx["folder"] / done_rel.format(slug=slug)).exists():
            continue
        out.append({"name": name, "slug": slug, "domain": txt(r.get("domain"), 120).lower(), "number": txt(r.get("company_number"), 12), "row": r})
    return out[:limit]


# search and stores
def hn(query, tags="story", days=365, n=20, by_date=False):
    """Hacker News Algolia: {total, hits, points} for the last `days`, or None when unreachable."""
    ts = int(time.time()) - days * 86400
    d = get_json("https://hn.algolia.com/api/v1/" + ("search_by_date" if by_date else "search"), {"query": query, "tags": tags, "hitsPerPage": n, "numericFilters": f"created_at_i>{ts}"})
    if not isinstance(d, dict):
        return None
    hits = [{"title": txt(h.get("title") or h.get("story_title"), 160), "text": txt(strip_html(h.get("comment_text") or h.get("story_text") or ""), 400),
             "url": f"https://news.ycombinator.com/item?id={h.get('objectID')}", "points": h.get("points") or 0, "date": (h.get("created_at") or "")[:10]} for h in lst(d.get("hits"))]
    return {"total": int(d.get("nbHits") or 0), "hits": hits, "points": sum(h["points"] for h in hits)}


def hn_link(query):
    return "https://hn.algolia.com/?dateRange=pastYear&type=story&query=" + requests.utils.quote(query)


def hn_monthly(query, months=12):
    """Monthly story counts, oldest first: a demand series when Google Trends is not available."""
    now, out = int(time.time()), []
    for i in range(months, 0, -1):
        lo, hi = now - i * 30 * 86400, now - (i - 1) * 30 * 86400
        d = get_json("https://hn.algolia.com/api/v1/search", {"query": query, "tags": "story", "hitsPerPage": 0, "numericFilters": f"created_at_i>{lo},created_at_i<={hi}"})
        if not isinstance(d, dict):
            return []
        out.append({"month": datetime.fromtimestamp(hi, timezone.utc).strftime("%Y-%m"), "value": int(d.get("nbHits") or 0)})
    return out


_REDDIT_JSON_DOWN = []  # set once the JSON API answers 403 in this process (GitHub runners, every time)
_REDDIT_RSS_DOWN = []  # set once the feed is still throttled after one wait
ATOM = "{http://www.w3.org/2005/Atom}"


def reddit_rss(query, n=25, sort="top", t="year"):
    """Reddit's search feed (search.rss), which answers GitHub runners when the JSON API returns 403. Same rows as reddit(),
    with score 0 because the feed carries none; None when the feed is blocked too."""
    if _REDDIT_RSS_DOWN:
        return None
    params = {"q": query, "t": t, "sort": sort, "limit": n}
    r = get("https://www.reddit.com/search.rss", params, headers={"User-Agent": util.BROWSER_UA}, wait=6)
    if r is not None and r.status_code == 429:  # the feed is throttled per address; runners share theirs, so wait once as told (a minute at most)
        try:
            pause = min(60, max(5, int(r.headers.get("Retry-After", "20"))))
        except ValueError:
            pause = 20
        time.sleep(pause)
        r = get("https://www.reddit.com/search.rss", params, headers={"User-Agent": util.BROWSER_UA}, wait=6)
    if os.environ.get("FOUNDRY_PROBE_DEBUG"):
        print("reddit rss: " + ("no response" if r is None else f"HTTP {r.status_code}, {len(r.text)} bytes, retry-after {r.headers.get('Retry-After')}"), file=sys.stderr)
    if r is None or not r.ok or "<feed" not in r.text[:400]:
        if r is not None and r.status_code in (403, 429):
            _REDDIT_RSS_DOWN.append(r.status_code)  # still throttled after the wait: stop asking in this process
        return None
    try:
        root = ET.fromstring(r.content)
    except ET.ParseError:
        return None
    out = []
    for e in list(root.iter(ATOM + "entry"))[:n]:
        link = next((a.get("href", "") for a in e.findall(ATOM + "link") if a.get("href")), "")
        cat = e.find(ATOM + "category")
        sub = (cat.get("label", "") if cat is not None else "").lstrip("r/") or (re.search(r"/r/([^/]+)/", link) or [None, ""])[1]
        body = html.unescape(re.sub(r"<[^>]+>", " ", (e.findtext(ATOM + "content") or "")))
        body = re.sub(r"\s+", " ", re.sub(r"submitted by\s+.*?\[link\].*?\[comments\]", " ", body)).strip()
        title = txt(e.findtext(ATOM + "title"), 200)
        if not util.on_topic(query, title, body, sub):
            continue  # the feed ranks loosely: a post sharing no word with the query is noise
        out.append({"title": title, "text": txt(body, 500), "url": link, "score": 0, "sub": sub, "date": (e.findtext(ATOM + "updated") or "")[:10]})
    return out


def reddit(query, n=25, sort="top", t="year"):
    """Reddit public JSON (about 10 requests a minute, so each call waits 6 seconds), falling back to the search feed
    where the JSON API is blocked (GitHub runners); None when both are."""
    if not _REDDIT_JSON_DOWN:
        r = get("https://www.reddit.com/search.json", {"q": query, "t": t, "sort": sort, "limit": n}, wait=6)
        if r is not None and r.status_code in (403, 429):
            _REDDIT_JSON_DOWN.append(r.status_code)
        d = None
        if r is not None and r.ok:
            try:
                d = r.json()
            except ValueError:
                d = None
        if isinstance(d, dict):
            out = []
            for c in lst(dct(d.get("data")).get("children")):
                p = dct(c.get("data"))
                out.append({"title": txt(p.get("title"), 200), "text": txt(p.get("selftext"), 500), "url": "https://www.reddit.com" + str(p.get("permalink", "")),
                            "score": int(p.get("score") or 0), "sub": p.get("subreddit", ""), "date": datetime.fromtimestamp(p.get("created_utc") or 0, timezone.utc).strftime("%Y-%m-%d")})
            return out
    if offline():
        return None
    return reddit_rss(query, n, sort, t)


def app_row(r):
    return {"app_id": str(r.get("trackId", "")), "name": txt(r.get("trackName"), 80), "url": r.get("trackViewUrl", ""), "seller_url": r.get("sellerUrl", ""),
            "price": float(r.get("price") or 0), "currency": r.get("currency", "GBP"), "rating": float(r.get("averageUserRating") or 0),
            "rating_count": int(r.get("userRatingCount") or 0), "updated": (r.get("currentVersionReleaseDate") or "")[:10], "description": txt(r.get("description"), 700)}


def appstore(term, n=10):
    d = get_json("https://itunes.apple.com/search", {"term": term, "country": "gb", "entity": "software", "limit": n}, wait=3)
    return None if not isinstance(d, dict) else [app_row(r) for r in lst(d.get("results")) if isinstance(r, dict)]


def lookup(app_id):
    d = get_json("https://itunes.apple.com/lookup", {"id": app_id, "country": "gb"}, wait=3)
    rows = lst(dct(d).get("results"))
    return app_row(rows[0]) if rows and isinstance(rows[0], dict) else None


def reviews(app_id, max_stars=2):
    """Recent 1 and 2 star App Store reviews from the customer reviews RSS: [{stars, title, text, url}] or None."""
    url = f"https://itunes.apple.com/gb/rss/customerreviews/id={app_id}/sortby=mostrecent/json"
    d = get_json(url, wait=3)
    if not isinstance(d, dict):
        return None
    entries = dct(d.get("feed")).get("entry")
    entries = [entries] if isinstance(entries, dict) else lst(entries)
    out = []
    for e in entries:
        stars = int(num(dct(dct(e).get("im:rating")).get("label"), 0) or 0)
        if 0 < stars <= max_stars:
            out.append({"stars": stars, "title": txt(dct(dct(e).get("title")).get("label"), 120), "text": txt(dct(dct(e).get("content")).get("label"), 400), "url": url,
                        "id": txt(dct(dct(e).get("id")).get("label"), 40), "date": txt(dct(dct(e).get("updated")).get("label"), 10)})
    return out


# pages
_robots = {}


def allowed(url):
    u = urlparse(url)
    base = f"{u.scheme}://{u.netloc}"
    if base not in _robots:
        r, rp = get(base + "/robots.txt", timeout=10), robotparser.RobotFileParser()
        rp.parse(r.text.splitlines() if r is not None and r.ok else (["User-agent: *", "Disallow: /"] if r is not None and r.status_code in (401, 403) else []))
        _robots[base] = rp
    return _robots[base].can_fetch(UA, url)


def page_text(url, limit=6000):
    """Page text after a robots.txt check: None when forbidden, '' when it could not be read."""
    if not allowed(url):
        return None
    r = get(url, timeout=25)
    return strip_html(r.text)[:limit] if r is not None and r.ok else ""


_urls = {}


def check_url(url):
    """(status, text) for a link: HEAD, then GET for the text. Status None under pytest, 0 when unreachable after a retry. Cached."""
    if url in _urls or offline():
        return _urls.get(url, (None, ""))
    hdr = {"User-Agent": UA}
    for _ in range(2):
        try:
            h = requests.head(url, headers=hdr, timeout=15, allow_redirects=True)
            if h.status_code in (404, 410):
                _urls[url] = (h.status_code, "")
            else:
                r = requests.get(url, headers=hdr, timeout=25)
                _urls[url] = (r.status_code, strip_html(r.text)[:60000] if r.ok else "")
            return _urls[url]
        except Exception:  # noqa: BLE001
            time.sleep(2)
    _urls[url] = (0, "")
    return _urls[url]


class Credits:
    """Caps the Firecrawl-capable calls of one job. `used` counts one credit per call while a key is set (an upper bound)."""

    def __init__(self, cap):
        self.cap, self.calls = cap, 0

    @property
    def used(self):
        return self.calls if k.secret("FIRECRAWL_API_KEY") else 0

    def search(self, query, n=5, topic="general"):
        if self.calls >= self.cap:
            return []
        self.calls += 1
        return k.search(query, n, topic)

    def fetch(self, url, limit=8000):
        if self.calls >= self.cap or not allowed(url):
            return ""
        self.calls += 1
        return k.fetch(url, limit)


# official data
def ch_get(path, params=None):
    """Companies House API (free key as the basic-auth user); None without a key or on failure."""
    key = k.secret("COMPANIES_HOUSE_API_KEY")
    if not key:
        return None
    auth = {"Authorization": "Basic " + base64.b64encode(f"{key}:".encode()).decode()}
    return get_json(CH + path, params, auth, wait=0.6)


def fx_gbp(code):
    """GBP per unit of a currency from Frankfurter (ECB rates, free, no key), or None."""
    code = str(code).upper()
    if code in ("GBP", ""):
        return 1.0
    for url, params in (("https://api.frankfurter.dev/v1/latest", {"base": code, "symbols": "GBP"}), ("https://api.frankfurter.app/latest", {"from": code, "to": "GBP"})):
        rate = dct(dct(get_json(url, params)).get("rates")).get("GBP")
        if rate:
            return float(rate)
    return None


def trends(phrases, baseline, geo="GB"):
    """Google Trends through pytrends, guarded. Returns a dict or a short reason string."""
    if offline():
        return "offline"
    try:
        from pytrends.request import TrendReq
    except Exception:  # noqa: BLE001
        return "pytrends not installed on this runner"
    try:
        pt = TrendReq(hl="en-GB", tz=0)

        def frame(ph, tf):
            for attempt in (1, 2):
                try:
                    pt.build_payload([ph, baseline], geo=geo, timeframe=tf)
                    return pt.interest_over_time()
                except Exception as exc:  # noqa: BLE001
                    if attempt == 1 and "429" in str(exc):
                        time.sleep(60)
                        continue
                    raise

        months, levels, base_levels, weekly = {}, [], [], []
        for ph in phrases[:3]:
            df = frame(ph, "today 12-m")
            vals = [float(v) for v in df[ph].tolist()]
            if not vals:
                continue
            weekly = weekly or vals
            levels.append(statistics.mean(vals))
            base_levels.append(statistics.mean(float(v) for v in df[baseline].tolist()) or 0.01)
            for d, v in zip(df.index, vals):
                months.setdefault(d.strftime("%Y-%m"), []).append(v)
            time.sleep(2)
        if not levels:
            return "pytrends returned no data"
        first, last = statistics.mean(weekly[:13]), statistics.mean(weekly[-13:])
        direction = "rising" if last > first * 1.2 + 0.5 else "falling" if last < first * 0.8 - 0.5 else "flat"
        five = frame(phrases[0], "today 5-y")
        by_moy = {}
        for d, v in zip(five.index, [float(x) for x in five[phrases[0]].tolist()]):
            by_moy.setdefault(d.month, []).append(v)
        avg = {m: statistics.mean(v) for m, v in by_moy.items()}
        peak = max(avg, key=avg.get) if avg else 0
        seasonal = bool(avg) and statistics.mean(avg.values()) > 0 and avg[peak] > 1.4 * statistics.mean(avg.values())
        return {"level": round(statistics.mean(levels) / statistics.mean(base_levels), 2), "direction": direction,
                "seasonality": f"peaks in month {peak}" if seasonal else "none seen",
                "monthly": [{"month": m, "value": round(statistics.mean(v), 1)} for m, v in sorted(months.items())]}
    except Exception as exc:  # noqa: BLE001
        return f"pytrends failed: {type(exc).__name__}"


# news, job boards, DNS, certificates, GitHub
def news(term, days=3):
    """Google News RSS items for a term in the last `days`: [{title, url, source, date}] or None."""
    r = get("https://news.google.com/rss/search", {"q": f'"{term}"', "hl": "en-GB", "gl": "GB", "ceid": "GB:en"})
    if r is None or not r.ok or b"<!DOCTYPE" in r.content[:300] or b"<!ENTITY" in r.content:
        return None
    try:
        root = ET.fromstring(r.content)
    except ET.ParseError:
        return None
    out = []
    for it in root.iter("item"):
        try:
            ts = parsedate_to_datetime(it.findtext("pubDate")).timestamp()
        except (TypeError, ValueError):
            ts = 0
        if ts and ts < time.time() - days * 86400:
            continue
        out.append({"title": txt(it.findtext("title"), 200), "url": it.findtext("link") or "", "source": txt(it.findtext("source"), 60), "date": datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d") if ts else ""})
    return out


def jobs(name, domain_name=""):
    """Open roles from Greenhouse, Lever or Ashby (free, keyless) under likely board tokens: (board, [{title, dept, url, text}]) or ('', [])."""
    base = re.sub(r"[^a-z0-9]", "", name.lower())
    tokens = list(dict.fromkeys(t for t in (domain_name.split(".")[0] if domain_name else "", base, re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")) if t))[:3]
    for t in tokens:
        g = dct(get_json(f"https://boards-api.greenhouse.io/v1/boards/{t}/jobs", {"content": "true"}))
        if lst(g.get("jobs")):
            return f"greenhouse:{t}", [{"title": txt(j.get("title"), 100), "dept": txt(dct((lst(j.get("departments")) or [{}])[0]).get("name"), 60) or "other", "url": j.get("absolute_url", ""),
                                       "text": strip_html(html.unescape(str(j.get("content", ""))))[:3000]} for j in lst(g["jobs"]) if isinstance(j, dict)]
        lv = get_json(f"https://api.lever.co/v0/postings/{t}", {"mode": "json"})
        if isinstance(lv, list) and lv:
            return f"lever:{t}", [{"title": txt(j.get("text"), 100), "dept": txt(dct(j.get("categories")).get("department") or dct(j.get("categories")).get("team"), 60) or "other", "url": j.get("hostedUrl", ""), "text": txt(j.get("descriptionPlain"), 3000)} for j in lv if isinstance(j, dict)]
        ab = dct(get_json(f"https://api.ashbyhq.com/posting-api/job-board/{t}"))
        if lst(ab.get("jobs")):
            return f"ashby:{t}", [{"title": txt(j.get("title"), 100), "dept": txt(j.get("department") or j.get("team"), 60) or "other", "url": j.get("jobUrl", ""), "text": txt(j.get("descriptionPlain"), 3000)} for j in ab["jobs"] if isinstance(j, dict)]
    return "", []


def dns(name, rtype):
    d = get_json("https://dns.google/resolve", {"name": name, "type": rtype})
    return [txt(a.get("data"), 300) for a in lst(dct(d).get("Answer")) if isinstance(a, dict)]


def subdomains(domain_name):
    """Subdomains from certificate transparency (crt.sh is slow and flaky: one retry, then [])."""
    for _ in range(2):
        r = get("https://crt.sh/", {"q": f"%.{domain_name}", "output": "json"}, timeout=45)
        if r is not None and r.ok:
            try:
                names = {n.strip().lower().lstrip("*.") for row in r.json() for n in str(dct(row).get("name_value", "")).splitlines()}
            except ValueError:
                return []
            return sorted(n for n in names if n.endswith(domain_name))[:60]
        time.sleep(3)
    return []


def github(path, params=None):
    tok = k.secret("GH_TOKEN")
    return get_json("https://api.github.com" + path, params, {"Accept": "application/vnd.github+json", **({"Authorization": f"Bearer {tok}"} if tok else {})}, wait=0.3)


def private_repo(ctx):
    """True only when the venture folder sits in the private data checkout, so sheets about people never reach a public repo."""
    try:
        return util.VENTURES.resolve() in Path(ctx["folder"]).resolve().parents
    except OSError:
        return False


# Companies House and SEC
SUFFIX = re.compile(r"\b(limited|ltd|plc|llp|inc|corp|co)\b\.?", re.I)
CH_WEB = "https://find-and-update.company-information.service.gov.uk/company/"


def company_key(n):
    return norm(SUFFIX.sub("", str(n)))


def resolve(name, number=""):
    """Entity resolution: Companies House (needs the key), then SEC EDGAR tickers. status: resolved, ambiguous or not found."""
    uk_ok = bool(k.secret("COMPANIES_HOUSE_API_KEY"))
    if uk_ok and number:
        p = dct(ch_get(f"/company/{number}"))
        if p.get("company_name"):
            return {"status": "resolved", "country": "UK", "name": p["company_name"], "number": number, "address": txt(dct(p.get("registered_office_address")).get("locality"), 60), "next_due": dct(p.get("accounts")).get("next_due", ""), "source": CH_WEB + number}
    if uk_ok:
        exact = [i for i in map(dct, lst(dct(ch_get("/search/companies", {"q": name, "items_per_page": 8})).get("items"))) if company_key(i.get("title", "")) == company_key(name)]
        cand = [{"name": i.get("title"), "number": i.get("company_number"), "address": txt(i.get("address_snippet"), 100)} for i in exact]
        if len(exact) > 1:
            return {"status": "ambiguous", "candidates": cand}
        if exact:
            return {"status": "resolved", "country": "UK", "name": exact[0]["title"], "number": exact[0]["company_number"], "address": txt(exact[0].get("address_snippet"), 100), "source": CH_WEB + str(exact[0]["company_number"])}
    tick = dct(get_json("https://www.sec.gov/files/company_tickers.json"))
    us = [v for v in map(dct, tick.values()) if company_key(v.get("title", "")) == company_key(name)]
    if len(us) == 1:
        return {"status": "resolved", "country": "US", "name": us[0]["title"], "cik": str(us[0].get("cik_str", "")).zfill(10), "ticker": us[0].get("ticker", ""), "source": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={us[0].get('cik_str')}"}
    if len(us) > 1:
        return {"status": "ambiguous", "candidates": [{"name": v.get("title"), "ticker": v.get("ticker")} for v in us]}
    return {"status": "not found", "uk_checked": uk_ok}


def ch_filings(number, n=40):
    out = []
    for i in map(dct, lst(dct(ch_get(f"/company/{number}/filing-history", {"items_per_page": n})).get("items"))):
        out.append({"type": i.get("type", ""), "date": i.get("date", ""), "description": txt(i.get("description"), 80), "url": f"{CH_WEB}{number}/filing-history/{i.get('transaction_id', '')}", "doc": dct(i.get("links")).get("document_metadata", "")})
    return out


def ch_officers(number):
    """Name, role and appointment dates only: never date of birth or address."""
    return [{"name": txt(o.get("name"), 80), "role": txt(o.get("officer_role"), 40), "appointed": o.get("appointed_on", ""), "resigned": o.get("resigned_on", "")}
            for o in map(dct, lst(dct(ch_get(f"/company/{number}/officers", {"items_per_page": 50})).get("items")))]


def ixbrl(text):
    """Headline figures from an iXBRL accounts file: reads ix:nonFraction tags, applies scale and sign. {} when none are tagged."""
    want = {"turnover": ("turnover", "revenue"), "profit": ("profitloss", "profitlossbeforetax"), "cash": ("cashbankonhand", "cashbankinhand", "cash"), "net_assets": ("netassetsliabilities",), "employees": ("averagenumberemployees",)}
    out = {}
    for m in re.finditer(r"<ix:nonFraction([^>]*)>(.*?)</ix:nonFraction>", text, re.S | re.I):
        attrs, body = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
        name = (re.search(r'name="[^":]*:?([^"]+)"', attrs) or [None, ""])[1].lower()
        v = num(body)
        for key, names in want.items():
            if v is not None and key not in out and any(name.startswith(n) for n in names):
                out[key] = v * 10 ** int((re.search(r'scale="(-?\d+)"', attrs) or [0, 0])[1]) * (-1 if 'sign="-"' in attrs else 1)
    return out


def ch_accounts_doc(doc_path):
    """The accounts document as XHTML through the Document API (the redirect to storage drops the auth header), or ''."""
    key = k.secret("COMPANIES_HOUSE_API_KEY")
    if not key or not doc_path:
        return ""
    auth = {"Authorization": "Basic " + base64.b64encode(f"{key}:".encode()).decode(), "Accept": "application/xhtml+xml"}
    r = get("https://document-api.company-information.service.gov.uk" + doc_path.replace("https://document-api.company-information.service.gov.uk", "") + "/content", headers=auth, timeout=40, wait=0.6)
    return r.text if r is not None and r.ok else ""


# technology fingerprints: a table kept as data beside tech-stack-detection, plus foundry/data/fingerprints.json if the build adds it
def fingerprints():
    rows = []
    for p in (Path(__file__).resolve().parent / "companies" / "tech-stack-detection" / "fingerprints.json", util.ROOT / "foundry" / "data" / "fingerprints.json"):
        try:
            rows += [r for r in json.loads(p.read_text(encoding="utf-8")) if isinstance(r, dict)]
        except (OSError, ValueError):
            continue
    return rows


def detect_tools(headers="", cookies=(), page="", mx=(), txt_records=(), cnames=None):
    """Match the fingerprint table. Header, script and DNS evidence is high confidence, meta and body hints medium. Drops tools with no evidence."""
    pools = {"header": str(headers), "cookie": " ".join(cookies), "html": page, "script": page, "meta": page, "dns_mx": " ".join(mx), "dns_txt": " ".join(txt_records), "dns_cname": " ".join(f"{a} {b}" for a, b in (cnames or {}).items())}
    found = {}
    for f in fingerprints():
        m = re.search(f.get("pattern", "(?!)"), pools.get(f.get("kind"), ""), re.I | re.M)
        if m and f.get("tool") not in found:
            found[f["tool"]] = {"category": f.get("category", ""), "tool": f["tool"], "evidence": f["kind"].replace("dns_", "dns ") + ": " + txt(m.group(0), 60), "confidence": "medium" if f["kind"] in ("meta", "html") else "high"}
    return list(found.values())
