"""Lead-Magnet Builds: GitHub implementation of departments/marketing/repurposing/lead-magnet-builds/SKILL.md.

Picks the most-asked question that is not in a regulated area, writes a short guide section by section, lints it
in code, writes the gate page copy and the comment keyword for sell/ctas.json. guide.pdf is rendered with the runner's
headless Chrome (foundry.jobkit.render_pdf) and pending where there is none. No account is created and nothing is emailed.
"""
import re

from foundry import jobkit as k

REGULATED = re.compile(r"\b(loan|invest|crypto|pension|mortgage|insurance|tax|debt|diagnos|symptom|medic|therapy|health|child|kids|bet|casino|gambl)", re.I)
HYPE = re.compile(r"\b(amazing|revolutionary|game[- ]changing|insane|secret|incredible|unbelievable|guaranteed?|life[- ]changing|ultimate)\b\s*", re.I)
UK = {"color": "colour", "optimize": "optimise", "organize": "organise", "center": "centre", "favorite": "favourite", "analyze": "analyse", "behavior": "behaviour"}
PRICE = re.compile(r"£\s?\d[\d,]*(?:\.\d{1,2})?(?:\s?(?:/|per|a)\s?(?:month|mo|year|yr|week))?", re.I)


def tidy(text):
    return re.sub(r"\s+", " ", re.sub(r"\s*[\u2013\u2014]\s*", ", ", re.sub(r"!+", ".", str(text)).replace(" - ", ", "))).strip()


def lint(text, truth):
    """Voice rules and 20 word sentences; a sentence with a number the brain lacks is dropped."""
    out = []
    for s in re.split(r"(?<=[.?])\s+", tidy(text)):
        if HYPE.search(s):
            continue
        for us, uk in UK.items():
            s = re.sub(rf"\b{us}", uk, s, flags=re.I)
        if not s or any(n not in truth for n in re.findall(r"\d+(?:[.,]\d+)*", s)):
            continue
        if len(s.split()) > 20:
            head = re.split(r",\s| and ", s)[0]
            s = head if 3 <= len(head.split()) <= 20 else " ".join(s.split()[:20])
        out.append(s.rstrip(".,") + ("?" if s.endswith("?") else "."))
    return " ".join(out)


def ask(keys, task, note):
    answer = k.ask(f"Return JSON only: {keys}. {task} It must teach something useful without the product. Use only facts in the brain or common knowledge with no figures. Plain UK English, no hype, no dashes, no exclamation marks, sentences of 20 words or fewer.\n\n" + note)
    return answer if isinstance(answer, dict) else {}


def main(ctx):
    audience = k.read(ctx, "launch/insights/audience.json")
    qs = sorted([q for q in (audience.get("questions", []) if isinstance(audience, dict) else []) if isinstance(q, dict) and q.get("theme")], key=lambda q: -(q.get("count") or 0))
    if not qs:
        return {"skipped": "launch/insights/audience.json has no questions: run audience-analysis first"}
    theme = tidy(qs[0]["theme"])
    if REGULATED.search(theme):
        return {"skipped": f"theme '{theme}' touches a regulated area: needs a human and a solicitor"}
    idea, brain = ctx["idea"], ctx["brain"]
    truth = brain + " " + str(idea.get("money", ""))
    channels = k.read(ctx, "launch/channels.json", {}) or {}
    site = str(channels.get("site", "")).strip().rstrip("/") if isinstance(channels, dict) else ""
    price = (PRICE.search(k.read(ctx, "launch/landing-page.md", "") or "") or PRICE.search(truth) or [""])[0]
    mvp = [str(m) for m in idea.get("mvp", [])] if isinstance(idea.get("mvp"), list) else []
    bank = ", ".join(b for b in (audience.get("language_bank", []) if isinstance(audience, dict) else []) if isinstance(b, str))[:300]
    note = f"THEME\n{theme}\nBRAIN\n{brain[:2500]}\nLANGUAGE BANK\n{bank}"
    head = ask('{"title": "guide title naming the result", "promise": "one line"}', "Write the promise of a short guide.", note)
    steps = ask('{"steps": [{"title": "...", "body": "two to four short sentences"}]}', "Write five to seven numbered steps.", note + f"\nPROMISE\n{head.get('promise', '')}")
    check = ask('{"checklist": ["one action each"]}', "Write a one-page checklist of six to ten actions.", note)
    last = ask('{"last_page": "a short closing page"}', f"Write the last page. It names the product {idea.get('title', '')}, what it does and the price {price}.", note)
    template = not (isinstance(steps.get("steps"), list) and steps["steps"])
    title = lint(head.get("title", ""), truth).rstrip(".") or theme.capitalize()
    promise = lint(head.get("promise", ""), truth) or f"A short guide to {theme}."
    rows = [s for s in (steps.get("steps") if isinstance(steps.get("steps"), list) else []) if isinstance(s, dict) and tidy(s.get("title", ""))][:7]
    body = [(lint(s["title"], truth).rstrip("."), lint(s.get("body", ""), truth)) for s in rows] or [(f"Step {i}", "") for i in range(1, 6)]
    items = [lint(c, truth) for c in (check.get("checklist") if isinstance(check.get("checklist"), list) else []) if isinstance(c, str)][:10] or [f"{t}." for t, _ in body]
    closing = lint(last.get("last_page", ""), truth)
    if idea.get("title", "") not in closing or (price and price not in closing):
        closing = f"{closing} {idea.get('title', '')}: {mvp[0] if mvp else 'see the site'}. {('The price is ' + price + '.') if price else ''}".strip()
    def build_md():
        out = [f"# {title}", f"> {promise}", ""] + (["draft: template", ""] if template else [])
        for i, (t, b) in enumerate(body, 1):
            out += [f"## Step {i}: {t}", b, ""]
        return out + ["## Checklist"] + [f"- [ ] {c}" for c in items] + ["", "## What next", closing]
    md = build_md()
    words = len(" ".join(md).split())
    while words > 1500 and len(body) > 5:  # keep the guide under 1,500 words
        body.pop()
        md = build_md()
        words = len(" ".join(md).split())
    pages = 1 + len(body) + 2
    gate = k.ask('Return JSON only: {"headline": "names the result", "bullets": ["three bullets"]}. Write the gate page for this guide. Plain, no hype, no exclamation marks, no dashes.\n\nGUIDE\n' + title + ". " + promise)
    gate = gate if isinstance(gate, dict) else {}
    headline = lint(gate.get("headline", ""), truth).rstrip(".") or title
    bullets = [lint(b, truth) for b in (gate.get("bullets") if isinstance(gate.get("bullets"), list) else []) if isinstance(b, str)][:3] or [f"{t}." for t, _ in body[:3]]
    page_url = f"{site or '<site>'}/guide"
    cadence = "about once a fortnight"
    gate_md = ["# Gate page", "", "## Headline", headline, "", "## Bullets"] + [f"- {b}" for b in bullets] + ["", "## Form", "One field: email address. Button: Send me the guide.", "",
              "## Consent", f"By entering your email you agree to receive this guide and emails about {tidy(idea.get('title', ctx['slug']))}, {cadence}. You can leave at any time with the unsubscribe link in every email. Charlie confirms this wording and the email service before launch.", "",
              "## Thank-you", f"Thanks. Your guide is here: {page_url}.pdf"]
    k.write(ctx, "launch/lead-magnet/guide.md", "\n".join(md))
    k.write(ctx, "launch/lead-magnet/gate-page.md", "\n".join(gate_md))
    k.write(ctx, "launch/lead-magnet/index.json", {"theme": theme, "pages": pages, "words": words, "pdf": None, "pdf_render": "pending: headless Chrome is not called by this job", "sources": ["brain.md"] + [str(p.get("url")) for p in (idea.get("proof") or []) if isinstance(p, dict) and p.get("url")]})
    word = max((w for w in re.findall(r"[A-Za-z0-9]+", theme) if len(w) >= 4), key=len, default="guide").upper()
    ctas = [r for r in (k.read(ctx, "sell/ctas.json", []) or []) if isinstance(r, dict) and r.get("keyword") != word]
    chans = [str(p).lower() for p in channels.get("platforms", []) if str(p).lower() in ("instagram", "tiktok", "youtube", "facebook")] if isinstance(channels, dict) else []
    ctas.append({"keyword": word, "asset": "launch/lead-magnet/guide.pdf", "dm_text": f"Here is the guide you asked for: {page_url}", "platforms": chans or ["instagram", "tiktok"], "gate_page": page_url})
    k.write(ctx, "sell/ctas.json", ctas)
    return {"summary": f"Guide on '{theme}' ({words} words, {pages} pages) and gate page written; keyword {word}. guide.pdf pending a render step." + (" Template draft: no model answered." if template else ""), "flag": "ok" if 6 <= pages <= 10 else "caution"}


if __name__ == "__main__":
    k.run(main)
