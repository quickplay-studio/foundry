"""Context Maintenance: GitHub implementation of departments/operations/knowledge/context-maintenance/SKILL.md.

Rebuilds the generated block at the end of brain.md from the JSON files (no model), appends new
meeting decisions to `## Decisions`, trims brain.md to 120 lines by moving the oldest decisions to
archive/brain-<date>.md, and writes proposed edits for the core sections to context/proposals.md
(the body of the `context: <slug>` pull request, which is not opened from here). The core sections
are never edited. The marker sha is a digest of the source files, not a git sha, so a run never
triggers the next one and a second run on the same state changes nothing.
"""
import hashlib
import json
import re

import requests

from foundry import jobkit as k, util

START = re.compile(r"<!-- context:start sha=(\S*) -->")
END = "<!-- context:end -->"
PRICE = re.compile(r"£\s?(\d[\d,]*(?:\.\d+)?)")
PASSED = ("pass", "passed", "ok", "success")


def gbp(x):
    try:
        return f"£{float(x or 0):,.2f}".replace(".00", "")
    except (TypeError, ValueError):
        return "£0"


def section(text, name):
    m = re.search(rf"^##\s+{name}\s*$(.*?)(?=^## |\Z)", text, re.S | re.M | re.I)
    return m.group(1).strip() if m else ""


def amounts(text):
    return {round(float(x.replace(",", "")), 2) for x in PRICE.findall(text or "")}


def meetings(ctx):
    out = []
    mdir = ctx["folder"] / "meetings"
    for p in sorted(mdir.glob("*.json")) if mdir.is_dir() else []:
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if isinstance(rec, dict) and p.name != "index.json":
            out.append((p.name, rec))
    return out


def get(url, token=""):
    try:
        r = requests.get(url, timeout=10, headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github.raw"} if token else {})
        return r.status_code, r.text
    except Exception:  # noqa: BLE001
        return 0, ""


def contradictions(ctx, brain, qa):
    out, idea = [], ctx["idea"]
    money = section(brain, "money") or str(idea.get("money", ""))
    pages = []
    live = str((ctx["board"] or {}).get("live_url") or (ctx["board"] or {}).get("url") or "")
    if live.startswith("http"):
        pages.append(("landing page " + live, k.fetch(live)))
    if k.secret("GH_TOKEN"):
        pages.append(("venture README.md", get(f"https://api.github.com/repos/quickplay-studio/{ctx['slug']}/contents/README.md", k.secret("GH_TOKEN"))[1]))
    for name, text in pages:
        if amounts(money) and amounts(text) and not amounts(money) & amounts(text):
            out.append(("brain.md", money[:120], f"use the price shown in the {name}, or fix the {name}", f"price in `money` does not match the {name}", "## Money"))
    bad = [str(c.get("id")) for c in qa.get("checks", []) if isinstance(c, dict) and str(c.get("result", "")).lower() not in PASSED] if isinstance(qa, dict) else []
    if bad:
        out.append(("brain.md", section(brain, "mvp")[:120].replace("\n", " / ") or "(mvp section)", "mark the unmet bullets as not yet built", "qa/result.json has failed checks: " + ", ".join(bad[:6]), "qa/result.json checks"))
    for link in re.findall(r"https?://[^\s)>\]]+", section(brain, "proof"))[:5]:
        status = get(link)[0]
        if status == 0 or status >= 400:
            out.append(("brain.md", link, "remove or replace the link", f"proof link returns {status or 'no answer'}", "## Proof"))
    return out


def decisions_span(head):
    """(start, end) of the body of `## Decisions` in head, or None."""
    m = re.search(r"^## Decisions[ \t]*\n?", head, re.M)
    if not m:
        return None
    nxt = re.search(r"^## ", head[m.end():], re.M)
    return m.end(), (m.end() + nxt.start() if nxt else len(head))


def add_decisions(head, new):
    span = decisions_span(head)
    if not span:
        return head + "\n\n## Decisions\n" + "\n".join(new)
    body = "\n".join(ln for ln in head[span[0]:span[1]].splitlines() if ln.strip() not in ("", "-"))  # drop the empty placeholder bullet
    rest = head[span[1]:]
    return head[:span[0]] + (body + "\n" if body else "") + "\n".join(new) + ("\n\n" + rest if rest else "")


def trim(ctx, head, block_len, today):
    """Keep brain.md at 120 lines: move the oldest decisions to archive/brain-<date>.md, leave one pointer line."""
    total = len(head.splitlines()) + 1 + block_len
    span = decisions_span(head)
    if total <= 120 or not span:
        return head, []
    body = head[span[0]:span[1]].strip("\n").splitlines()
    old = [ln for ln in body if ln.startswith("- ") and len(ln.strip()) > 1 and not ln.startswith("- Older decisions:")]
    pointer = f"- Older decisions: archive/brain-{today}.md"
    n = 0
    while n < len(old) and total - n + (0 if pointer in body else 1) > 120:
        n += 1
    moved = old[:n]
    if not moved:
        return head, []
    keep = ([] if pointer in body else [pointer]) + [ln for ln in body if ln not in moved]
    rest = head[span[1]:]
    head = head[:span[0]] + "\n".join(keep) + ("\n\n" + rest if rest else "")
    prev = k.read(ctx, f"archive/brain-{today}.md", "") or f"# Archived decisions from brain.md ({today})\n"
    k.write(ctx, f"archive/brain-{today}.md", prev.rstrip("\n") + "\n" + "\n".join(moved))
    return head, moved


def main(ctx):
    brain = k.read(ctx, "brain.md", "") or ""
    if not brain.strip():
        return {"skipped": "brain.md is missing"}
    board = ctx["board"] if isinstance(ctx["board"], dict) else (k.read(ctx, "board.json", {}) or {})
    budget, qa = ctx["budget"] or {}, k.read(ctx, "qa/result.json", {}) or {}
    latest, recs = k.read(ctx, "status/latest.md", "") or "", meetings(ctx)
    digest = hashlib.sha256(json.dumps([board, budget, qa, latest, recs], sort_keys=True, default=str).encode()).hexdigest()[:12]
    marker = START.search(brain)
    if marker and marker.group(1) == digest:
        return {"skipped": "no change since the recorded sha"}
    end = brain.find(END)
    head = (brain[:marker.start()] if marker and end > marker.start() else brain).rstrip("\n")
    today = util.today()
    gates = board.get("gates") or {}
    passed = [s for s in gates if gates[s] == "passed"]
    checks = [c for c in qa.get("checks", []) if isinstance(c, dict)] if isinstance(qa, dict) else []
    open_inc = sum(1 for i in board.get("incidents") or [] if isinstance(i, dict) and i.get("status") in ("open", "mitigated"))
    questions = sum(len(r.get("open_questions") or []) for _, r in recs)
    block = [f"<!-- context:start sha={digest} -->", "<!-- generated by context-maintenance: do not edit by hand -->", "## Current state",
             f"- Stage: {board.get('stage', 'unknown')}", f"- Last gate passed: {passed[-1] if passed else 'none'}",
             f"- MVP status: {sum(str(c.get('result', '')).lower() in PASSED for c in checks)} of {len(checks)} QA checks passed" if checks else "- MVP status: no QA result yet",
             f"- Price: {ctx['idea'].get('money') or 'not set'}", f"- Spend: {gbp(budget.get('spent'))} of {gbp(budget.get('ad_budget'))} ad budget, revenue {gbp(budget.get('revenue'))}",
             f"- Open incidents: {open_inc}", f"- Open decisions: {questions} open questions from meetings", f"- Last updated: {str(board.get('updated', 'unknown'))[:10]}", END]
    new = []  # new decisions, append only
    for name, rec in recs:
        for d in rec.get("decisions") or []:
            text = re.sub(r"\s+", " ", str(d.get("text", "") if isinstance(d, dict) else d)).strip()[:200]
            line = f"- {rec.get('date', '')}, {text}, meetings/{name}"
            if text and line not in brain and line not in new:
                new.append(line)
    if new:
        head = add_decisions(head, new)
    head, moved = trim(ctx, head, len(block), today)
    k.write(ctx, "brain.md", head.rstrip("\n") + "\n\n" + "\n".join(block))
    found = contradictions(ctx, brain, qa)
    if found:
        body = ["# Proposed edits to the core sections", "", f"Body for the pull request `context: {ctx['slug']}`. The job does not edit these sections.", ""]
        for f_, old_, new_, why, src in found:
            body += [f"- File: {f_}", f"  Old text: {old_}", f"  New text: {new_}", f"  Reason: {why}", f"  Source line: {src}", ""]
        k.write(ctx, "context/proposals.md", "\n".join(body))
    total = len((head + "\n\n" + "\n".join(block)).splitlines())
    return {"summary": f"Block refreshed, {len(new)} decisions appended, {len(moved)} archived, {len(found)} proposed edits; brain.md is {total} lines" + (" (over 120)" if total > 120 else ""),
            "flag": "caution" if found or total > 120 else "ok"}


if __name__ == "__main__":
    k.run(main)
