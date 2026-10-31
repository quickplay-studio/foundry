"""Cold-Call Scripting: GitHub implementation of departments/sales/outreach-writing/cold-call-scripting/SKILL.md.

One script per ICP segment in sell/sequences/call-<segment>.md, one page, opening with the rules block
(Charlie calls live; no automated or recorded marketing calls; TPS and CTPS screening before dialling;
stop when told and suppress). The model drafts, code lints (opener under 15 seconds, two-sentence pitch
with the price, voicemail under 20 seconds with no price) and falls back to plain defaults. The
"take me off your list" branch is fixed text: confirm, thank, suppress. Nothing is dialled by this job.
"""
import csv
import io
import json
import re

from foundry import jobkit as k
from foundry import util

RULES = ["## Rules",
         "- Charlie makes every call himself, live. No automated or recorded marketing calls.",
         "- Screen each number against the TPS (individuals, sole traders, partnerships) and the CTPS (companies) before dialling. If a free check is not available for a number, do not call it.",
         "- Show the calling number. Give name and business when asked.",
         "- Stop when told to, and add the number to `sell/suppression.csv`.", ""]
NAMES = ["Not interested", "Send me an email", "We already use something", "No budget or too expensive", "Who are you", "Call me later"]
DEFAULT_OBJ = {"Not interested": ("Fair enough.", "Most people say that before they know what it does: it saves the time you spend on the problem. One question and I will leave you be.", "Thanks for your time, goodbye."),
               "Send me an email": ("Happy to.", "What address should I use, and what one thing should it answer?", "I will send it today. Thanks."),
               "We already use something": ("That makes sense.", "What do you like least about it? Mine does one thing differently.", "Good to know. Thanks for your time."),
               "No budget or too expensive": ("Understood.", "It is priced low enough to start without a budget line. Would the saving cover it?", "I will not push. Thank you."),
               "Who are you": ("Fair question.", "I am Charlie, I run this business in London and I am calling about a specific problem.", "If it is not relevant, say so and I will go."),
               "Call me later": ("Of course.", "When suits: morning or afternoon?", "I will ring then. Thanks.")}
DASH = re.compile(r"\s*[" + chr(0x2013) + chr(0x2014) + r"]\s*")  # model text never carries dashes into files


def b2b(ctx):
    audit = k.read(ctx, "audit.json", {}) or {}
    return "b2b" in (str(ctx["idea"].get("business_model", "")).lower(), str(audit.get("business_model", "")).lower())


def get_icp(ctx):
    data = k.read(ctx, "sell/icp.json", None)
    if not isinstance(data, dict):
        data = None
        for block in reversed(re.findall(r"```json\s*(.*?)```", k.read(ctx, "sell/icp.md", "") or "", re.S)):
            try:
                data = json.loads(block)
                break
            except ValueError:
                continue
    return data if isinstance(data, dict) and isinstance(data.get("segments"), list) else None


def plain(text, n=400):
    return re.sub(r"\s+", " ", DASH.sub(", ", str(text or "")).replace(chr(33), ".")).strip()[:n]


def main(ctx):
    if not b2b(ctx):
        return {"skipped": "no business buyer"}
    icp = get_icp(ctx)
    if not icp:
        return {"skipped": "no ICP yet (sell/icp.md): run icp-definition first"}
    idea = ctx["idea"]
    mvp = (idea.get("mvp") or ["does one job well"])[0] if isinstance(idea.get("mvp"), list) else "does one job well"
    money = str(idea.get("money", "")).rstrip(".") or "a simple monthly price"
    pains = (re.search(r"## Pains(.*?)(\n## |\Z)", k.read(ctx, "sell/icp.md", "") or "", re.S) or [None, ""])[1].strip()[:1000]
    proof = k.read(ctx, "sell/proof.json", {}) or {}
    leads = [r for r in csv.DictReader(io.StringIO(k.read(ctx, "sell/leads.csv", "") or "")) if r["tier"] == "A" and r["suppressed"] != "yes"][:20]
    segs = [s for s in icp["segments"] if isinstance(s, dict) and s.get("name")]
    notes, written = [], 0
    for seg in segs:
        name = str(seg["name"])
        ans = k.ask("Write a cold-call script for a solo UK founder calling a business. Plain, no hype, no exclamation marks. "
                    "opener: name, the reason for the call in one line, then ask permission ('Have you got thirty seconds?'), under 35 words. "
                    f"pitch: exactly two sentences, what the product does and the price ({money}). questions: three discovery questions taken from the pains. "
                    "ask: a 15 minute meeting with two slots offered. objections: for each of " + "; ".join(NAMES) + " give acknowledge, reply and exit (one line each). "
                    "gatekeeper: ask for the right person, never pretend to know them. voicemail: name, number as {{number}}, one reason, no price, under 45 words. "
                    "Return JSON only: {\"opener\": \"...\", \"pitch\": \"...\", \"questions\": [\"...\"], \"ask\": \"...\", \"objections\": [{\"name\": \"...\", \"acknowledge\": \"...\", \"reply\": \"...\", \"exit\": \"...\"}], "
                    "\"gatekeeper\": \"...\", \"voicemail\": \"...\"}\n\nPRODUCT\n" + str(idea.get("title", "")) + ": " + mvp + "\nSEGMENT " + name + "\nPAINS\n" + pains)
        ans = ans if isinstance(ans, dict) else {}
        opener, pitch = plain(ans.get("opener")), plain(ans.get("pitch"))
        vm, qs = plain(ans.get("voicemail")), [plain(q) for q in ans.get("questions", []) if isinstance(q, str)] if isinstance(ans.get("questions"), list) else []
        if not (opener and len(opener.split()) <= 35 and "?" in opener):
            opener = "Hello, it is Charlie from " + str(idea.get("title", "my business")) + ". I am calling about the time businesses like yours lose on this problem. Have you got thirty seconds?"
            notes.append("opener")
        if not (pitch and len(re.findall(r"[.?]", pitch)) <= 2 and re.search(r"£|\d|free|pound", pitch)):
            pitch = f"{idea.get('title', 'It')} {mvp.rstrip('.').lower()}. It costs {money}."
            notes.append("pitch")
        if not (vm and len(vm.split()) <= 45 and "£" not in vm and "{{number}}" in vm):
            vm = "Hello, it is Charlie. My number is {{number}}. I am calling about a time-saving idea for your business. I will try again, or you can ring me back."
            notes.append("voicemail")
        if len(qs) < 3:
            qs = (qs + ["How do you deal with this today?", "What does it cost you in time each week?", "Who decides on fixing it?"])[:3]
        objs = {o.get("name"): o for o in ans.get("objections", []) if isinstance(o, dict)} if isinstance(ans.get("objections"), list) else {}
        branches = []
        for n in NAMES:
            o = objs.get(n) or {}
            a, r, e = (plain(o.get(x), 200) for x in ("acknowledge", "reply", "exit"))
            if not (a and r and e):
                a, r, e = DEFAULT_OBJ[n]
            branches.append(f"### {n}\n- Acknowledge: {a}\n- Reply: {r}\n- Exit: {e}")
        branches.append("### Take me off your list\n- Confirm: Of course, I will take you off now.\n- Thank: Thanks for telling me, and sorry to have bothered you.\n- Suppress: add the number to `sell/suppression.csv` today. Never call again.")
        hooks = [re.search(r"## Opener\s*\n(.+)", k.read(ctx, f"sell/dossiers/{r['id']}.md", "") or "") for r in leads if r["segment"] == name]
        slot = (proof.get("segments") or {}).get(name, {}).get("primary", {}).get("line", "") if isinstance(proof, dict) else ""
        lines = [f"# Call script: {name}", "", *RULES, "## Opener (under 15 seconds)", opener, "", "## Pitch (two sentences) and discovery",
                 pitch, *[f"{i}. {q}" for i, q in enumerate(qs[:3], 1)], "", "## The ask", plain(ans.get("ask"), 250) or "Could we have a 15 minute call? I have Tuesday at 10 or Wednesday at 2.", "",
                 "## Objection branches", *branches, "", "## Gatekeeper", plain(ans.get("gatekeeper"), 250) or "Could you tell me who looks after this? I do not know the right person.", "",
                 "## Voicemail (under 20 seconds, no price)", vm, "", "## Tier A hooks from dossiers", *([f"- {m.group(1)}" for m in hooks if m][:3] or ["- none yet"]),
                 *(["", f"Proof line available: {slot}"] if slot else []), "", "## After the call", "Charlie logs each call in `sell/calls.csv`: `lead_id,date,outcome,note`. Revise after the first 10 calls."]
        k.write(ctx, f"sell/sequences/call-{util.slugify(name)}.md", "\n".join(lines))
        written += 1
    return {"summary": f"Call scripts for {written} segments, rules block first. Charlie reviews and dials; TPS and CTPS screening is his step." + (f" Defaults used for: {', '.join(sorted(set(notes)))}." if notes else ""), "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
