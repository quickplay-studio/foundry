"""Ad Creative: GitHub implementation of departments/marketing/creation/ad-creative/SKILL.md.

Writes launch/ad-brief.md for Charlie to approve: three creatives, two audiences, a daily cap, the total
budget from budget.json, a target cost per sign-up and the kill rule. Never holds a card, never creates an
ad account, never publishes. The brief and its field check are the only outputs; the runner marks it review.
"""
import csv
import io
import re

from foundry import jobkit as k

FIELDS = ["objective", "platform", "creative 1", "creative 2", "creative 3", "audience 1", "audience 2", "daily cap", "total budget", "target cost per sign-up", "kill rule", "campaign id"]
MIN_DAILY = {"Meta": 5, "TikTok": 15, "Google": 5}  # pounds a day (as of Oct 2026, check the limit)
GOOGLE_LIMITS = (30, 90)  # headline and description characters
ANGLES = ["problem", "outcome", "proof"]
PRICE = re.compile(r"£\s?\d[\d,]*(?:\.\d{1,2})?(?:\s?(?:/|per|a)\s?(?:month|mo|year|yr|week))?", re.I)
BAD = re.compile(r"(\b(best|greatest|fastest|cheapest|number one|perfect|guaranteed?|guarantee|risk[- ]free|earn|income|make money|lose weight|cure|treat|heal)\b|#1|[\u2013\u2014!]| - |\b(are you|if you(?:'re| are)) (in debt|overweight|depressed|anxious|sick|single|poor|unemployed|divorced|pregnant|struggling)\b)", re.I)
SENSITIVE = re.compile(r"\b(debt|health|religio|ethnic|sexual|politic|disab|medical|pregnan|union|loan|gambl)", re.I)
NEGATIVES = "free, jobs, course, pdf, template, reddit, youtube, salary"


def tidy(text):
    return re.sub(r"\s+", " ", re.sub(r"\s*[\u2013\u2014]\s*", ", ", re.sub(r"!+", ".", str(text)).replace(" - ", ", "))).strip()


def annual(price_text):
    m = re.search(r"\d[\d,]*(?:\.\d+)?", price_text)
    n = float(m.group(0).replace(",", "")) if m else 0
    return n * (12 if re.search(r"month|mo\b", price_text, re.I) else 52 if re.search(r"week", price_text, re.I) else 1)


def banned_terms(text):
    out = []
    for line in text.splitlines():
        if re.search(r"ban|prohibit|must not|do not|never|not allowed", line, re.I):
            out += [t.lower() for t in re.findall(r'["“‘]([^"”’]{3,40})["”’]', line)]
    return out


def jaccard(a, b):
    a, b = set(re.findall(r"\w+", a.lower())), set(re.findall(r"\w+", b.lower()))
    return len(a & b) / len(a | b) if a | b else 0


def ok(c, platform, price_token, truth, banned, hooks):
    hook, body = tidy(c.get("hook", "")), tidy(c.get("body", ""))
    h_lim, b_lim = (GOOGLE_LIMITS if platform == "Google" else (None, None))
    if not hook or not body or BAD.search(hook + " " + body) or (price_token and price_token not in body):
        return None
    if (h_lim and (len(hook) > h_lim or len(body) > b_lim)) or (not h_lim and (len(hook.split()) > 12 or len(body.split()) > 30)):
        return None
    if any(t in (hook + " " + body).lower() for t in banned) or any(n not in truth for n in re.findall(r"\d+(?:[.,]\d+)*", hook + " " + body)):
        return None
    return {"angle": c.get("angle"), "hook": hook, "body": body, "visual_note": tidy(c.get("visual_note", "")) or "Screen recording of the product", "rank": max([jaccard(hook, h["text"]) * (h.get("score") or 1) for h in hooks] + [0])}


def candidates(angles, platform, note):
    lim = "Google: hook is a headline of 30 characters or fewer, body a description of 90 or fewer." if platform == "Google" else "Hook 12 words or fewer; body 30 words or fewer."
    answer = k.ask('Return JSON only: {"candidates": [{"angle": "problem, outcome or proof", "hook": "...", "body": "...", "visual_note": "..."}]}. Three per angle for: ' + ", ".join(angles)
                   + f". Angles: problem, the outcome with the price, the proof. {lim} The body states the price and what the product does. Use only facts below. Plain, no hype, no superlatives, no guarantees, no income or health claims, no exclamation marks, no dashes.\n\n" + note)
    rows = answer.get("candidates") if isinstance(answer, dict) else None
    return [c for c in rows if isinstance(c, dict)] if isinstance(rows, list) else []


def fields_of(md):
    out, cur = {}, None
    for line in md.splitlines():
        m = re.match(r"\*\*([a-z0-9 -]+):\*\*\s*(.*)", line)
        if m:
            cur = m.group(1)
            out[cur] = [m.group(2)] if m.group(2) else []
        elif cur and line.strip():
            out[cur].append(line.strip())
    return out


def check(md):
    f = fields_of(md)
    if list(f) != FIELDS:
        return "fields are not exactly the listed fields in order"
    try:
        daily, total, target = (float(re.search(r"£(\d+(?:\.\d+)?)", f[n][0]).group(1)) for n in ("daily cap", "total budget", "target cost per sign-up"))
    except (AttributeError, ValueError):
        return "a money field does not parse"
    return "daily cap is above the total budget" if daily > total else "target is not above zero" if target <= 0 else ""


def pick(cands, angles, platform, price_token, truth, banned, hooks, note):
    best = {}
    for attempt in range(2):  # regenerate once for an angle with nothing left
        for c in cands:
            r = ok(c, platform, price_token, truth, banned, hooks) if c.get("angle") in angles else None
            if r and (r["angle"] not in best or r["rank"] > best[r["angle"]]["rank"]):
                best[r["angle"]] = r
        missing = [a for a in angles if a not in best]
        if not missing or attempt:
            break
        cands = candidates(missing, platform, note)
    return best


def main(ctx):
    idea, brain, kind = ctx["idea"], ctx["brain"], str(ctx["idea"].get("kind", "app")).lower()
    try:
        total = float(ctx["budget"].get("ad_budget") or 0)
    except (TypeError, ValueError):
        total = 0
    if total <= 0:
        return {"skipped": "no ad budget"}
    comp = sorted(p for d in ("launch", "clear") for p in (ctx["folder"] / d).glob("*ad-compliance*") if p.suffix == ".md") or sorted(p for d in ("launch", "clear") for p in (ctx["folder"] / d).glob("*ad-compliance*"))
    if not comp:
        return {"skipped": "no ad-compliance file: ad copy is not written before the rules"}
    rules = comp[0].read_text(encoding="utf-8")
    if re.match(r"\s*FLAG:\s*stop", rules, re.I):
        return {"skipped": "platform and ad compliance flag is stop"}
    landing = k.read(ctx, "launch/landing-page.md", "") or ""
    shop = kind in ("shop", "tiktok-shop", "dropshipping")
    cost = k.read(ctx, "commerce/landed-cost.json", {}) if shop else {}
    price_text = f"£{float(cost['selling_price']):g}" if shop and isinstance(cost, dict) and isinstance(cost.get("selling_price"), (int, float)) else (PRICE.search(landing) or PRICE.search(str(idea.get("money", "")) + brain) or [""])[0]
    if shop and not (isinstance(cost, dict) and cost.get("target_cpa")):
        return {"skipped": "no commerce/landed-cost.json target_cpa: run landed-cost-modelling first"}
    if not shop and not price_text:
        return {"skipped": "no price in the landing page copy or the brain, so no target cost can be set"}
    audience = k.read(ctx, "launch/insights/audience.json", {}) or {}
    m = re.search(r"£\s?\d[\d,]*(?:\.\d{1,2})?", price_text)
    price_token = re.sub(r"\s", "", m.group(0)) if m else ""
    text = f"{idea.get('who', '')} {idea.get('problem', '')}".lower()
    words_used = " ".join(str(q) for x in (audience.get("questions", []) if isinstance(audience, dict) else []) if isinstance(x, dict) for q in [x.get("theme", ""), *x.get("quotes", [])]).lower()
    platform = "Google" if not shop and re.search(r"\bhow (do|can) i\b|\bbest\b.{0,30}\bfor\b", words_used) else "TikTok" if re.search(r"student|teen|gen z|young|under 30|20s", text) else "Meta"
    daily = min(total, max(5.0, float(round(total / 10))))
    if MIN_DAILY[platform] > daily:
        platform = next(p for p in ("Meta", "Google", platform) if MIN_DAILY[p] <= daily or p == platform)
    hooks = [h for h in (k.read(ctx, "launch/hooks.json", {}) or {}).get("hooks", []) if isinstance(h, dict) and h.get("status") != "rejected"]
    themes = [x.get("theme", "") for x in (audience.get("questions", []) if isinstance(audience, dict) else []) if isinstance(x, dict) and not SENSITIVE.search(x.get("theme", ""))]
    truth = brain + " " + landing + " " + price_text + " " + str(daily) + " " + str(total)
    note = f"PRICE\n{price_text}\nBRAIN\n{brain[:2500]}\nLANDING PAGE\n{landing[:1500]}\nAUDIENCE WORDS\n" + "; ".join(themes[:8])
    old, results = k.read(ctx, "launch/ad-brief.md"), k.read(ctx, "launch/inputs/ad-results.csv")
    if old and results and not check(old):  # re-run: replace the worst creative, never raise the cap or total
        f, costs = fields_of(old), {}
        for r in csv.DictReader(io.StringIO(results)):
            try:
                n = int(re.search(r"\d", r["creative"]).group(0))
                costs[n] = float(r["spend"]) / float(r["signups"]) if float(r["signups"]) else float("inf")
            except (KeyError, ValueError, AttributeError):
                continue
        if len(costs) >= 2:
            worst, best = max(costs, key=costs.get), min(costs, key=costs.get)
            angle = (re.search(r"\[angle: (\w+)\]", " ".join(f.get(f"creative {best}", []))) or [None, "problem"])[1]
            fresh = pick(candidates([angle], platform, note), [angle], platform, price_token, truth, banned_terms(rules), hooks, note).get(angle)
            if fresh:
                block = [f"**creative {worst}:**", "hook: " + fresh["hook"], "body: " + fresh["body"], f"visual note: [angle: {angle}] " + fresh["visual_note"]]
                md, skipping = [], False
                for line in old.splitlines():
                    if line.startswith(f"**creative {worst}:**"):
                        md, skipping = md + block, True
                    elif line.startswith("**"):
                        md, skipping = md + [line], False
                    elif not skipping:
                        md.append(line)
                md = "\n".join(md)
                if not check(md):
                    k.write(ctx, "launch/ad-brief.md", md)
                    return {"summary": f"Creative {worst} replaced on the {angle} angle after results; cap and total unchanged.", "flag": "ok"}
        return {"skipped": "re-run could not replace a creative (needs results for two creatives and a candidate that passes)"}
    best = pick(candidates(ANGLES, platform, note), ANGLES, platform, price_token, truth, banned_terms(rules), hooks, note)
    if len(best) < 3:
        return {"skipped": "no creative left for the " + ", ".join(a for a in ANGLES if a not in best) + " angle after filtering and one regeneration"}
    if platform == "Google":
        kw = [t.lower() for t in themes[:2]] + [str(idea.get("problem", "")).lower()[:40]]
        aud = [f'Keyword theme: "{kw[0]}" (phrase match). Negative keywords: {NEGATIVES}. UK only.', f'Keyword theme: [{kw[1] if len(kw) > 2 else kw[-1]}] (exact match). Negative keywords: {NEGATIVES}. UK only.']
    else:
        who_line = tidy(idea.get("who", "")).rstrip(".")
        aud = ["Broad: UK, ages 25 to 54, all genders, no interest targeting.", f"Narrower: UK, ages 25 to 44, people matching this description: {who_line}. Use job title or interest options that fit; no sensitive categories."]
    if shop:
        target, assume = min(float(cost["target_cpa"]), float(cost.get("break_even_cpa") or cost["target_cpa"])), "target_cpa from commerce/landed-cost.json, capped at break_even_cpa; the goal is a sale, not a sign-up"
    else:
        year = annual(price_text)
        target, assume = round(year / 3 * 0.10, 2), f"one third of first-year revenue per paying user (£{year:.2f}), times an assumed 10 per cent of sign-ups who pay"
    target = max(target, 0.01)
    expected = int(total / target)
    tail = f" Expected {'sales' if shop else 'sign-ups'} at target: {expected}." + (" Under 20, so the test is too small to judge." if expected < 20 else "")
    kill = f"Stop when cost per sign-up is above £{target:.2f} after the first £50 spent." + (" The total budget ends the test first." if total < 50 else "")
    goal = "sales" if shop else "sign-ups"
    event = "purchase" if shop else "sign_up"
    md = ["# Ad brief: " + tidy(idea.get("title", ctx["slug"])), f"**objective:** {goal.capitalize()} at or below £{target:.2f} each, within £{total:g} in total, tracked as the {event} event.", f"**platform:** {platform}"]
    for i, a in enumerate(ANGLES, 1):
        c = best[a]
        md += [f"**creative {i}:**", "hook: " + c["hook"], "body: " + c["body"], f"visual note: [angle: {a}] " + c["visual_note"]]
    md += [f"**audience 1:** {aud[0]}", f"**audience 2:** {aud[1]}", f"**daily cap:** £{daily:g}", f"**total budget:** £{total:g}, copied from budget.json",
           f"**target cost per sign-up:** £{target:.2f}, {assume}.{tail}", f"**kill rule:** {kill}", "**campaign id:** pending, Charlie fills this in after he pays"]
    text = "\n".join(md)
    problem = check(text)
    if problem:
        return {"skipped": "field check failed: " + problem}
    k.write(ctx, "launch/ad-brief.md", text)
    return {"summary": f"Ad brief on {platform}: daily cap £{daily:g}, total £{total:g}, target £{target:.2f} per {goal[:-1]}. Waiting for Charlie to approve, pay and build the campaign.", "flag": "caution" if expected < 20 else "ok"}


if __name__ == "__main__":
    k.run(main)
