"""SEO and GEO: GitHub implementation of departments/marketing/distribution/seo-and-geo/SKILL.md.

Audits our own live page over plain HTTP (html.parser, PageSpeed Insights), then writes a patch pack:
metadata, JSON-LD, sitemap.xml, robots.txt, llms.txt, an answer block and patch.md. Charlie or the Build
session applies it; Charlie submits the sitemap in Search Console himself.
"""
import datetime as dt
import json
import re
from html.parser import HTMLParser

from foundry import jobkit as k

PRICE = re.compile(r"£\s?\d[\d,]*(?:\.\d{1,2})?(?:\s?(?:/|per|a)\s?(?:month|mo|year|yr|week))?", re.I)
STOP = set("a an the and or of to in on for with is are was be it this that you your we our at as by from not no so if do can will how my i".split())


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.h, self.title, self.desc, self.canon, self.lang, self.viewport, self.noalt, self.imgs, self._in = [], "", "", "", "", False, 0, 0, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "meta" and a.get("name") == "description":
            self.desc = a.get("content", "")
        elif tag == "meta" and a.get("name") == "viewport":
            self.viewport = True
        elif tag == "link" and a.get("rel") == "canonical":
            self.canon = a.get("href", "")
        elif tag == "img":
            self.imgs += 1
            self.noalt += 0 if a.get("alt") else 1
        elif tag in ("title", "h1", "h2", "h3"):
            self._in = tag

    def handle_data(self, data):
        if self._in == "title":
            self.title += data
        elif self._in:
            self.h.append((self._in, data.strip()))

    def handle_endtag(self, tag):
        self._in = None if tag == self._in else self._in


def tidy(text):
    return re.sub(r"\s+", " ", re.sub(r"\s*[\u2013\u2014]\s*", ", ", re.sub(r"!+", ".", str(text)).replace(" - ", ", "))).strip()


def trim(text, limit):
    text = tidy(text)
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0].rstrip(",;:")


def audit(site, skipped):
    try:
        r = k.requests.get(site, timeout=20, headers={"User-Agent": "Mozilla/5.0 (Foundry seo audit of our own site)"})
        r.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        skipped.append(f"live page: {type(exc).__name__}")
        return []
    p = Page()
    p.feed(r.text)
    h1s = [t for tag, t in p.h if tag == "h1"]
    order = [int(tag[1]) for tag, _ in p.h]
    checks = [("one H1", len(h1s) == 1, "Use exactly one H1"), ("title 60 characters or fewer", 0 < len(p.title.strip()) <= 60, "Shorten the title"),
              ("meta description 140 to 160", 140 <= len(p.desc) <= 160, "Set a 140 to 160 character description"), ("heading order", all(b - a <= 1 for a, b in zip(order, order[1:])), "Do not skip heading levels"),
              ("alt text on images", p.noalt == 0, f"{p.noalt} of {p.imgs} images lack alt"), ("canonical link", bool(p.canon), "Add a canonical link"),
              ("lang en-GB", p.lang.lower() == "en-gb", "Set lang=\"en-GB\" on html"), ("viewport tag", p.viewport, "Add the viewport meta tag"), ("HTML under 100 KB", len(r.content) < 100000, "Reduce the HTML size")]
    out = [(n, "pass" if ok else "fail", "" if ok else fix) for n, ok, fix in checks]
    try:
        d = k.requests.get("https://www.googleapis.com/pagespeedonline/v5/runPagespeed", params={"url": site, "strategy": "mobile"}, timeout=60).json()
        score = round(d["lighthouseResult"]["categories"]["performance"]["score"] * 100)
        out.append(("PageSpeed mobile performance", "pass" if score >= 90 else "fail", f"score {score}" + ("" if score >= 90 else ", see PageSpeed Insights for fixes")))
    except Exception as exc:  # noqa: BLE001
        skipped.append(f"pagespeed: {type(exc).__name__}")
    return out


def parse_copy(md):
    sec = {m.group(1).strip().lower(): m.group(2) for m in re.finditer(r"^## ([^\n]+)\n(.*?)(?=^## |\Z)", md, re.S | re.M)}
    hero = [re.sub(r"^#+\s*", "", l).strip() for l in sec.get("hero", "").splitlines() if l.strip() and not l.startswith("[")]
    faq = [(q.strip(), a.strip()) for q, a in re.findall(r"^### ([^\n]+)\n(.*?)(?=^### |\Z)", sec.get("faq", ""), re.S | re.M) if a.strip()]
    return hero, faq


def jsonld(kind, title, desc, price, site, faq):
    app = {"@context": "https://schema.org", "@type": "SoftwareApplication" if kind in ("app", "service") else "WebSite", "name": title, "description": desc}
    if site:
        app["url"] = site
    if kind in ("app", "service"):
        app.update(applicationCategory="WebApplication", operatingSystem="Web")
        m = re.search(r"\d[\d,]*(?:\.\d+)?", price or "")
        if m:
            app["offers"] = {"@type": "Offer", "price": f"{float(m.group(0).replace(',', '')):.2f}", "priceCurrency": "GBP", "description": price}
    out = [app]
    if faq:
        out.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]})
    return out


def main(ctx):
    idea, brain = ctx["idea"], ctx["brain"]
    skipped, today = [], dt.date.today().isoformat()
    channels = k.read(ctx, "launch/channels.json", {}) or {}
    site = str(channels.get("site", "")).strip().rstrip("/") if isinstance(channels, dict) else ""
    pages = [str(p).strip("/") for p in channels.get("pages", [])] if isinstance(channels, dict) and isinstance(channels.get("pages"), list) else []
    copy = k.read(ctx, "launch/landing-page.md", "") or ""
    hero, faq = parse_copy(copy)
    audience = k.read(ctx, "launch/insights/audience.json", {}) or {}
    bank = [b for b in audience.get("language_bank", []) if isinstance(b, str) and 1 < len(b.split()) <= 5] if isinstance(audience, dict) else []
    vid = k.read(ctx, "launch/inputs/vidiq-keywords.json", []) or []
    vkeys = [str(r.get("keyword", r) if isinstance(r, dict) else r).lower() for r in vid][:6]
    kws = list(dict.fromkeys(vkeys + bank))
    title_text = tidy(idea.get("title", ctx["slug"]))
    primary = kws[0] if kws else " ".join(w for w in re.findall(r"[a-z']+", str(idea.get("problem", "")).lower()) if w not in STOP)[:40] or title_text.lower()
    secondary = [x for x in kws[1:4]]
    price = (PRICE.search(copy) or PRICE.search(str(idea.get("money", "")) + brain) or [""])[0]
    mvp = idea.get("mvp") if isinstance(idea.get("mvp"), list) and idea.get("mvp") else [str(idea.get("problem", ""))]
    h1 = hero[0] if hero else title_text
    first_lines = " ".join(hero[1:3]) or f"{title_text}: {mvp[0]}"
    answer = k.ask('Return JSON only: {"title": "60 characters or fewer", "description": "140 to 160 characters", "h1": "...", "answer": "a visible answer block of 60 words or fewer: what it is, who it is for, the price, how it works"}. '
                   f"Include the primary phrase '{primary}' once in the title, the description and the H1, with the price or what it does. Use only these facts. No hype, no dashes, no exclamation marks.\n\nBRAIN\n{brain[:2500]}\nCOPY\n{copy[:1500]}\nPRICE\n{price}")
    a = answer if isinstance(answer, dict) else {}
    title = trim(a.get("title") if isinstance(a.get("title"), str) else f"{h1} {price}".strip(), 60)
    desc = trim(a.get("description") if isinstance(a.get("description"), str) else first_lines, 160)
    if len(desc) < 140:
        desc = trim(f"{desc} {price + '. ' if price and price not in desc else ''}{' '.join(str(m).rstrip('.') + '.' for m in mvp[:2])}", 160)
    if primary and primary.lower() not in title.lower():
        title = trim(f"{primary.capitalize()}: {title}", 60)
    block_src = a.get("answer") if isinstance(a.get("answer"), str) else f"{title_text} {str(mvp[0]).rstrip('.').lower()}. It is for {str(idea.get('who', 'people with this problem')).rstrip('.').lower()}. The price is {price or 'not set yet'}."
    block = " ".join(tidy(block_src).split()[:56]) + f" Checked {today}."
    meta = {"site": site, "primary": primary, "secondary": secondary, "title": title, "description": desc, "h1": trim(a.get("h1") if isinstance(a.get("h1"), str) else h1, 70), "answer_block": block, "price": price, "checked": today}
    ld = jsonld(str(idea.get("kind", "app")).lower(), title_text, desc, price, site, faq)
    urls = [site + "/"] + [f"{site}/{p}" for p in pages] if site else ["/"]
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>" for u in urls) + "\n</urlset>"
    robots = "User-agent: *\nAllow: /\n\n# AI crawlers (GPTBot, ClaudeBot, PerplexityBot, Google-Extended) are allowed by default. Charlie: add Disallow lines per crawler to change that.\n" + (f"Sitemap: {site}/sitemap.xml" if site else "# Sitemap: <site>/sitemap.xml (add once launch/channels.json has a site)")
    names = [("Home" if u == site + "/" else u.rstrip("/").rsplit("/", 1)[-1].replace("-", " ").capitalize(), u) for u in urls if site]
    llms = f"# {title_text}\n\n> {block}\n\n## Key pages\n" + ("\n".join(f"- [{n}]({u})" for n, u in names) if names else "- Add pages once the site URL is known")
    rows = audit(site, skipped) if site else []
    report = [f"# SEO and GEO report: {title_text}", f"Checked {today}. " + (f"Live page: {site}" if site else "No site in launch/channels.json, so the live audit was skipped and the pack is written from the copy."), "", "| Check | Result | Fix |", "|---|---|---|"]
    report += [f"| {n} | {r} | {f} |" for n, r, f in rows] or ["| live audit | not run | add a site to launch/channels.json |"]
    report += ["", f"Primary phrase: {primary}. Secondary: {', '.join(secondary) or 'none yet'}."] + (["", "## Skipped"] + [f"- {s}" for s in skipped] if skipped else [])
    repo = f"quickplay-studio/{ctx['slug']}"
    patch = [f"# Patch pack for {repo}", "", "Apply in the site repo. Nothing here is live until you do.", "",
             f"1. In the HTML head of the home page: title `{title}`, meta description `{desc}`, `<link rel=\"canonical\" href=\"{site or '<site>'}/\">`, `<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">`, and `lang=\"en-GB\"` on the html tag.",
             f"2. H1 on the page: `{meta['h1']}`. One H1 only.", "3. JSON-LD: paste the contents of `jsonld.json` as `<script type=\"application/ld+json\">` blocks in the head, one per object.",
             f"4. Near the top of the body, a visible answer block: `<p>{block}</p>`", "5. Add `sitemap.xml`, `robots.txt` and `llms.txt` at the site root (in `public/` for most frameworks).",
             "6. Submit `sitemap.xml` in Google Search Console yourself; it needs your login.", "7. Crawler policy: robots.txt allows AI crawlers by default. Change it if you disagree.", "", "JSON-LD does not promise rich results; llms.txt is a proposed convention with no guaranteed effect."]
    for rel, content in (("report.md", "\n".join(report)), ("metadata.json", meta), ("jsonld.json", ld), ("sitemap.xml", sitemap), ("robots.txt", robots), ("llms.txt", llms), ("patch.md", "\n".join(patch))):
        k.write(ctx, f"launch/seo/{rel}", content)
    fails = sum(1 for _, r, _ in rows if r == "fail")
    return {"summary": f"SEO pack written for '{primary}'. Live audit: {'not run' if not rows else f'{fails} of {len(rows)} checks fail'}. Skipped: {len(skipped)}.", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
