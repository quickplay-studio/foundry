"""Kickoff Pack: GitHub implementation of departments/operations/onboarding/kickoff-pack/SKILL.md.

A lookup table maps the MVP bullets to free services and writes the welcome note and the access
checklist (secret names only). It also drafts launch/brand.json if project-scaffolding has not.
The free model may word one line; every number comes from idea.json and budget.json.
"""
import re

from foundry import jobkit as k

DASH = re.compile("[" + chr(0x2013) + chr(0x2014) + "]")
CHECK = "as of Oct 2026, check the limit"
GH = ("GH_TOKEN", "GitHub Actions and API (github.token)", "yes", "GitHub")
GEMINI = ("GEMINI_API_KEY", "model calls, first choice", "yes", "Google AI Studio")
GROQ = ("GROQ_API_KEY", "model calls, fallback", "no", "Groq")
# need: (regex over the MVP text, stack line, extra secret rows)
NEEDS = [
    ("hosting", None, "Cloudflare Pages or Netlify", []),
    ("jobs", None, "GitHub Actions", []),
    ("monitoring", None, "UptimeRobot (Charlie creates the monitor, an account step)", []),
    ("database", r"\b(database|store|save|history|account|profile|list|log|record)", "Supabase",
     [("SUPABASE_URL", "database URL", "yes", "Supabase"), ("SUPABASE_ANON_KEY", "database key, anonymous role", "yes", "Supabase")]),
    ("auth", r"\b(login|log in|sign in|sign-in|auth|password|account)", "Supabase auth", []),
    ("analytics", r"\b(analytic|metric|dashboard|funnel|usage)", "PostHog", [("POSTHOG_KEY", "product analytics", "no", "PostHog")]),
    ("model calls", r"\b(ai|summar|generat|classif|extract|recommend|chat|assistant|model|parse)", "Gemini 2.5 Flash then Groq", []),
    ("payments", r"\b(pay|price|subscription|checkout|charge|paid|buy)", "later: after first sign-ups", []),
    ("email", r"\b(email|e-mail|newsletter|digest|reminder|notification)", "needs Charlie: no default free sender in the stack", []),
]


def clean(text):
    return DASH.sub(", ", str(text)).replace("!", ".").strip()


def as_list(v):
    return [clean(x) for x in v if str(x).strip()] if isinstance(v, list) else ([clean(v)] if v else [])


def money(v):
    return clean(v) if isinstance(v, (str, int, float)) else clean(" ".join(f"{a} {b}" for a, b in v.items())) if isinstance(v, dict) else ""


def blocked_gates(board):
    jobs, gates = board.get("jobs") or [], board.get("gates") or {}
    return [s for s in ("validate", "clear") if any(isinstance(j, dict) and j.get("stage") == s for j in jobs) and gates.get(s) != "passed"]


def numbers_ok(text, facts):
    return all(n in facts for n in re.findall(r"\d+(?:[.,]\d+)*", text))


def main(ctx):
    idea, brain = ctx["idea"], ctx["brain"]
    if not brain.strip():
        return {"skipped": "brain.md is missing"}
    wait = blocked_gates(ctx["board"])
    if wait:
        return {"skipped": "gates not passed: " + ", ".join(wait)}
    title = clean(idea.get("title") or ctx["slug"])
    mvp = as_list(idea.get("mvp"))
    problem, who, price = clean(idea.get("problem", "")), clean(idea.get("who", "")), money(idea.get("money"))
    text = " ".join(mvp + [problem]).lower()
    stack, rows = [], [GH, GEMINI, GROQ]
    for need, pattern, service, extra in NEEDS:
        if pattern is None or re.search(pattern, text):
            stack.append((need, service))
            rows += [r for r in extra if r not in rows]
    if not any(n == "model calls" for n, _ in stack):
        rows[1] = GEMINI[:2] + ("no",) + GEMINI[3:]
    budget = ctx["budget"] or {}
    ad = budget.get("ad_budget", idea.get("budget_gbp", 0))
    facts = " ".join([price, problem, who, str(ad), title] + mvp)
    opening = problem
    answer = k.ask('Reword the problem as one plain sentence of at most 25 words saying what the product does. Use no numbers that are not in the text. '
                   'Return JSON only: {"opening": "<sentence>"}\n\nPRODUCT ' + title + "\nPROBLEM " + problem + "\nMVP " + "; ".join(mvp))
    line = clean(answer.get("opening", "")) if isinstance(answer, dict) and isinstance(answer.get("opening"), str) else ""
    if 10 <= len(line) <= 200 and numbers_ok(line, facts):
        opening = line
    note = [f"# {title}: kickoff", f"Price: {price or 'not set in idea.json'}.", f"What it does: {opening}", "",
            f"Who it is for: {who or 'see brain.md'}", f"Problem: {problem}", "", "## MVP"] + [f"- {b}" for b in mvp or ["see brain.md"]] + ["", "## Free stack (" + CHECK + ")"]
    note += [f"- {need}: {service}" for need, service in stack]
    note += ["", f"Ad budget: £{ad}. Charlie approves every ad line.", "",
             "## Build gate", "QA passes on real data and Charlie uses it once end to end. Charlie signs up to each service himself; nothing here creates an account."]
    k.write(ctx, "kickoff/note.md", "\n".join(note[:40]))
    table = ["| name | purpose | required | free tier | state |", "|---|---|---|---|---|"]
    table += [f"| {n} | {p} | {r} | {s} ({CHECK}) | missing |" for n, p, r, s in rows]
    k.write(ctx, "kickoff/access.md", "# Access checklist\n\nNames only, never values. Add each as a repository secret.\n\n" + "\n".join(table))
    brand = ""
    if k.read(ctx, "launch/brand.json") is None:  # project-scaffolding writes the final one
        tagline = (re.split(r"(?<=[.])\s", opening)[0] or title)[:80].rstrip(".")
        k.write(ctx, "launch/brand.json", {"name": title, "tagline": tagline, "colours": {"bg": "#ffffff", "text": "#111111", "accent": "#2f6fed"},
                                           "font": "system-ui", "logo": "", "voice": "plain, short, UK English, no dashes, no exclamation marks"})
        brand = " Drafted launch/brand.json."
    unfree = [n for n, s in stack if s.startswith("needs Charlie")]
    return {"summary": f"Kickoff note and access checklist ({len(rows)} secrets) written.{brand}" + (f" Needs Charlie: {', '.join(unfree)}." if unfree else ""),
            "flag": "caution" if unfree else "ok"}


if __name__ == "__main__":
    k.run(main)
