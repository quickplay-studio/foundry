"""Probe the keyless data sources from wherever this runs (a GitHub runner, normally) and print one line each.

    python -m foundry.probe            # all sources
    python -m foundry.probe reddit     # only the names containing the word

Each line: name, HTTP status, bytes, a count of what the scraper would find, and a short sample. Used by
smoke.yml to see which routes work from GitHub before a job relies on them; nothing is written.
"""
import json
import re
import sys

import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
BOT = {"User-Agent": "foundry-research-bot/1.0 (public business data only; https://github.com/quickplay-studio/foundry)"}
Q = "meal planning app"


def probe(name, method, url, count=None, **kw):
    try:
        r = requests.request(method, url, timeout=25, **kw)
        n = count(r.text) if count else ""
        sample = re.sub(r"\s+", " ", r.text[:160])
        print(f"{name:28} {r.status_code} {len(r.text):>8}  found {str(n):>4}  {sample}")
        return r
    except Exception as exc:  # noqa: BLE001
        print(f"{name:28} ERR {type(exc).__name__}: {str(exc)[:100]}")
        return None


def json_count(key):
    def f(text):
        try:
            d = json.loads(text)
        except ValueError:
            return "nojson"
        cur = d
        for k in key.split("."):
            cur = cur.get(k, []) if isinstance(cur, dict) else []
        return len(cur) if isinstance(cur, list) else "?"
    return f


SOURCES = [
    ("reddit www search.json", "GET", "https://www.reddit.com/search.json", json_count("data.children"), {"params": {"q": Q, "limit": 5}, "headers": BOT}),
    ("reddit old search.json", "GET", "https://old.reddit.com/search.json", json_count("data.children"), {"params": {"q": Q, "limit": 5}, "headers": UA}),
    ("reddit search.rss", "GET", "https://www.reddit.com/search.rss", lambda t: len(re.findall(r"<entry>", t)), {"params": {"q": Q}, "headers": UA}),
    ("reddit sub top.json", "GET", "https://www.reddit.com/r/smallbusiness/top.json", json_count("data.children"), {"params": {"t": "week", "limit": 5}, "headers": UA}),
    ("pullpush submissions", "GET", "https://api.pullpush.io/reddit/search/submission/", json_count("data"), {"params": {"q": Q, "size": 5}, "headers": BOT}),
    ("pullpush comments", "GET", "https://api.pullpush.io/reddit/search/comment/", json_count("data"), {"params": {"q": Q, "size": 5}, "headers": BOT}),
    ("jina reader reddit", "GET", "https://r.jina.ai/https://www.reddit.com/search/?q=" + Q.replace(" ", "+"), lambda t: len(re.findall(r"r/\w+", t)), {"headers": {"Accept": "text/plain", **BOT}}),
    ("jina reader page", "GET", "https://r.jina.ai/https://www.bbc.co.uk/news", lambda t: len(t.splitlines()), {"headers": {"Accept": "text/plain", **BOT}}),
    ("hn algolia", "GET", "https://hn.algolia.com/api/v1/search", json_count("hits"), {"params": {"query": Q, "hitsPerPage": 5}}),
    ("ddg html", "POST", "https://html.duckduckgo.com/html/", lambda t: len(re.findall(r'class="result__a"', t)), {"data": {"q": Q}, "headers": UA}),
    ("ddg lite", "GET", "https://lite.duckduckgo.com/lite/", lambda t: len(re.findall(r"result-link", t)), {"params": {"q": Q}, "headers": UA}),
    ("bing html", "GET", "https://www.bing.com/search", lambda t: len(re.findall(r'<li class="b_algo"', t)), {"params": {"q": Q, "setlang": "en-GB"}, "headers": UA}),
    ("brave html", "GET", "https://search.brave.com/search", lambda t: len(re.findall(r'class="snippet', t)), {"params": {"q": Q, "source": "web"}, "headers": UA}),
    ("mojeek api", "GET", "https://www.mojeek.com/search", lambda t: len(re.findall(r'class="results-standard"|<li class="r', t)), {"params": {"q": Q, "fmt": "html"}, "headers": UA}),
    ("google play page", "GET", "https://play.google.com/store/apps/details", lambda t: len(re.findall(r"review", t, re.I)), {"params": {"id": "com.mealime", "hl": "en_GB"}, "headers": UA}),
    ("trustpilot page", "GET", "https://uk.trustpilot.com/review/www.hellofresh.co.uk", lambda t: len(re.findall(r'data-service-review-card', t)), {"headers": UA}),
    ("companies house html", "GET", "https://find-and-update.company-information.service.gov.uk/search", lambda t: len(re.findall(r'class="type-company"', t)), {"params": {"q": "hellofresh"}, "headers": UA}),
    ("appstore search", "GET", "https://itunes.apple.com/search", json_count("results"), {"params": {"term": Q, "country": "gb", "entity": "software", "limit": 3}}),
    ("google trends rss", "GET", "https://trends.google.com/trending/rss", lambda t: len(re.findall(r"<item>", t)), {"params": {"geo": "GB"}, "headers": UA}),
    ("ons nomis", "GET", "https://www.nomisweb.co.uk/api/v01/dataset/NM_1_1.jsonstat.json", lambda t: "ok" if t.startswith("{") else "?", {"params": {"geography": "2092957699", "sex": "7", "item": "1", "measures": "20100", "time": "latest"}}),
    ("youtube rss", "GET", "https://www.youtube.com/feeds/videos.xml", lambda t: len(re.findall(r"<entry>", t)), {"params": {"channel_id": "UCBJycsmduvYEL83R_U4JriQ"}, "headers": UA}),
]


def parsed():
    """What the scrapers make of the routes that answered: the rows a job would get."""
    from foundry import util
    sys.path.insert(0, str(util.DEPARTMENTS / "intelligence"))
    import intelkit
    for name, rows in (("bing_search", util.bing_search(Q, 3)), ("keyless_search", util.keyless_search(Q, 3)), ("reddit_rss", (intelkit.reddit_rss(Q, 3) or [])[:3])):
        print(f"{name:28} {len(rows)} rows")
        for r in rows:
            print("   ", json.dumps({k: str(v)[:90] for k, v in r.items()}, ensure_ascii=False))


def main(argv=None):
    only = (argv or [])[:1]
    for name, method, url, count, kw in SOURCES:
        if only and only[0].lower() not in name.lower():
            continue
        probe(name, method, url, count, **kw)
    if not only:
        parsed()


if __name__ == "__main__":
    main(sys.argv[1:])
