"""Landing Page Copy: GitHub implementation of departments/marketing/creation/landing-page-copy/SKILL.md.

One model call per section, then lint in code (sentence length, dashes, hype) and a claims table:
any sentence with no source line in the brain or audience.json is removed. Measured on sign-ups only.
"""
import re

from foundry import jobkit as k

PRICE = re.compile(r"£\s?\d[\d,]*(?:\.\d{1,2})?(?:\s?(?:/|per|a)\s?(?:month|mo|year|yr|week))?", re.I)
HYPE = re.compile(r"\b(amazing|revolutionary|game[- ]changing|insane|secret|incredible|unbelievable|guaranteed?|life[- ]changing|ultimate|best|world[- ]class|effortless)\b", re.I)
STOP = set("a an the and or but of to in on for with is are was were be it its this that you your we our at as by from not no so if do does can will it's".split())
UK = {"color": "colour", "optimize": "optimise", "organize": "organise", "program ": "programme "}


def tidy(text):
    return re.sub(r"\s+", " ", re.sub(r"\s*[\u2013\u2014]\s*", ", ", re.sub(r"!+", ".", str(text)).replace(" - ", ", "))).strip()


def words(text):
    return {w.rstrip("s") for w in re.findall(r"[a-z0-9£']+", text.lower()) if w not in STOP and len(w) > 2}


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.?])\s+", tidy(text)) if s.strip()]


def fit(text):
    """Lint one block: drop hype sentences, UK spelling, sentences of 20 words or fewer."""
    out = []
    for s in sentences(text):
        if HYPE.search(s):
            continue
        for us, uk in UK.items():
            s = s.replace(us, uk)
        if len(s.split()) > 20:
            head = re.split(r",\s| and ", s)[0]
            s = head if 3 <= len(head.split()) <= 20 else " ".join(s.split()[:20])
        out.append(s.rstrip(".,?") + ("?" if s.endswith("?") else "."))
    return " ".join(out)


def source_lines(brain, audience, price):
    lines = [("brain.md", re.sub(r"^[-*#\s]+", "", l)) for l in brain.splitlines() if l.strip() and not l.startswith("#")]
    for q in (audience.get("questions", []) if isinstance(audience, dict) else []):
        if isinstance(q, dict):
            lines.append(("audience.json", f"{q.get('count', 0)} comments asked about {q.get('theme', '')}"))
    return lines + [("price", f"The price is {price}")]


def sourced(sentence, sources):
    """The best source line for a sentence, or None if it has no support (numbers must appear in the sources)."""
    sw, text = words(sentence), " ".join(s for _, s in sources)
    if not sw or any(n not in text for n in re.findall(r"\d+(?:[.,]\d+)*", sentence)):
        return None
    best = max(sources, key=lambda s: len(sw & words(s[1])) / len(sw), default=None)
    return f"{best[0]}: {best[1][:90]}" if best and len(sw & words(best[1])) / len(sw) >= 0.5 else None


def find_price(ctx, brain):
    pr = k.read(ctx, "validate/pricing-research.json")
    band = pr.get("band") if isinstance(pr, dict) else None
    if isinstance(band, dict) and isinstance(band.get("base"), (int, float)) and band["base"] > 0:
        return f"£{band['base']:g} a month"
    m = PRICE.search(str(ctx["idea"].get("money", ""))) or PRICE.search(brain)
    return tidy(m.group(0)) if m else ""


def section(brain, name):
    m = re.search(rf"^## {name}\n(.*?)(?=\n## |\Z)", brain, re.S | re.M)
    return m.group(1).strip() if m else ""


def ask(keys_hint, task, note):
    answer = k.ask(f'Return JSON only: {keys_hint}. {task} Use only facts in the brain. Plain UK English, no hype, no exclamation marks, no dashes, sentences of 20 words or fewer.\n\n' + note)
    return answer if isinstance(answer, dict) else {}


def main(ctx):
    idea, brain = ctx["idea"], ctx["brain"]
    price = find_price(ctx, brain)
    if not price:
        return {"skipped": "no price in pricing-research or the brain money line"}
    audience = k.read(ctx, "launch/insights/audience.json", {})
    bank = [b for b in audience.get("language_bank", []) if isinstance(b, str)][:15] if isinstance(audience, dict) else []
    sources = source_lines(brain, audience, price)
    mvp = [re.sub(r"^[-*\s]+", "", l) for l in section(brain, "MVP").splitlines() if l.strip()]
    top_q = next((q.get("theme", "") for q in audience.get("questions", []) if isinstance(q, dict)), "") if isinstance(audience, dict) else ""
    note = f"PRICE\n{price}\nBRAIN\n{brain[:3500]}\nLANGUAGE BANK\n{', '.join(bank)}\nBIGGEST QUESTION\n{top_q}"
    hero = ask('{"headline": "10 words or fewer", "does": "one sentence on what the product does", "button": "2 to 4 word verb phrase for sign up", "risk": "one true risk line or empty"}', "Write the hero.", note)
    proof = ask('{"proof": ["one line each"]}', "Write proof lines: the demand evidence with its source, and what the MVP does today. No testimonials, user counts, logos or press.", note)
    offer = ask('{"gets": ["three to five lines from the MVP"], "billing": "price and billing terms", "not_included": "what is not included"}', "Write the offer.", note)
    faq = ask('{"faq": [{"question": "...", "answer": "..."}]}', "Write two to four FAQ items from the audience questions. Skip a question you have no fact for.", note)
    cta = ask('{"closing": "one closing line"}', "Write one closing line for a sign-up button.", note)
    template = not (hero.get("headline") and hero.get("does"))
    claims, dropped = [], []

    def keep(text):
        out = []
        for s in sentences(fit(text)):
            src = sourced(s, sources)
            if src:
                out.append(s)
                claims.append({"claim": s, "source": src})
            else:
                dropped.append(s[:50])
        return " ".join(out)

    headline = fit(hero.get("headline", "")).rstrip(".") if hero.get("headline") else ""
    headline = headline if 0 < len(headline.split()) <= 10 else " ".join(tidy(idea.get("title", "")).split()[:10])
    does = keep(hero.get("does", "")) or keep((mvp or [str(idea.get("problem", ""))])[0])
    button = tidy(hero.get("button", "")) if 1 < len(str(hero.get("button", "")).split()) <= 4 and not HYPE.search(str(hero.get("button"))) else "Sign up"
    risk = keep(hero.get("risk", "")) if isinstance(hero.get("risk"), str) else ""
    proof_lines = [keep(p) for p in (proof.get("proof") if isinstance(proof.get("proof"), list) else []) if isinstance(p, str)]
    for q in (audience.get("questions", [])[:2] if isinstance(audience, dict) else []):
        if isinstance(q, dict) and q.get("count"):
            proof_lines.append(f"{q['count']} public comments we reviewed asked about {tidy(q.get('theme', ''))}.")
            claims.append({"claim": proof_lines[-1], "source": "audience.json: questions"})
    srcs = [p for p in (idea.get("proof") or []) if isinstance(p, dict) and p.get("source")]
    proof_lines += [f"Demand seen on {tidy(p['source'])}." for p in srcs[:2]]
    claims += [{"claim": f"Demand seen on {tidy(p['source'])}.", "source": "brain.md: Proof"} for p in srcs[:2]]
    proof_lines += [f"Today it does this: {m}." for m in mvp[:3]]
    claims += [{"claim": f"Today it does this: {m}.", "source": f"brain.md: {m}"} for m in mvp[:3]]
    gets = [keep(g) for g in (offer.get("gets") if isinstance(offer.get("gets"), list) else []) if isinstance(g, str)] or [m.rstrip(".") + "." for m in mvp[:5]]
    billing = keep(offer.get("billing", ""))
    not_inc = keep(offer.get("not_included", ""))
    qa = [(f"How much does it cost?", f"The price is {price}.")]
    facts = [t for _, line in sources for t in sentences(line)]
    cancel = next((t for t in facts if re.search(r"cancel|refund", t, re.I)), "")
    data = next((t for t in facts if re.search(r"\bdata\b|delete|privacy", t, re.I)), "")
    missing = [n for n, v in (("cancellation", cancel), ("data", data)) if not v]
    qa += [("Can I cancel?", fit(cancel))] if cancel else []
    qa += [("What happens to my data?", fit(data))] if data else []
    for f in (faq.get("faq") if isinstance(faq.get("faq"), list) else []):
        a = keep(f.get("answer", "")) if isinstance(f, dict) else ""
        if a and tidy(f.get("question", "")):
            qa.append((tidy(f["question"]).rstrip("?") + "?", a))
    claims += [{"claim": a, "source": "brain.md: " + (cancel if "cancel" in q.lower() else data if "data" in q.lower() else "Money")[:90]} for q, a in qa[:3]]
    closing = keep(cta.get("closing", ""))
    closing = closing or "Sign up when you are ready."
    lines = [f"# Landing page copy: {tidy(idea.get('title', ctx['slug']))}", "Measured on: sign-ups (completed sign-up form per 100 visitors). Nothing else."]
    lines += ["draft: template"] if template else []
    lines += ["", "## Hero", f"### {headline}", does, f"{price}.", f"[{button}]"] + ([risk] if risk else [])
    lines += ["", "## Proof"] + [f"- {p}" for p in proof_lines if p]
    lines += ["", "## Offer"] + [f"- {g}" for g in gets if g] + [f"Price: {billing if price in billing else (price + '. ' + billing).strip()}"] + ([f"Not included: {not_inc}"] if not_inc else [])
    lines += ["", "## FAQ"] + [x for q, a in qa[:7] for x in (f"### {q}", a, "")][:-1]
    lines += ["", "## CTA", closing, f"[{button}]"]
    k.write(ctx, "launch/landing-page.md", "\n".join(lines))
    k.write(ctx, "launch/landing-page.claims.json", claims)
    note_out = f" Missing brain facts: {', '.join(missing)} (FAQ items left out)." if missing else ""
    return {"summary": f"Landing page copy written with {len(claims)} sourced claims, {len(dropped)} sentences removed for no source.{note_out}" + (" Template draft, no model answered." if template else ""), "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
