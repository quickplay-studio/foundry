"""Portal Sync: GitHub implementation of departments/operations/client-comms/portal-sync/SKILL.md.

Builds portal/status.json from the allow-list in portal/scope.json (venture folder copy, else read
from the venture repo with GH_TOKEN), stages shared deliverables in portal/files/, and runs the leak
check before anything is written. It opens no pull request: portal/publish-commands.md holds the exact
git and gh commands for the rolling `portal-sync` branch. No model.
"""
import datetime as dt
import json
import re
import shutil

import requests

from foundry import jobkit as k, util

KEY = re.compile(r"AIza[\w-]{20,}|gsk_\w{20,}|\bsk-[\w-]{20,}|ghp_\w{20,}")
MAX_BYTES = 2_000_000


def numbers(obj):
    if isinstance(obj, bool):
        return set()
    if isinstance(obj, (int, float)):
        return {round(float(obj), 2)} if obj else set()
    return {n for v in (obj.values() if isinstance(obj, dict) else obj if isinstance(obj, list) else []) for n in numbers(v)}


def leak_check(texts, scope, budget):
    """Names of the checks that failed, never the matched text. Kept separate so it cannot be skipped."""
    blob, bad = "\n".join(texts), []
    if KEY.search(blob):
        bad.append("key pattern")
    found = {round(float(x.replace(",", "")), 2) for x in re.findall(r"£\s?(\d[\d,]*(?:\.\d+)?)", blob)}
    if numbers(budget) & found:
        bad.append("pound figure from budget.json")
    allowed = {str(e).lower() for e in scope.get("allowed_emails") or []}
    if any(e.lower() not in allowed for e in re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", blob)):
        bad.append("email address")
    if any(str(n).strip() and re.search(r"\b" + re.escape(str(n).strip().lower()) + r"\b", blob.lower()) for n in scope.get("never") or []):
        bad.append("never list")
    return bad


def load_scope(ctx):
    scope = k.read(ctx, "portal/scope.json")
    token = k.secret("GH_TOKEN")
    if scope is None and token:
        try:
            r = requests.get(f"https://api.github.com/repos/quickplay-studio/{ctx['slug']}/contents/portal/scope.json", timeout=20,
                             headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github.raw"})
            scope = json.loads(r.text) if r.ok else None
        except Exception:  # noqa: BLE001
            scope = None
    return scope if isinstance(scope, dict) else None


def front_share(text):
    m = re.match(r"---\s*\n(.*?)\n---", text, re.S)
    return bool(m and re.search(r"^share:\s*true\s*$", m.group(1), re.M | re.I))


def main(ctx):
    scope = load_scope(ctx)
    if not scope:
        return {"skipped": "portal/scope.json not found: portal-provisioning has not run, or copy it into the venture folder"}
    allow = next((scope[key] for key in ("allow", "allowed", "allow_list", "allowlist", "fields") if isinstance(scope.get(key), list)), [])
    never = {str(n) for n in scope.get("never") or []}
    if not allow:
        return {"skipped": "scope.json has no allow-list"}
    board = ctx["board"] if isinstance(ctx["board"], dict) else {}
    jobs = [j for j in board.get("jobs") or [] if isinstance(j, dict)]
    today = util.today()
    latest = "\n".join(ln for ln in (k.read(ctx, "status/latest.md", "") or "").splitlines() if not ln.startswith("Spend:")).strip()
    index = k.read(ctx, "deliverables/index.json", []) or []
    shared, files = [], []
    for d in index if isinstance(index, list) else []:
        src = (ctx["folder"] / str(d.get("path", ""))).resolve() if isinstance(d, dict) and d.get("share") is True else None
        if src and src.is_file() and ctx["folder"].resolve() in src.parents and src.suffix.lower() in (".pdf", ".md", ".csv") and src.stat().st_size <= MAX_BYTES:
            shared.append({"title": str(d.get("title", src.name)), "url": f"files/{src.name}", "date": str(d.get("date", ""))})
            files.append(src)
    recaps, staged = [], {}
    for p in sorted((ctx["folder"] / "meetings").glob("*-recap.md")) if (ctx["folder"] / "meetings").is_dir() else []:
        date, text = p.name[:10], p.read_text(encoding="utf-8")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) and date < today and front_share(text):  # default is not shared
            title = re.search(r"^# Recap: (.*?)(?: \(\d{4}-\d{2}-\d{2}\))?$", text, re.M)
            recaps.append({"date": date, "title": title.group(1) if title else p.stem, "url": f"files/{p.name}"})
            staged[p.name] = re.sub(r"\s*\(@[\w-]+\)", "", re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, flags=re.S))  # no front matter, no handles
    nxt = next((j["id"] for j in jobs if j.get("status") != "done" and j.get("id")), "")
    fields = {"updated": util.now(), "stage": board.get("stage", ""), "gates": board.get("gates", {}), "jobs_done": sum(j.get("status") == "done" for j in jobs),
              "jobs_total": len(jobs), "next": nxt, "latest_update": latest, "deliverables": shared, "recaps": recaps}
    status = {key: v for key, v in fields.items() if key in allow and key not in never}
    texts = [json.dumps(status, ensure_ascii=False)] + [f.read_bytes().decode("latin-1") for f in files] + list(staged.values())
    bad = leak_check(texts, scope, ctx["budget"] or {})
    if bad:
        return {"skipped": "leak check failed: " + ", ".join(bad), "flag": "caution"}
    prior = k.read(ctx, "portal/status.json", {}) or {}
    for f in files:
        ctx["outputs"].append(f"portal/files/{f.name}")
        if not ctx["dry_run"]:
            (ctx["folder"] / "portal" / "files").mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, ctx["folder"] / "portal" / "files" / f.name)
    for name, text in staged.items():
        k.write(ctx, f"portal/files/{name}", text)
    k.write(ctx, "portal/status.json", status)
    slug = ctx["slug"]
    cmds = ["# Publish the portal sync", "", "Nothing is pushed from the job. Run from the root of the private foundry-ventures checkout:", "", "```",
            f"git clone https://github.com/quickplay-studio/{slug} /tmp/{slug}-portal && cd /tmp/{slug}-portal",
            "git checkout -B portal-sync", "mkdir -p portal/files",
            f"cp <ventures checkout>/ventures/{slug}/portal/status.json portal/status.json",
            f"cp -r <ventures checkout>/ventures/{slug}/portal/files/. portal/files/ 2>/dev/null || true",
            'git add portal && git commit -m "portal-sync: status" && git push -f origin portal-sync',
            f"gh pr view portal-sync -R quickplay-studio/{slug} || gh pr create -R quickplay-studio/{slug} --head portal-sync --title \"portal-sync\" --body \"Rolling status update.\"", "```",
            "", "After merging and redeploying, open the live status.json and check `updated` is within 24 hours."]
    k.write(ctx, "portal/publish-commands.md", "\n".join(cmds))
    note = ""
    url = str(board.get("portal_url") or "").rstrip("/")
    if url.startswith("http") and prior.get("updated"):
        try:
            live = requests.get(url + "/status.json", timeout=15).json().get("updated", "")
            old = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(str(prior["updated"]).replace("Z", "+00:00"))).total_seconds() > 86400
            note = "; live portal is stale (updated does not match the last sync)" if old and live != prior["updated"] else ""
        except Exception:  # noqa: BLE001
            note = "; live portal status.json could not be read"
    return {"summary": f"portal/status.json built with {len(status)} allowed fields, {len(files) + len(staged)} files staged; commands in portal/publish-commands.md{note}", "flag": "caution" if note else "ok"}


if __name__ == "__main__":
    k.run(main)
