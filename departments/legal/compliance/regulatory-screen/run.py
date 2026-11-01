"""Regulatory Screen: GitHub implementation of departments/legal/compliance/regulatory-screen/SKILL.md.

Flags ideas that touch regulated ground before any work starts. The free model drafts the
area table; a keyword list can only raise the flag; the flag always waits for Charlie.
Not legal advice.
"""
import datetime as dt
import json

from foundry import jobkit as k

AREAS = [
    ("Financial services", "Does it advise on, arrange, lend, broker, hold or move money, or promote investments or crypto?",
     "FCA PERG perimeter guidance; FSMA 2000 financial promotions; Payment Services Regulations 2017; Money Laundering Regulations 2017",
     ("loan", "lend", "invest", "crypto", "trading", "broker", "pension", "mortgage", "insurance", "payment", "wallet", "bank")),
    ("Health", "Does it diagnose, triage, advise on treatment or dosing, or process health data?",
     "MHRA software as a medical device guidance; NHS DTAC; CQC scope; ASA health claims rules",
     ("diagnos", "symptom", "treatment", "dosing", "medic", "therapy", "mental health", "supplement", "prescription", "clinic")),
    ("Children", "Aimed at, or likely to be used by, under-18s?",
     "ICO Children's code; Online Safety Act 2023 child safety duties; Apple Kids and Google Play Families policies",
     ("kids", "child", "children", "teen", "school", "parent", "toddler", "pupil")),
    ("Gambling and prizes", "Betting, gaming, lotteries, loot boxes, paid prize draws?",
     "Gambling Act 2005; Gambling Commission licensing",
     ("bet", "casino", "lottery", "prize draw", "raffle", "loot box", "wager", "odds")),
    ("User-generated content or messaging", "Can users post, message or share with each other?",
     "Online Safety Act 2023; Ofcom duties for user-to-user services",
     ("community", "forum", "chat", "message", "comment", "share with", "marketplace", "social")),
    ("Special category or large-scale personal data", "Special category data, profiling or automated decisions?",
     "UK GDPR Articles 9 and 22; ICO guidance",
     ("biometric", "profil", "automated decision", "credit score", "location tracking", "religion", "ethnic")),
    ("Legal, tax or accounting advice", "Reserved legal activity, or tax or accounting advice?",
     "Legal Services Act 2007; HMRC anti-money-laundering supervision",
     ("legal advice", "tax return", "accountant", "conveyanc", "will writing", "probate")),
    ("Other regulated sectors", "Energy, telecoms, lettings, recruitment or age-restricted goods?",
     "Ofgem; Ofcom; Estate Agents Act 1979 and Tenant Fees Act 2019; Employment Agencies Regulations 2003; CAP Code age-restricted rules",
     ("energy supplier", "telecom", "letting", "tenant", "recruit", "alcohol", "vape", "tobacco", "knife")),
    ("Data sourcing", "Does it depend on data or scraping a site's terms forbid? (hand to licence-audit)",
     "Site terms; Computer Misuse Act 1990; database right",
     ("scrape", "scraping", "crawl")),
]
ORDER = {"clear": 0, "caution": 1, "stop": 2}
STOP_WORDS = ("casino", "bet", "lottery", "diagnos", "prescription", "loan", "invest", "crypto", "kids", "children")


def keyword_flags(text):
    text = text.lower()
    out = {}
    for area, _, _, words in AREAS:
        hits = [w for w in words if w in text]
        if not hits:
            out[area] = ("clear", "no trigger word")
        elif any(w in STOP_WORDS for w in hits):
            out[area] = ("stop", "trigger words: " + ", ".join(hits[:4]))
        else:
            out[area] = ("caution", "trigger words: " + ", ".join(hits[:4]))
    return out


def worse(a, b):
    return a if ORDER.get(a, 1) >= ORDER.get(b, 1) else b


def main(ctx):
    idea, brain = ctx["idea"], ctx["brain"]
    facts_text = json.dumps({key: idea.get(key) for key in ("title", "kind", "problem", "who", "mvp", "money", "channels", "note")}, ensure_ascii=False)
    baseline = keyword_flags(facts_text + " " + brain)
    prompt = (
        "You are the regulatory screen of a UK solo founder's AI workforce. Not legal advice. Read the venture and, for each area, "
        "answer the question, name the source and give an area flag of clear, caution or stop with a one-line finding. "
        "Also write five plain facts: what it does, who uses it, what it charges, what personal data it holds, whether users can post or message. "
        "Return JSON only: {\"facts\": [\"...\"], \"areas\": [{\"area\": \"<name exactly as given>\", \"source\": \"...\", \"finding\": \"...\", \"flag\": \"clear|caution|stop\"}], "
        "\"design_limits\": [\"...\"], \"reason\": \"<two sentences>\"}\n\nVENTURE\n" + facts_text + "\n\nBRAIN\n" + brain[:4000]
        + "\n\nAREAS\n" + "\n".join(f"- {a}: {q} Sources: {s}" for a, q, s, _ in AREAS)
    )
    answer = k.ask(prompt)
    incomplete = not answer or not isinstance(answer.get("areas"), list)
    model_flags = {}
    if not incomplete:
        for row in answer["areas"]:
            given = str(row.get("area", "")).strip().lower() if isinstance(row, dict) else ""
            # models reword the area names ("Financial Services", "financial-services regulation"): match loosely
            area = next((a for a in baseline if a.lower() == given), None) or next((a for a in baseline if given and (a.lower() in given or given in a.lower())), None)
            if area and area not in model_flags:
                model_flags[area] = (str(row.get("flag", "caution")).lower().strip(), str(row.get("finding", ""))[:200], str(row.get("source", ""))[:200])
    if not incomplete and not model_flags:
        incomplete = True  # the model answered but none of its areas could be matched: do not call that clear
    areas, overall = [], "clear"
    for area, question, source, _ in AREAS:
        kw_flag, kw_reason = baseline[area]
        m_flag, finding, m_source = model_flags.get(area, ("caution" if incomplete else "clear", "model gave no finding", source))
        flag = worse(kw_flag, m_flag) if m_flag in ORDER else kw_flag
        if flag == "clear" and kw_flag != "clear":
            flag = kw_flag
        areas.append({"area": area, "question": question, "source": m_source or source, "finding": finding or kw_reason, "flag": flag})
        overall = worse(overall, flag)
    if incomplete:
        overall = worse(overall, "caution")
        reason = "Screen incomplete: no free model answered, so the keyword screen alone set the flag. Re-run before relying on it."
    else:
        reason = str(answer.get("reason", ""))[:400] or "See the table."
    # read one official page for each caution or stop area, if the router or Firecrawl can
    sources_read = []
    for a in areas:
        if a["flag"] != "clear":
            rows = k.search(f"{a['area']} UK regulator guidance {idea.get('kind', '')} {idea.get('title', '')}", 2)
            for r in rows[:1]:
                if r.get("url"):
                    sources_read.append({"area": a["area"], "url": r["url"], "title": r.get("title", ""), "read_on": dt.date.today().isoformat()})
    checked_on = dt.date.today().isoformat()
    facts = answer.get("facts", []) if not incomplete else []
    limits = answer.get("design_limits", []) if not incomplete else []
    lines = [f"FLAG: {overall}", "", reason, "", "Not legal advice. Drafts are checked by Charlie or a solicitor before use.", "",
             "## Facts", *[f"- {f}" for f in facts], "",
             "## Areas", "| Area | Question | Source | Finding | Flag |", "|---|---|---|---|---|",
             *[f"| {a['area']} | {a['question']} | {a['source']} | {a['finding']} | {a['flag']} |" for a in areas], "",
             "## Design limits that keep a caution inside the line", *([f"- {l}" for l in limits] or ["- none proposed"]), "",
             "## Sources read", *([f"- {s['area']}: {s['title']} {s['url']} (read {s['read_on']})" for s in sources_read] or ["- none: no search available this run"]), "",
             f"Checked on {checked_on}."]
    k.write(ctx, "clear/regulatory-screen.md", "\n".join(lines))
    k.write(ctx, "clear/regulatory-screen.json", {"flag": overall, "reason": reason, "areas": [{key: a[key] for key in ("area", "source", "finding", "flag")} for a in areas],
                                                  "design_limits": limits, "sources_read": sources_read, "checked_on": checked_on, "incomplete": incomplete})
    return {"summary": f"Regulatory screen: {overall}. {reason}", "flag": overall}


if __name__ == "__main__":
    k.run(main)
