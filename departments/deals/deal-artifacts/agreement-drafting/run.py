"""Agreement Drafting: GitHub implementation of departments/deals/deal-artifacts/agreement-drafting/SKILL.md.

Fills only the merge fields (square-bracket blanks) of Legal's services agreement template from clear/, for each deal at
verbal_yes with no draft. Clauses are copied unchanged. Anything the proposal and pricing do not settle becomes
{{MISSING: field}}. Requested changes go on a page for the solicitor, never into the clauses. Not legal advice; nothing is
sent, signed or marked won, and the pull request is a note in sell/alerts.md.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import dealkit as D  # noqa: E402
from foundry import jobkit as k  # noqa: E402

HEADER = "DRAFT. Not legal advice. Do not send or sign until a solicitor or Charlie has approved it."
CHECKLIST = ["Parties correct", "Fees match pricing", "No MISSING markers", "Requested changes reviewed", "Solicitor or Charlie sign-off"]
CHANGE = re.compile(r"liabilit\w*|indemn\w*|intellectual property|\bIP\b|terminat\w*|data protection|GDPR|payment terms|net \d+|late payment", re.I)
FIELD = re.compile(r"\[([^\[\]\n]{2,80})\](?!\()")


def find_template(ctx):
    text = k.read(ctx, "clear/contract-template.md", None)
    if text:
        return text, "clear/contract-template.md"
    found = [p for p in D.files(ctx, "clear/contracts/*.md") if not p.name.endswith("review-note.md")]
    found.sort(key=lambda p: ("services" not in p.name.lower(), p.name))
    return (found[0].read_text(encoding="utf-8"), found[0].relative_to(ctx["folder"]).as_posix()) if found else (None, "")


def section(md, title):
    m = re.search(rf"^## +{title}[^\n]*\n(.*?)(?=^## |\Z)", md, re.M | re.S | re.I)
    return m.group(1).strip() if m else ""


def bullets(text):
    return [re.sub(r"^[-*]\s+", "", ln).strip() for ln in text.splitlines() if re.match(r"\s*[-*]\s+", ln)]


def proposal_price(meta, md):
    try:
        if meta.get("price_gbp"):
            return float(re.sub(r"[^\d.]", "", meta["price_gbp"]))
    except ValueError:
        pass
    m = re.search(r"£\s?([\d,]+(?:\.\d+)?)", section(md, "Investment"))
    return float(m.group(1).replace(",", "")) if m else None


def main(ctx):
    gate = D.gate(ctx)
    if gate:
        return gate
    tmpl, tpath = find_template(ctx)
    if not tmpl:
        return {"skipped": "no services agreement template in clear/ (Legal contract-drafting has not written one); never drafted from nothing"}
    rows, replies, made, lines = D.pipeline(ctx), k.read(ctx, "sell/replies.json", []) or [], 0, []
    for row in rows:
        deal, company = row.get("id", ""), row.get("company") or "the customer"
        if row.get("stage") != "verbal_yes" or (ctx["folder"] / "sell/agreements" / f"{deal}-draft.md").exists():
            continue
        props = sorted(D.files(ctx, f"sell/proposals/{deal}-v*.md"), key=lambda p: int(re.search(r"-v(\d+)\.md$", p.name).group(1)))
        price = D.approved_price(ctx, deal)
        if not props or not price:
            lines.append(f"Agreement blocked for {company}: needs a proposal in sell/proposals/ and an approved sell/pricing/{deal}.md")
            continue
        meta, md = D.front(props[-1].read_text(encoding="utf-8"))
        shown = proposal_price(meta, md)
        if shown is None or abs(shown - price) > 0.5:
            lines.append(f"Price mismatch: {company}: proposal says {'no figure' if shown is None else format(shown, 'g')}, approved pricing says {price:g}")
            continue
        scope = bullets(section(md, "What we will do"))
        schedule = "\n".join(f"{i}. {s}" for i, s in enumerate(scope, 1)) or "{{MISSING: services schedule}}"
        invest = section(md, "Investment")
        included = bullets(invest.split("Not included")[0].split("Included:")[1]) if "Included:" in invest else []
        missing, uses_schedule = [], False

        def fill(m):
            nonlocal uses_schedule
            low = m.group(1).lower()
            if re.search(r"customer|client|counterparty", low) and "address" not in low and "number" not in low:
                return company
            if "payment" in low:
                missing.append("payment schedule")
                fee = f"£{price:,.0f}; payment schedule " if re.search(r"fee|price|charge", low) else ""
                return fee + "{{MISSING: payment schedule}}"
            if re.search(r"service|schedule|scope", low):
                uses_schedule = True
                return schedule
            if re.search(r"fee|price|charge", low) and "payment" not in low:
                return f"£{price:,.0f}"
            if "deliverable" in low and (included or scope):
                return "; ".join(included or scope)
            missing.append(m.group(1))
            return "{{MISSING: " + m.group(1) + "}}"

        body = FIELD.sub(fill, tmpl)
        if not uses_schedule:
            body += f"\n\n## Schedule 1: Services\n\n{schedule}\n"
        asked = []
        for r in replies:
            hit = CHANGE.search(str(r.get("summary", ""))) if isinstance(r, dict) and r.get("deal_id") == deal else None
            if hit:
                asked.append(f"{hit.group(0).lower()} (reply {r.get('id')}): {D.txt(r.get('summary'), 160)}")
        for p in D.files(ctx, f"sell/debriefs/{deal}-*.json"):
            d = k.read(ctx, f"sell/debriefs/{p.name}", {}) or {}
            asked += [f"{CHANGE.search(o['quote']).group(0).lower()} (debrief): \"{D.txt(o['quote'], 160)}\"" for o in D.lst(d.get("objections")) if isinstance(o, dict) and CHANGE.search(str(o.get("quote", "")))]
        doc = [HEADER, "", f"# Agreement draft: {company} ({deal})", "", f"Template: {tpath}. Proposal: {props[-1].name}. Approved price: £{price:,.0f}.", "",
               f"## Missing fields ({len(missing)})", *([f"- {f}" for f in missing] or ["- none"]), "", "## Sign-off checklist", *[f"- [ ] {c}" for c in CHECKLIST], "",
               "## Requested changes (for the solicitor, not drafted in)", *([f"- {a}" for a in asked] or ["- none recorded"]),
               "- The Gmail thread is not read on GitHub: add any change the prospect asked for by email.", "", "---", "", body]
        k.write(ctx, f"sell/agreements/{deal}-draft.md", "\n".join(doc))
        lines.append(f"Agreement draft: {company}: sell/agreements/{deal}-draft.md. Checklist: " + "; ".join(CHECKLIST) + f". {len(missing)} fields missing.")
        made += 1
    D.alert(ctx, "agreement-drafting", lines)
    if not made:
        return {"skipped": "no verbal_yes deal ready for a draft" + (f" ({lines[0]})" if lines else "")}
    return {"summary": f"{made} agreement drafts written from {tpath}; nothing sent, signed or marked won.", "flag": "caution"}


if __name__ == "__main__":
    k.run(main)
