"""Keep one "Needs you" issue in the private repo in step with the digest, so GitHub emails Charlie when the list changes.

    python -m foundry.notify            # after foundry.digest; needs VENTURES_TOKEN with Issues read and write

Reads office/digest.md, takes the "Needs you" items per venture, compares them with office/needs-last.json and,
when they changed, creates or updates the open issue titled "Needs you" in quickplay-studio/foundry-ventures and
adds one comment listing what is new (an edit to the body sends no email; a comment does). Without the token, or
with a token that lacks the Issues permission, it prints one line and does nothing. Nothing else is posted anywhere.
"""
import hashlib
import json
import os
import re

import requests

from . import digest, util

API = f"https://api.github.com/repos/{digest.REPO}"
TITLE = "Needs you"
LAST = util.OFFICE / "needs-last.json"


def needs(text):
    """{venture heading: [items]} from the digest, only the Needs you sections with real items."""
    out, venture, section = {}, None, None
    for line in text.splitlines():
        h = re.match(r"^## (.+)$", line)
        if h:
            venture, section = h.group(1), None
            continue
        if line.startswith("### "):
            section = line[4:].strip()
            continue
        if section == "Needs you" and line.startswith("- ") and not line.startswith("- Nothing."):
            out.setdefault(venture, []).append(line[2:].strip())
    return out


def body(items):
    lines = [f"Written by the jobs workflow after each run from `office/digest.md`. Do not edit; it is rewritten. Last change {util.now()}.", ""]
    for venture, rows in items.items():
        lines += [f"### {venture}", *(f"- {r}" for r in rows), ""]
    return "\n".join(lines).rstrip() + "\n"


def main():
    token = os.environ.get("VENTURES_TOKEN", "").strip()
    text = digest.OUT.read_text(encoding="utf-8") if digest.OUT.exists() else ""
    items = needs(text)
    digest_hash = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()[:16]
    last = util.read_json(LAST, {}) or {}
    if last.get("hash") == digest_hash:
        print("needs you: unchanged, no issue update")
        return 0
    if not token:
        print("needs you: VENTURES_TOKEN not set, issue not updated")
        return 0
    h = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    try:
        r = requests.get(f"{API}/issues", params={"state": "open", "per_page": 50}, headers=h, timeout=30)
        if r.status_code in (403, 404):
            print(f"needs you: the token cannot read issues on {digest.REPO} (HTTP {r.status_code}); give it Issues read and write to get emails")
            return 0
        r.raise_for_status()
        issue = next((i for i in r.json() if isinstance(i, dict) and i.get("title") == TITLE and not i.get("pull_request")), None)
        new = [f"{v}: {x}" for v, rows in items.items() for x in rows if x not in set(last.get("items", {}).get(v, []))]
        gone = [f"{v}: {x}" for v, rows in (last.get("items") or {}).items() for x in rows if x not in set(items.get(v, []))]
        if not items and issue:
            requests.patch(issue["url"], json={"state": "closed", "body": body(items)}, headers=h, timeout=30).raise_for_status()
            print("needs you: nothing left, issue closed")
        elif items:
            if issue:
                requests.patch(issue["url"], json={"body": body(items)}, headers=h, timeout=30).raise_for_status()
            else:
                r = requests.post(f"{API}/issues", json={"title": TITLE, "body": body(items)}, headers=h, timeout=30)
                r.raise_for_status()
                issue = r.json()
            note = [f"Digest {util.today()}: {sum(len(v) for v in items.values())} items."]
            note += [f"- New: {x}" for x in new[:20]] + [f"- Cleared: {x}" for x in gone[:20]]
            requests.post(issue["comments_url"], json={"body": "\n".join(note)}, headers=h, timeout=30).raise_for_status()
            print(f"needs you: issue #{issue.get('number')} updated, {len(new)} new, {len(gone)} cleared")
        else:
            print("needs you: nothing to report, no issue")
    except requests.RequestException as exc:
        print(f"needs you: GitHub refused ({exc}); carried on")
        return 0
    util.write_json(LAST, {"hash": digest_hash, "items": items, "updated": util.now()})
    return 0


if __name__ == "__main__":
    main()
