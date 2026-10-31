"""Newsletter and Broadcast: GitHub implementation of departments/marketing/distribution/newsletter-and-broadcast/SKILL.md.

Drafts one issue on the venture's cadence: one lead item, up to two short items, one call to action, with the
lint, link and contrast checks in code. Writes issue.html, issue.txt and meta.json. It never holds the subscriber
list and never sends: Charlie tests and sends from his own email service.
"""
import datetime as dt
import html
import re

from foundry import jobkit as k

BRAND = {"colours": {"bg": "#FFFFFF", "text": "#111111", "accent": "#0B5FFF"}, "font": "Arial, Helvetica, sans-serif"}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
HYPE = re.compile(r"\b(amazing|revolutionary|game[- ]changing|insane|secret|incredible|unbelievable|guaranteed?|life[- ]changing|ultimate|free|act now|winner|limited time|urgent)\b\s*", re.I)
UK = {"color": "colour", "optimize": "optimise", "organize": "organise", "center": "centre", "favorite": "favourite", "analyze": "analyse", "behavior": "behaviour"}
DAYS = {"weekly": 7, "fortnightly": 14, "monthly": 30}


def tidy(text):
    return re.sub(r"\s+", " ", re.sub(r"\s*[\u2013\u2014]\s*", ", ", re.sub(r"!+", ".", str(text)).replace(" - ", ", "))).strip()


def contrast(a, b):
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def clean(text, truth):
    """Voice and spam lint, UK spelling; a sentence with a number the brain lacks is dropped."""
    out = []
    for s in re.split(r"(?<=[.?])\s+", tidy(text)):
        if HYPE.search(s):
            continue
        for us, uk in UK.items():
            s = re.sub(rf"\b{us}", uk, s, flags=re.I)
        if s and all(n in truth for n in re.findall(r"\d+(?:[.,]\d+)*", s)):
            out.append(s)
    return " ".join(out)


def main(ctx):
    folder, idea, brain = ctx["folder"], ctx["idea"], ctx["brain"]
    today = dt.date.today()
    decisions = (re.search(r"^## Decisions\n(.*?)(?=\n## |\Z)", brain, re.S | re.M) or [None, ""])[1].lower()
    cadence = next((d for w, d in DAYS.items() if w in decisions), 14)
    issues = sorted(p.name for p in (folder / "launch/newsletter").glob("????-??-??")) if (folder / "launch/newsletter").is_dir() else []
    if issues and today < dt.date.fromisoformat(issues[-1]) + dt.timedelta(days=cadence):
        return {"skipped": f"next issue is not due until {dt.date.fromisoformat(issues[-1]) + dt.timedelta(days=cadence)}"}
    audience = k.read(ctx, "launch/insights/audience.json", {}) or {}
    perf = k.read(ctx, "launch/insights/performance.md", "") or ""
    updates = k.read(ctx, "launch/inputs/updates.md", "") or ""
    qs = sorted([q for q in (audience.get("questions", []) if isinstance(audience, dict) else []) if isinstance(q, dict) and q.get("theme")], key=lambda q: -(q.get("count") or 0))
    if not (qs or perf.strip() or updates.strip()):
        return {"skipped": "no content source: needs audience.json, performance.md or inputs/updates.md"}
    channels = k.read(ctx, "launch/channels.json", {}) or {}
    site = str(channels.get("site", "")).strip().rstrip("/") if isinstance(channels, dict) else ""
    magnet = k.read(ctx, "launch/lead-magnet/index.json", {}) or {}
    brand = k.read(ctx, "launch/brand.json")
    brand = brand if isinstance(brand, dict) and isinstance(brand.get("colours"), dict) else dict(BRAND)
    col = {key: (brand["colours"].get(key) if HEX.match(str(brand["colours"].get(key, ""))) else BRAND["colours"][key]) for key in BRAND["colours"]}
    link = f"{site}?utm_source=newsletter&utm_medium=email&utm_campaign={today.isoformat()}" if site else ""
    answer = k.ask('Return JSON only: {"subject": "50 characters or fewer", "preheader": "90 characters or fewer", "sections": [{"heading": "...", "body": "..."}], "cta_text": "...", "cta_link": "..."}. '
                   "One issue: a lead item first (a question from the audience answered with facts from the brain, or the best post idea, or a product update), then up to two short items. Body 250 words or fewer in total, one call to action. "
                   "No hype or spam words, no dashes, no exclamation marks, UK English.\n\nTOP QUESTIONS\n" + "; ".join(f"{q['theme']} ({q.get('count', 0)})" for q in qs[:5]) + "\nBEST POSTS\n" + perf[:700] + "\nPRODUCT UPDATES\n" + updates[:700] + "\nBRAIN\n" + brain[:2000])
    a = answer if isinstance(answer, dict) else {}
    truth = brain + " " + updates
    sections = [(tidy(s.get("heading", "")), clean(s.get("body", ""), truth)) for s in (a.get("sections") if isinstance(a.get("sections"), list) else [])[:3] if isinstance(s, dict) and tidy(s.get("heading", ""))]
    sections = [(h, b) for h, b in sections if b]
    template = not sections
    if template:  # lead item from the top question and its brain answer
        theme = qs[0]["theme"] if qs else tidy(idea.get("title", ctx["slug"]))
        mvp = idea.get("mvp") if isinstance(idea.get("mvp"), list) and idea.get("mvp") else [idea.get("problem", "")]
        sections = [(tidy(theme).capitalize(), clean(f"{idea.get('title', '')}: {mvp[0]}. {idea.get('money', '')}", truth))]
    words = 0
    kept = []
    for h, b in sections:
        left = 250 - words
        if left <= 0:
            break
        b = " ".join(b.split()[:left])
        words += len(b.split())
        kept.append((h, b))
    subject = clean(a.get("subject", ""), truth)[:50].rstrip() if isinstance(a.get("subject"), str) and a.get("subject") else ""
    subject = subject or tidy(kept[0][0])[:50]
    pre = (clean(a.get("preheader", ""), truth) or tidy(kept[0][1]))[:90].rstrip()
    cta_text = clean(a.get("cta_text", ""), truth) if isinstance(a.get("cta_text"), str) else ""
    cta_text = cta_text if 0 < len(cta_text.split()) <= 6 else f"See {tidy(idea.get('title', 'the product'))}"
    links = [link] if link else []
    if isinstance(magnet, dict) and magnet.get("theme") and site:
        links.append(f"{site}/guide?utm_source=newsletter&utm_medium=email&utm_campaign={today.isoformat()}")
    ok_links = None
    if links:
        ok_links = True
        for u in links:
            try:
                ok_links = ok_links and k.requests.get(u, timeout=20).status_code == 200
            except Exception:  # noqa: BLE001
                ok_links = False
    lint_ok = not re.search(r"[\u2013\u2014!]", " ".join(h + b for h, b in kept) + subject + pre) and not HYPE.search(" ".join(h + b for h, b in kept) + subject + pre)
    c_ok = contrast(col["text"], col["bg"]) >= 4.5 and contrast("#FFFFFF", col["accent"]) >= 4.5
    e = html.escape
    body_html = "".join(f'<h2 style="margin:24px 0 8px;font-size:20px;color:{col["text"]}">{e(h)}</h2><p style="margin:0 0 12px;font-size:16px;line-height:1.5;color:{col["text"]}">{e(b)}</p>' for h, b in kept)
    button = f'<p style="margin:24px 0"><a href="{e(link)}" style="background:{col["accent"]};color:#FFFFFF;padding:12px 20px;text-decoration:none;display:inline-block;font-size:16px">{e(cta_text)}</a></p>' if link else f'<p style="margin:24px 0;font-size:16px;color:{col["text"]}">{e(cta_text)}</p>'
    footer = f'<p style="font-size:13px;color:{col["text"]};border-top:1px solid #DDDDDD;padding-top:12px">You get this because you signed up for {e(tidy(idea.get("title", ctx["slug"])))}. {{{{unsubscribe_link}}}}</p>'
    page = (f'<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{e(subject)}</title></head>'
            f'<body style="margin:0;background:{col["bg"]};font-family:{brand.get("font", BRAND["font"])}"><span style="display:none">{e(pre)}</span><table role="presentation" width="100%"><tr><td align="center">'
            f'<table role="presentation" width="600" style="max-width:600px;width:100%"><tr><td style="padding:24px">{body_html}{button}{footer}</td></tr></table></td></tr></table></body></html>')
    text = "\n\n".join([subject, *[f"{h}\n{b}" for h, b in kept], f"{cta_text}: {link}" if link else cta_text, f"You get this because you signed up for {tidy(idea.get('title', ctx['slug']))}. {{{{unsubscribe_link}}}}"])
    nxt = (dt.date.fromisoformat(issues[-1]) + dt.timedelta(days=cadence)) if issues else today + dt.timedelta(days=2)
    d = f"launch/newsletter/{today.isoformat()}"
    k.write(ctx, f"{d}/issue.html", page)
    k.write(ctx, f"{d}/issue.txt", text)
    k.write(ctx, f"{d}/meta.json", {"subject": subject, "preheader": pre, "send_after": f"{max(nxt, today).isoformat()}T09:00:00 Europe/London", "segment": "all subscribers", "links": links,
                                    "checks": {"lint": lint_ok, "links": ok_links if ok_links is not None else "not run: no site", "contrast": c_ok}, "note": "Replace {{unsubscribe_link}} with your email service's unsubscribe merge tag. Add sent and the date here after sending."})
    return {"summary": f"Issue drafted for {today.isoformat()}: '{subject}', {words} words. Checks: lint {lint_ok}, links {ok_links}, contrast {c_ok}. Charlie tests and sends it; nothing was sent." + (" Template draft, no model answered." if template else ""), "flag": "ok" if lint_ok and c_ok and ok_links is not False else "caution"}


if __name__ == "__main__":
    k.run(main)
