"""Script Writing: GitHub implementation of departments/marketing/creation/script-writing/SKILL.md.

Takes the best spoken hooks (one per theme, platforms rotating), outlines the beats, asks the free model for the
lines, then times them in code (2.5 words a second), applies the voice check and marks any claim the brain does
not support as [needs proof]. Sponsored scripts are deal-scripting, not this job.
"""
import re

from foundry import jobkit as k

WPS = 2.5
BEATS = ["hook (0 to 3 s)", "problem (3 to 10 s)", "what it does and the price (10 to 20 s)", "proof: a number from the brain or a screen recording of the product", "one call to action"]
HYPE = re.compile(r"\b(amazing|revolutionary|game[- ]changing|insane|secret|incredible|unbelievable|guaranteed?|life[- ]changing|ultimate)\b\s*", re.I)
UK = {"color": "colour", "optimize": "optimise", "organize": "organise", "center": "centre", "favorite": "favourite", "analyze": "analyse", "behavior": "behaviour", "realize": "realise"}
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")
BIO = ("tiktok", "instagram", "facebook")
PRICE = re.compile(r"£\s?\d[\d,]*(?:\.\d{1,2})?(?:\s?(?:/|per|a)\s?(?:month|mo|year|yr|week))?", re.I)


def tidy(text):
    return re.sub(r"\s+", " ", re.sub(r"\s*[\u2013\u2014]\s*", ", ", re.sub(r"!+", ".", str(text)).replace(" - ", ", "))).strip()


def voice(text):
    text = re.sub(r"\s+([.,?])", r"\1", EMOJI.sub("", HYPE.sub("", tidy(text))))
    for us, uk in UK.items():
        text = re.sub(rf"\b{us}", uk, text, flags=re.I)
    return text.strip()


def seconds(text):
    return len(text.split()) / WPS


def time_lines(lines, max_s):
    """Cut the longest middle line until the script fits, then assign start and end."""
    for _ in range(40):
        if sum(max(seconds(l["voiceover"]), 1.0) for l in lines) <= max_s or len(lines) < 3:
            break
        i = max(range(1, len(lines) - 1), key=lambda j: len(lines[j]["voiceover"].split()))
        w = lines[i]["voiceover"].split()
        if len(w) <= 4:
            break
        lines[i]["voiceover"] = " ".join(w[:max(4, int(len(w) * 0.8))]).rstrip(",;:.") + "."
    t = 0.0
    for l in lines:
        d = max(round(seconds(l["voiceover"]), 1), 1.0)
        l["start"], l["end"] = round(t, 1), round(t + d, 1)
        t += d
    return round(t, 1)


def unsupported(text, brain):
    return [n for n in re.findall(r"[£$]?\d+(?:[.,]\d+)*", text) if n.lstrip("£$") not in brain]


def template_lines(idea, brain, hook, price, beats):
    mvp = idea.get("mvp") if isinstance(idea.get("mvp"), list) and idea.get("mvp") else [""]
    base = [hook, str(idea.get("problem", "")).split(".")[0], f"{idea.get('title', '')}: {str(mvp[0]).rstrip('.')}. {price}".strip(), "Here it is working in the product.", ""]
    return [{"voiceover": b, "on_screen": " ".join(b.split()[:7]), "visual": "Screen recording of the product" if "product" in b else "Presenter or stock footage that matches the line"} for b in base[:len(beats)]]


def main(ctx):
    hooks_doc = k.read(ctx, "launch/hooks.json")
    if not isinstance(hooks_doc, dict) or not hooks_doc.get("hooks"):
        return {"skipped": "launch/hooks.json missing: run hook-writing first"}
    idea, brain = ctx["idea"], ctx["brain"]
    req = k.read(ctx, "launch/inputs/script-request.json", {}) or {}
    req = req if isinstance(req, dict) else {}
    try:
        length_s, count = float(req.get("length_s", 30)), int(req.get("count", 1 if float(req.get("length_s", 30)) >= 180 else 10))
    except (TypeError, ValueError):
        length_s, count = 30.0, 10
    long_form = length_s >= 180
    index = k.read(ctx, "launch/scripts/index.json", []) or []
    index = [r for r in index if isinstance(r, dict)]
    used = {r.get("hook_id") for r in index}
    nxt = max([int(r["post_id"][2:]) for r in index if re.match(r"p-\d+$", str(r.get("post_id", "")))] + [0]) + 1
    spoken = [h for h in hooks_doc["hooks"] if isinstance(h, dict) and h.get("kind") == "spoken" and h.get("status") != "rejected" and h.get("id") not in used
              and (not req.get("platform") or h.get("platform") == req["platform"]) and (not req.get("theme") or str(req["theme"]).lower() in str(h.get("theme", "")).lower())]
    best = {}
    for h in sorted(spoken, key=lambda h: -(h.get("score") or 0)):
        best.setdefault((h.get("theme"), h.get("platform")), h)
    queues = {}
    for h in sorted(best.values(), key=lambda h: -(h.get("score") or 0)):
        queues.setdefault(h.get("platform"), []).append(h)
    picked = []
    while queues and len(picked) < count:
        for p in list(queues):
            if queues[p] and len(picked) < count:
                picked.append(queues[p].pop(0))
            if not queues[p]:
                del queues[p]
    if not picked:
        return {"skipped": "no unused spoken hook to script"}
    audience = k.read(ctx, "launch/insights/audience.json", {}) or {}
    qs = [x.get("theme", "") for x in (audience.get("questions", []) if isinstance(audience, dict) else []) if isinstance(x, dict)][:6]
    trends = (k.read(ctx, "launch/insights/trends.md", "") or "")[:600]
    price = (PRICE.search(str(idea.get("money", "")) + brain) or [""])[0]
    beats = (["opening hook"] + [f"chapter on: {q}" for q in qs] + ["one call to action"]) if long_form and qs else BEATS
    made, proof_total, templated = [], 0, False
    for h in picked:
        pid, platform = f"p-{nxt:03d}", str(h.get("platform", "tiktok"))
        nxt += 1
        cta = "Sign up at the link in bio." if platform in BIO else "Watch the next video."
        answer = k.ask('Return JSON only: {"lines": [{"voiceover": "...", "on_screen": "7 words or fewer", "visual": "..."}]}. One line per beat, in order: ' + "; ".join(beats)
                       + f". Spoken English, about 2.5 words a second, {int(length_s)} seconds in total. Start from this hook: \"{h.get('text', '')}\". Say the price and what it does. Use only facts in the brain. Plain UK English, no hype, no dashes, no exclamation marks.\n\nBRAIN\n{brain[:2500]}\nPRICE\n{price}\nTRENDS\n{trends}")
        raw = [l for l in (answer.get("lines") if isinstance(answer, dict) and isinstance(answer.get("lines"), list) else []) if isinstance(l, dict) and str(l.get("voiceover", "")).strip()]
        template = len(raw) < len(beats)
        templated = templated or template
        lines = [{"voiceover": voice(l["voiceover"]), "on_screen": " ".join(voice(l.get("on_screen", "")).split()[:7]), "visual": tidy(l.get("visual", "")) or "Screen recording of the product"} for l in raw[:len(beats)]] if not template else template_lines(idea, brain, h.get("text", ""), price, beats)
        lines[0]["voiceover"] = voice(h.get("text", "")) or lines[0]["voiceover"]
        lines[-1].update(voiceover=cta, on_screen="Link in bio" if platform in BIO else "Next video")
        bad = [i for i, l in enumerate(lines) if unsupported(l["voiceover"], brain)]
        if bad and not template:  # rewrite once, then mark [needs proof]
            fix = k.ask('Return JSON only: {"lines": [{"voiceover": "..."}]}. Rewrite each line with no number or claim that is not in the brain, keeping its job in the script.\n\nBRAIN\n' + brain[:2500] + "\nLINES\n" + "\n".join(lines[i]["voiceover"] for i in bad))
            new = [voice(x.get("voiceover", "")) for x in (fix.get("lines") if isinstance(fix, dict) and isinstance(fix.get("lines"), list) else []) if isinstance(x, dict)]
            for i, text in zip(bad, new):
                lines[i]["voiceover"] = text or lines[i]["voiceover"]
            for i in bad:
                if unsupported(lines[i]["voiceover"], brain):
                    lines[i]["voiceover"] += " [needs proof]"
        proof = sum("[needs proof]" in l["voiceover"] for l in lines)
        proof_total += proof
        data = {"post_id": pid, "platform": platform, "hook_id": h.get("id"), "duration_s": time_lines(lines, length_s), "lines": lines}
        data.update({"draft": "template"} if template else {})
        k.write(ctx, f"launch/scripts/{pid}.json", data)
        md = [f"# Script {pid} ({platform}, {data['duration_s']} s)", f"Hook {h.get('id')}: {h.get('text', '')}", ""] + (["draft: template"] if template else [])
        md += ["| Time | Voiceover | On screen and visual |", "|---|---|---|"] + [f"| {l['start']} to {l['end']} | {l['voiceover'].replace('|', '/')} | {l['on_screen'].rstrip('.').replace('|', '/')}. {l['visual'].replace('|', '/')} |" for l in lines]
        k.write(ctx, f"launch/scripts/{pid}.md", "\n".join(md))
        index.append({"post_id": pid, "platform": platform, "hook_id": h.get("id"), "duration_s": data["duration_s"], "needs_proof": proof, **({"draft": "template"} if template else {})})
        made.append(pid)
    k.write(ctx, "launch/scripts/index.json", index)
    return {"summary": f"{len(made)} scripts written ({made[0]} to {made[-1]}), {proof_total} [needs proof] lines." + (" Some are template drafts: no model answered." if templated else ""), "flag": "caution" if proof_total else "ok"}


if __name__ == "__main__":
    k.run(main)
