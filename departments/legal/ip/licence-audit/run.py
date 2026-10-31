"""Licence Audit: GitHub implementation of departments/legal/ip/licence-audit/SKILL.md.

Dependencies come from the venture repo (GitHub SBOM and manifests, needs GH_TOKEN); each licence is the SPDX id from PyPI,
npm or deps.dev, classified in code. The free model only lists assets named in the brain. Unknown is a finding, never a pass.
Issues for stops are drafted, not opened. Not legal advice.
"""
import base64
import datetime as dt
import json
import re
from urllib.parse import unquote

import requests

from foundry import jobkit as k

MANIFESTS = {"requirements.txt": "runtime", "requirements-dev.txt": "dev", "dev-requirements.txt": "dev", "package.json": "runtime"}
RANK = {"permissive": 0, "weak copyleft": 1, "unknown": 2, "strong copyleft": 3, "restricted": 4}
ORDER = {"clear": 0, "caution": 1, "stop": 2}
NOTICE = "Not legal advice. Drafts are checked by Charlie or a solicitor before use."


def api(url, token=None):
    """JSON from a free API; None on any failure."""
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"} if token else {}, timeout=15)
        return r.json() if r.ok else None
    except Exception:  # noqa: BLE001
        return None


def classify(lic):
    """Licence string or SPDX expression to a class. OR takes the best alternative, AND the worst."""
    s = str(lic or "").upper()
    for a, b in (("GNU AFFERO GENERAL PUBLIC", "AGPL"), ("GNU LESSER GENERAL PUBLIC", "LGPL"), ("GNU GENERAL PUBLIC", "GPL")):
        s = s.replace(a, b)
    if not s.strip() or re.fullmatch(r"\W*(UNKNOWN|NOASSERTION|NONE|OTHER)\W*", s):
        return "unknown"
    if " OR " in s:
        return min((classify(x) for x in s.split(" OR ")), key=RANK.get)
    if " AND " in s:
        return max((classify(x) for x in s.split(" AND ")), key=RANK.get)
    if re.search(r"-NC|NONCOMMERCIAL|NON-COMMERCIAL|-ND\b|NODERIV|BUSL|BUSINESS SOURCE|SSPL|ELASTIC|COMMONS.?CLAUSE|SUSTAINABLE USE|POLYFORM|AGPL", s):
        return "restricted"
    if re.search(r"(?<!L)GPL", s):
        return "strong copyleft"
    if re.search(r"LGPL|MPL|EPL|CDDL|SHARE.?ALIKE|-SA\b|ODBL", s):
        return "weak copyleft"
    if re.search(r"\b(MIT|BSD|ISC|PSF|OGL|OFL|0BSD|CC0|WTFPL|ZLIB)\b|APACHE|UNLICENSE|PYTHON SOFTWARE FOUNDATION|PUBLIC DOMAIN|CC.BY\b|ATTRIBUTION|OPEN GOVERNMENT|OPEN FONT|UNSPLASH|PEXELS|PIXABAY", s):
        return "permissive"
    return "unknown"


def resolve(eco, name, ver):
    """(licence, source checked) from the registry, then deps.dev as the cross-check."""
    if eco == "pypi":
        d = api(f"https://pypi.org/pypi/{name}/{ver}/json" if ver else f"https://pypi.org/pypi/{name}/json")
        info = (d or {}).get("info", {}) if isinstance(d, dict) else {}
        lic = info.get("license_expression") or " OR ".join(c.split("::")[-1].strip() for c in info.get("classifiers", []) if c.startswith("License ::")) or str(info.get("license") or "")[:200]
        src = "PyPI JSON API"
    else:
        d = api(f"https://registry.npmjs.org/{name}/{ver or 'latest'}")
        lic = (d or {}).get("license", "") if isinstance(d, dict) else ""
        lic = lic.get("type", "") if isinstance(lic, dict) else lic
        src = "npm registry"
    if classify(lic) == "unknown" and ver:
        d = api(f"https://api.deps.dev/v3/systems/{eco}/packages/{name}/versions/{ver}")
        alt = " OR ".join((d or {}).get("licenses", [])) if isinstance(d, dict) else ""
        if alt:
            lic, src = alt, "deps.dev"
    return str(lic)[:80], src


def repo_deps(repo, token):
    """{(eco, name): {version, scope}} from the manifests, then the SBOM for transitive packages; plus whether the repo was readable."""
    deps, read = {}, False

    def add(key, version, scope):
        if deps.get(key, {}).get("scope") != "runtime":  # runtime beats dev when a package is in both
            deps[key] = {"version": version, "scope": scope}

    for path, scope in MANIFESTS.items():
        d = api(f"https://api.github.com/repos/{repo}/contents/{path}", token)
        if not isinstance(d, dict) or "content" not in d:
            continue
        read = True
        body = base64.b64decode(d["content"]).decode("utf-8", "ignore")
        if path == "package.json":
            try:
                pkg = json.loads(body)
            except ValueError:
                continue
            for sect, sc in (("dependencies", "runtime"), ("devDependencies", "dev")):
                for n, v in (pkg.get(sect) or {}).items():
                    add(("npm", n), re.sub(r"^[^\d]*", "", str(v)) if re.match(r"^[\^~]?\d", str(v)) else "", sc)
        else:
            for line in body.splitlines():
                line = line.split("#")[0].strip()
                if line and not line.startswith("-"):
                    m = re.match(r"([A-Za-z0-9_.\-]+)(?:\[[^\]]*\])?\s*(?:==\s*([\w.]+))?", line)
                    if m:
                        add(("pypi", m.group(1).lower()), m.group(2) or "", scope)
    sbom = api(f"https://api.github.com/repos/{repo}/dependency-graph/sbom", token)
    for p in (sbom or {}).get("sbom", {}).get("packages", []) if isinstance(sbom, dict) else []:
        for ref in p.get("externalRefs", []):
            m = re.match(r"pkg:(pypi|npm)/([^@]+)@?(.*)", str(ref.get("referenceLocator", "")))
            if m:
                read = True
                deps.setdefault((m.group(1), unquote(m.group(2)).lower()), {"version": m.group(3).split("?")[0], "scope": "transitive"})
    return deps, read


def main(ctx):
    idea, brain = ctx["idea"], ctx["brain"]
    day = dt.date.today().isoformat()
    token = k.secret("GH_TOKEN")
    repo = str(idea.get("repo") or f"quickplay-studio/{ctx['slug']}")
    why, rows = [], []
    deps, read = repo_deps(repo, token) if token else ({}, False)
    if not token:
        why.append("GH_TOKEN missing, so the venture repo and registries were not read: dependencies unaudited")
    elif not read:
        why.append(f"repo {repo} not readable, so dependencies are unaudited")
    for i, ((eco, name), d) in enumerate(sorted(deps.items(), key=lambda kv: (kv[1]["scope"] == "transitive", kv[0]))):
        lic, src = resolve(eco, name, d["version"]) if i < 80 else ("", "not resolved (lookup cap of 80)")
        rows.append({"item": name, "type": f"{eco} package", "version": d["version"] or "unpinned", "licence": lic or "unknown", "source": src, "scope": d["scope"], "cls": classify(lic)})
    text = (json.dumps(idea, ensure_ascii=False) + " " + brain).lower()
    distributed = bool(re.search(r"\bios\b|android|app store|desktop app|extension|distribut", text))
    ans = k.ask("You list the fonts, images, icons, audio, datasets, APIs and AI-generated media a product uses, only those the venture text names. Not legal advice. "
                "Return JSON only: {\"assets\": [{\"name\": \"...\", \"kind\": \"font|image|icon|audio|dataset|api|ai-media\", \"source\": \"...\", \"source_url\": \"https://...\", \"claimed_licence\": \"...\"}], \"reason\": \"<one sentence>\"}\n\nVENTURE\n"
                + json.dumps(idea, ensure_ascii=False)[:2000] + "\n\nBRAIN\n" + brain[:3500])
    if not isinstance(ans, dict):
        why.append("no free model answered, so fonts, images and datasets were not listed")
    for a in [a for a in (ans or {}).get("assets", []) if isinstance(a, dict)][:15] if isinstance((ans or {}).get("assets"), list) else []:
        url, claimed = str(a.get("source_url", "")), str(a.get("claimed_licence", ""))
        page = k.fetch(url, 20000) if url.startswith("http") else ""
        page = page if len(page) >= 200 else ""
        c1, c2 = classify(claimed), classify(page[:6000]) if page else "unknown"
        if c1 == "unknown":
            cls, note = c2, "class read from page text by pattern: confirm" if c2 != "unknown" else ""
        elif not page:
            cls, note = c1, "licence claimed, source page not read: unverified"
        elif c2 == c1:
            cls, note = c1, ""
        elif c2 == "unknown":
            cls, note = c1, "claimed licence not found on the page read: unverified"
        else:
            cls, note = max((c1, c2), key=RANK.get), f"page text suggests {c2}, claimed {c1}: check"
        kind = str(a.get("kind", "asset"))[:20]
        row = {"item": str(a.get("name", ""))[:60], "type": kind, "version": "", "licence": claimed[:60] or "not stated", "source": f"{url} (read {day})" if page else (url or "none given") + " (not read)", "scope": "asset", "cls": cls}
        if note:
            row["note"] = note
        if kind == "ai-media":
            row["note"] = "UK copyright in AI output is unsettled; read the generator's current terms on commercial use and output ownership"
        if re.search(r"scrap|crawl", str(a.get("source", "")).lower()):
            row["note"] = "scraped source: a site whose terms forbid scraping cannot be used; read the terms"
        rows.append(row)
    for r in rows:
        c, scope = r["cls"], r["scope"]
        flag = "clear"
        if c == "restricted" or (c == "strong copyleft" and scope == "runtime"):
            flag = "stop" if scope in ("runtime", "asset") else "caution"
        elif c in ("unknown", "strong copyleft") or r.get("note"):
            flag = "caution"
        r["flag"] = flag
        r["verdict"] = {"permissive": "ok with notice", "weak copyleft": "ok as an unmodified library or share-alike duty: check", "strong copyleft": "conflict for shipped closed or hosted code", "restricted": "not allowed in shipped code", "unknown": "finding: licence unknown"}[c]
        r["action"] = r.get("note") or {"permissive": "Keep the notice", "weak copyleft": "Do not modify; keep source link", "strong copyleft": "Replace, or Charlie accepts the obligation", "restricted": "Remove or replace", "unknown": "Read the licence by hand"}[c]
    flag = max(["caution" if why else "clear"] + [r["flag"] for r in rows], key=ORDER.get)
    stops = [r for r in rows if r["flag"] == "stop"]
    if stops or any(r["flag"] == "caution" for r in rows):
        why.append(f"{len(stops)} stop and {sum(r['flag'] == 'caution' for r in rows)} caution items")
    reason = "; ".join(why) or "Every dependency and asset resolved to a commercial-use licence."
    notices = ["# Third-party notices", "", *[f"- {r['item']} {r['version']}".strip() + f": {r['licence']} ({r['source']})" for r in rows if r["cls"] in ("permissive", "weak copyleft")]]
    issues = [{"title": f"Licence stop: {r['item']}", "body": f"{r['item']} {r['version']} is {r['licence']} ({r['verdict']}). Action: {r['action']}."} for r in stops]
    cell = lambda v: str(v).replace("|", "/").replace("\n", " ")
    lines = [f"FLAG: {flag}", "", reason, "", NOTICE, "", f"Venture repo: {repo}. Shipped as: {'distributed app or extension' if distributed else 'hosted service'}. Checked {day}.", "",
             "## Licences", "| Item | Type | Version | Licence | Source checked | Verdict | Action |", "|---|---|---|---|---|---|---|",
             *([f"| {cell(r['item'])} | {cell(r['type'])} | {cell(r['version'])} | {cell(r['licence'])} | {cell(r['source'])} | {cell(r['verdict'])} ({r['flag']}) | {cell(r['action'])} |" for r in rows] or ["| none audited | | | | | | |"]), "",
             "## Issue drafts for each stop (not opened by the job)", *([f"- {i['title']}: {i['body']}" for i in issues] or ["- none"]), "", "## Draft NOTICES.md", "```markdown", *notices, "```"]
    k.write(ctx, "clear/licence-audit.md", "\n".join(lines))
    k.write(ctx, "clear/licence-audit.json", {"flag": flag, "notice": NOTICE, "reason": reason, "checked_on": day, "repo": repo, "rows": [{key: r.get(key, "") for key in ("item", "type", "version", "licence", "source", "verdict", "action", "scope", "flag")} for r in rows],
                                              "notices": "\n".join(notices), "issue_drafts": issues})
    return {"summary": f"Licence audit: {flag}. {reason}"[:300], "flag": flag}


if __name__ == "__main__":
    k.run(main)
