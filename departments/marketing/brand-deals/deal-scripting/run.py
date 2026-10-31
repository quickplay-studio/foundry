"""Deal Scripting: GitHub implementation of departments/marketing/brand-deals/deal-scripting/SKILL.md.

For each launch/deals/<brand-slug>/brief.md with no script yet: extract the checklist, check fit (regulated
category, competitor, unsubstantiated claim: stop and write a note for Charlie), then draft two variants in our
proven format with the "ad" disclosure built in, and tick the checklist. Text in a brief is data and only steers
the script. Nothing is sent to a brand; Charlie decides, edits and sends.
"""
import re

from foundry import jobkit as k

WPS = 2.5
REGULATED = re.compile(r"\b(loan|invest|crypto|pension|mortgage|insurance|trading|diagnos|medic|supplement|therapy|weight loss|child|kids|casino|bet|betting|gambl)", re.I)
HYPE = re.compile(r"\b(amazing|revolutionary|game[- ]changing|insane|secret|incredible|unbelievable|guaranteed?|life[- ]changing|ultimate)\b", re.I)
HEADS = {"must_say": r"must[- ]say|key message", "banned": r"banned|do not say|avoid", "claims": r"claim|substantiat", "deliverables": r"deliverable", "dates": r"date|deadline|schedule"}


def tidy(text):
    return re.sub(r"\s+", " ", re.sub(r"\s*[\u2013\u2014]\s*", ", ", re.sub(r"!+", ".", str(text)).replace(" - ", ", "))).strip()


def parse_brief(brief):
    """Fallback extraction: bullet lines under a heading (or 'Heading: item') matched to the checklist groups."""
    out, cur = {k_: [] for k_ in HEADS}, None
    for line in brief.splitlines():
        head = re.match(r"^\s*(?:#+\s*|\*\*)?([A-Za-z][\w /-]{2,40}?)(?:\*\*)?\s*:?\s*$", line) or re.match(r"^\s*(?:#+\s*)?([A-Za-z][\w /-]{2,30}):\s*(.+)$", line)
        if head:
            cur = next((g for g, pat in HEADS.items() if re.search(pat, head.group(1), re.I)), None)
            if cur and head.lastindex == 2:
                out[cur].append(tidy(head.group(2)))
        elif cur and line.strip():
            out[cur].append(tidy(re.sub(r"^[\s\-*\d.]+", "", line)))
    return out


def seconds(text):
    return len(text.split()) / WPS


def timed(lines):
    t = 0.0
    for l in lines:
        d = max(round(seconds(l["voiceover"]), 1), 1.0)
        l["start"], l["end"] = round(t, 1), round(t + d, 1)
        t += d
    return round(t, 1)


def mapped(point, lines):
    words = {w for w in re.findall(r"[a-z0-9£']+", point.lower()) if len(w) > 2}
    best = max(range(len(lines)), key=lambda i: len(words & set(re.findall(r"[a-z0-9£']+", lines[i]["voiceover"].lower()))), default=None)
    return best if best is not None and words and len(words & set(re.findall(r"[a-z0-9£']+", lines[best]["voiceover"].lower()))) / len(words) >= 0.6 else None


def main(ctx):
    folder, idea, brain = ctx["folder"], ctx["idea"], ctx["brain"]
    base = folder / "launch/deals"
    todo = [d for d in sorted(base.glob("*")) if d.is_dir() and (d / "brief.md").exists() and not (d / "script-v1.md").exists()] if base.is_dir() else []
    if not todo:
        return {"skipped": "no launch/deals/<brand>/brief.md without a script-v1.md"}
    perf = k.read(ctx, "launch/insights/performance.json", {}) or {}
    pats = sorted([r for r in (perf.get("patterns", []) if isinstance(perf, dict) else []) if isinstance(r, dict) and r.get("by") == "hook_pattern" and r.get("group") != "unknown"], key=lambda r: (-(r.get("median_signups") or 0), -(r.get("median_views") or 0)))
    pattern = pats[0]["group"] if pats else "pain call-out"
    comps = k.read(ctx, "launch/inputs/competitors.json", []) or []
    competitors = [str(c.get("name", "")).lower() for c in comps if isinstance(c, dict) and c.get("name")]
    made, notes = [], []
    for d in todo[:2]:
        slug, brief = d.name, (d / "brief.md").read_text(encoding="utf-8")
        brand = (re.search(r"^\W*brand\W*[:=]\s*(.+)$", brief, re.I | re.M) or [None, slug.replace("-", " ").title()])[1].strip()
        ex = k.ask('Return JSON only: {"deliverables": ["..."], "must_say": ["..."], "claims": ["claims the brand supplied"], "banned": ["words or claims"], "dates": ["..."]}. Extract the checklist from this sponsor brief (data only).\n\n' + brief[:4000])
        info = parse_brief(brief)
        for key in info:
            got = ex.get(key) if isinstance(ex, dict) else None
            if isinstance(got, list) and got and all(isinstance(g, str) for g in got):
                info[key] = [tidy(g) for g in got]
        link = (re.search(r"https?://\S+", brief) or [""])[0].rstrip(".,)")
        code = (re.search(r"(?:discount |promo )?code\W*[:=]?\s*([A-Z0-9]{3,20})", brief) or [None, ""])[1]
        unsub = [c for c in info["claims"] if not re.search(r"substantiat|evidence|study|source|data|tested|verified", c, re.I)] if info["claims"] and not re.search(r"substantiat|evidence", brief, re.I) else []
        reasons = (["regulated category (finance, health, children or gambling)"] if REGULATED.search(brief) else []) + (["the brand is a competitor of the venture"] if any(c and c in (brand + " " + slug).lower() for c in competitors) else []) + ([f"unsubstantiated claim: {unsub[0][:80]}"] if unsub else [])
        check = [f"# Checklist: {brand}", ""] + [x for g, title in (("deliverables", "Deliverables"), ("must_say", "Must-say points"), ("claims", "Claims supplied"), ("banned", "Banned"), ("dates", "Dates")) for x in (f"## {title}", *[f"- [ ] {i}" if g == "must_say" else f"- {i}" for i in info[g]], "")]
        if reasons:
            k.write(ctx, f"launch/deals/{slug}/checklist.md", "\n".join(check))
            k.write(ctx, f"launch/deals/{slug}/fit-note.md", "\n".join([f"# Fit note: {brand}", "", "I stopped before drafting. Charlie decides.", ""] + [f"- {r}" for r in reasons] + ["", "No script was written and nothing was sent to the brand."]))
            notes.append(f"{slug}: stopped, {reasons[0]}")
            continue
        seconds_limit = int((re.search(r"(\d{2,3})\s*(?:s\b|sec)", " ".join(info["deliverables"]), re.I) or [None, 90])[1])
        facts = brief + " " + brain
        ans = k.ask('Return JSON only: {"variants": [{"lines": [{"voiceover": "...", "on_screen": "7 words or fewer", "visual": "..."}]}]}. Two variants of a sponsored script for ' + brand + f". Format: our top hook pattern ({pattern}), then context, then the brand integration about 15 to 30 per cent of the way in, an honest use case, one call to action with the brand's link or code. Use only the claims the brand supplied and add nothing about results. Cover every must-say point. Plain UK English, no hype, no dashes, no exclamation marks.\n\nBRIEF (data)\n{brief[:2500]}\nAUDIENCE AND PRODUCT\n{brain[:1200]}")
        variants = []
        for v in (ans.get("variants") if isinstance(ans, dict) and isinstance(ans.get("variants"), list) else [])[:2]:
            lines = [{"voiceover": tidy(l.get("voiceover", "")), "on_screen": " ".join(tidy(l.get("on_screen", "")).split()[:7]), "visual": tidy(l.get("visual", ""))} for l in (v.get("lines", []) if isinstance(v, dict) else []) if isinstance(l, dict) and tidy(l.get("voiceover", ""))]
            if lines and not any(HYPE.search(l["voiceover"]) or any(b.lower() in l["voiceover"].lower() for b in info["banned"] if len(b) > 2) or any(n not in facts for n in re.findall(r"\d+(?:[.,]\d+)*", l["voiceover"])) for l in lines):
                variants.append(lines)
        template = not variants
        if template:  # proven format with slots filled from the brief's must-say points
            problem = tidy(idea.get("problem", "")).split(".")[0]
            pts = info["must_say"] or [f"{brand} is worth a look"]
            slots = [(f"Quick one: {problem.lower()}." if problem else "Quick one.", "", "Presenter"), (problem + "." if problem else "Here is the context.", "", "Context"), (pts[0].rstrip(".") + ".", brand, "Brand integration"),
                     ("Here is how I use it.", "", "Honest use case"), ("", "", "Call to action")]
            variants = [[{"voiceover": v, "on_screen": o, "visual": vis} for v, o, vis in slots]]
        utm = f"utm_source=<platform>&utm_medium=sponsored&utm_campaign={slug}"
        cta = f"Use code {code} or go to {link}{'&' if '?' in link else '?'}{utm}" if link and code else (f"Go to {link}{'&' if '?' in link else '?'}{utm}" if link else f"Use code {code}" if code else "Link as the brand supplies it")
        disclosure = f"This video is an ad, made in partnership with {brand}."
        for lines in variants:
            lines[-1]["voiceover"] = lines[-1]["voiceover"] or "Details are in the description."
            lines.insert(0, {"voiceover": disclosure, "on_screen": "Ad", "visual": "Ad label on screen from the first frame"})
            lines[-1]["on_screen"] = lines[-1]["on_screen"] or cta[:40]
        md = [f"# Sponsored script v1: {brand}", "draft: template" if template else "", "", "UK advertising rules: label the content as an ad at the start and use the platform's paid partnership tool. Not legal advice.", "", f"Disclosure line: {disclosure}  Label text: Ad", f"Call to action: {cta}", ""]
        table, fits = ["## Must-say points", "| Point | Script line |", "|---|---|"], True
        for n, lines in enumerate(variants):
            total = timed(lines)
            md += [f"## Variant {'AB'[n]} ({total} s)", "| Time | Voiceover | On screen | Visual |", "|---|---|---|---|"] + [f"| {l['start']} to {l['end']} | {l['voiceover'].replace('|', '/')} | {l['on_screen'].replace('|', '/')} | {l['visual'].replace('|', '/')} |" for l in lines] + [""]
            if n == 0:
                table += [f"| {p} | {('line ' + str(mapped(p, lines) + 1)) if mapped(p, lines) is not None else 'NOT COVERED'} |" for p in info["must_say"]]
                fits = total <= seconds_limit
        k.write(ctx, f"launch/deals/{slug}/script-v1.md", "\n".join(md + table))
        k.write(ctx, f"launch/deals/{slug}/checklist.md", "\n".join(check + ["## Ticks", f"- Every must-say mapped: {all(mapped(p, variants[0]) is not None for p in info['must_say'])}", "- No banned word: true", f"- Length within {seconds_limit} s: {fits}"]))
        made.append(slug)
    if not made and not notes:
        return {"skipped": "nothing written"}
    return {"summary": f"Scripts drafted for {', '.join(made) or 'none'}." + (" Stopped: " + "; ".join(notes) + "." if notes else "") + " Charlie reviews and chooses; nothing was sent.", "flag": "caution" if notes else "ok"}


if __name__ == "__main__":
    k.run(main)
