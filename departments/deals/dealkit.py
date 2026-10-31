"""Shared helpers for the deals run.py scripts: the pipeline CSV, suppression, gates, drafts, alerts, Gmail read.

Stdlib plus requests. Nothing here sends, posts, books or pays: drafts and alerts are files in the venture
folder for Charlie. Scripts import this with a sys.path line, see any run.py in this department.
"""
import base64
import csv
import datetime as dt
import html
import io
import re

import requests

from foundry import jobkit as k
from foundry import util

COLS = "id,company,contact,email,role,source,stage,value_gbp,prob_override,expected_close,next_step,next_step_date,last_touch,created,updated,lost_reason,flag,notes".split(",")
STAGES = ["new", "qualified", "meeting_booked", "discovery_done", "proposal_sent", "negotiation", "verbal_yes", "won", "lost", "dormant"]
ACTIVE = STAGES[:7]
EMAIL = re.compile(r"[\w.+'-]+@[\w-]+(?:\.[\w-]+)+")
FREEMAIL = {"gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "hotmail.co.uk", "yahoo.com", "yahoo.co.uk", "icloud.com", "live.co.uk", "live.com", "aol.com", "proton.me", "protonmail.com", "me.com"}
SENSITIVE = re.compile(r"complain|legal|solicitor|lawyer|gdpr|data protection|subject access|\bsar\b|\bico\b|\bsue\b|lawsuit|security|breach", re.I)
OBJECTION_TYPES = ("price", "timing", "authority", "need", "competitor", "trust")
PERMISSION = re.compile(r"say i sent you|mention my name|feel free to (use|mention)|i.?ve (cc|copied)|cc.?d|copied in|looping", re.I)
try:
    from zoneinfo import ZoneInfo
    UK = ZoneInfo("Europe/London")
except Exception:  # noqa: BLE001
    UK = dt.timezone.utc


def today():
    return util.today()


def b2b(ctx):
    """True when the idea, the audit or the board names a business buyer."""
    audit = k.read(ctx, "audit.json", {}) or {}
    vals = [ctx["idea"].get("business_model"), audit.get("business_model"), (ctx.get("board") or {}).get("business_model")]
    return any(str(v or "").lower() in ("b2b", "both") for v in vals)


def gate(ctx):
    return None if b2b(ctx) else {"skipped": "no business buyer"}


def txt(x, n=400):
    return re.sub(r"\s+", " ", x).strip()[:n] if isinstance(x, str) else (str(x)[:n] if isinstance(x, (int, float)) and not isinstance(x, bool) else "")


def lst(x):
    return x if isinstance(x, list) else []


def section(ctx, name):
    m = re.search(rf"^## +{name}\s*\n(.*?)(?=^## |\Z)", ctx.get("brain", ""), re.M | re.S | re.I)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def proof(ctx):
    items = ctx["idea"].get("proof")
    if isinstance(items, list) and items:
        return "; ".join(txt(i.get("source", "") + " " + i.get("url", "") if isinstance(i, dict) else i, 160) for i in items[:3]).strip()
    return section(ctx, "Proof").replace("- ", "").strip()


def money(ctx):
    return txt(ctx["idea"].get("money", ""), 300) or section(ctx, "Money")


def sender(ctx):
    return txt(ctx["idea"].get("sender", ""), 60) or "Charlie"


def email_of(text):
    m = EMAIL.search(str(text or ""))
    return m.group(0).lower() if m else ""


def domain(email):
    return email.split("@")[-1].lower() if "@" in email else ""


def first_name(header):
    name = re.sub(r"<.*?>|[\"']", "", str(header or "")).strip()
    word = name.split()[0] if name and "@" not in name else re.split(r"[._-]", email_of(header).split("@")[0])[0]
    return (word.title() if word.islower() else word) or "there"


def parse_dt(s):
    try:
        d = dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except (ValueError, TypeError):
        return None


def parse_date(s):
    s = str(s or "").strip()
    for f in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %b %Y", "%d %B %Y", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(s, f).date()
        except ValueError:
            continue
    d = parse_dt(s)
    return d.date() if d else None


def days_since(s):
    d = parse_date(s)
    return (dt.date.today() - d).days if d else None


def nums(text):
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", str(text))}


def read_csv(ctx, rel):
    text = k.read(ctx, rel, "") or ""
    rd = csv.DictReader(io.StringIO(text))
    rows = [{c: (v if isinstance(v, str) else "") for c, v in r.items() if c} for r in rd]
    return rows, list(rd.fieldnames or [])


def write_csv(ctx, rel, rows, cols):
    extra = sorted({c for r in rows for c in r if c not in cols})
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(cols) + extra, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    k.write(ctx, rel, buf.getvalue())


def pipeline(ctx):
    return read_csv(ctx, "sell/pipeline.csv")[0]


def save_pipeline(ctx, rows):
    write_csv(ctx, "sell/pipeline.csv", rows, COLS)


def new_row(rows, **kw):
    ymd = today().replace("-", "")
    n = 1 + sum(1 for r in rows if r.get("id", "").startswith(f"d-{ymd}-"))
    row = {c: "" for c in COLS}
    row.update({"id": f"d-{ymd}-{n}", "created": today(), "updated": today()}, **kw)
    return row


def find_row(rows, email="", company="", contact=""):
    email = email.lower()
    for r in rows:
        if email and r.get("email", "").lower() == email:
            return r
    dom = domain(email)
    for r in rows:
        if dom and dom not in FREEMAIL and domain(r.get("email", "")) == dom and contact and r.get("contact", "").lower() == contact.lower():
            return r
    return None


def add_note(row, note):
    row["notes"] = (row.get("notes", "") + "; " if row.get("notes") else "") + note


def suppressed(ctx):
    out = set()
    for rel in ("sell/suppress.csv", "sell/suppression.csv"):
        for r in read_csv(ctx, rel)[0]:
            e = (r.get("email") or next(iter(r.values()), "") or "").strip().lower()
            if e:
                out.add(e)
    return out


def alert(ctx, job, lines):
    """Issue text for Charlie goes to sell/alerts.md (a dated block per run); nothing is posted anywhere."""
    if lines:
        old = k.read(ctx, "sell/alerts.md", "") or "# Alerts for Charlie\n"
        k.write(ctx, "sell/alerts.md", old.rstrip("\n") + f"\n\n## {today()} {job}\n" + "\n".join(f"- {x}" for x in lines))


def draft(ctx, name, head, body):
    """A message for Charlie to read, edit and send. Never sent by the job."""
    lines = [f"{key}: {val}" for key, val in head.items()] + ["status: draft, not sent", "", body]
    k.write(ctx, f"sell/drafts/{name}.md", "\n".join(lines))
    return f"sell/drafts/{name}.md"


def front(text):
    """(front matter dict, body) for a markdown file that starts with a --- block."""
    m = re.match(r"---\s*\n(.*?)\n---\s*\n?(.*)", text or "", re.S)
    if not m:
        return {}, text or ""
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            meta[key.strip()] = val.strip()
    return meta, m.group(2)


def approved_price(ctx, deal_id):
    meta, _ = front(k.read(ctx, f"sell/pricing/{deal_id}.md", "") or "")
    try:
        price = float(re.sub(r"[^\d.]", "", meta.get("price_gbp", "")))
    except ValueError:
        return None
    return price if meta.get("approved", "").lower() == "true" and price > 0 else None


def files(ctx, rel_glob):
    return sorted(ctx["folder"].glob(rel_glob))


def gmail_auth():
    """(auth headers, reason). Needs GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET and GMAIL_REFRESH_TOKEN."""
    ids = [k.secret(n) for n in ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN")]
    if not all(ids):
        return None, "no Gmail key"
    try:
        r = requests.post("https://oauth2.googleapis.com/token", timeout=30, data={
            "client_id": ids[0], "client_secret": ids[1], "refresh_token": ids[2], "grant_type": "refresh_token"})
        if not r.ok:
            return None, "gmail token expired"
        return {"Authorization": "Bearer " + r.json()["access_token"]}, ""
    except Exception as exc:  # noqa: BLE001
        return None, f"gmail error {type(exc).__name__}"


def _body(p):
    if p.get("mimeType") == "text/plain" and p.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(p["body"]["data"] + "==").decode("utf-8", "replace")
    for q in p.get("parts", []) or []:
        t = _body(q)
        if t:
            return t
    return ""


def gmail(query, limit=40):
    """(messages, reason): read-only fetch of {id, thread_id, from, subject, received, body, headers}; None when no key."""
    auth, why = gmail_auth()
    if not auth:
        return None, why
    base = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
    try:
        refs = requests.get(base, params={"q": query, "maxResults": limit}, headers=auth, timeout=30).json().get("messages", [])
        out = []
        for ref in refs:
            m = requests.get(f"{base}/{ref['id']}", params={"format": "full"}, headers=auth, timeout=30).json()
            hd = {h["name"].lower(): h["value"] for h in m.get("payload", {}).get("headers", [])}
            when = dt.datetime.fromtimestamp(int(m.get("internalDate", 0)) / 1000, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            out.append({"id": m["id"], "thread_id": m.get("threadId", ""), "from": hd.get("from", ""), "subject": hd.get("subject", ""),
                        "received": when, "body": _body(m.get("payload", {})), "headers": hd})
        return out, ""
    except Exception as exc:  # noqa: BLE001
        return None, f"gmail error {type(exc).__name__}"


def md_html(text):
    """Small markdown to HTML: headings, bullet lists, pipe tables, paragraphs, bold."""
    out, buf = [], []

    def inline(s):
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html.escape(s))

    def flush():
        if not buf:
            return
        if buf[0][0] == "li":
            out.append("<ul>" + "".join(f"<li>{inline(b[1])}</li>" for b in buf) + "</ul>")
        elif buf[0][0] == "tr":
            rows = [b[1] for b in buf if not re.fullmatch(r"[\s|:-]+", b[1])]
            out.append("<table>" + "".join("<tr>" + "".join(f"<td>{inline(c.strip())}</td>" for c in r.strip("|").split("|")) + "</tr>" for r in rows) + "</table>")
        else:
            out.append("<p>" + inline(" ".join(b[1] for b in buf)) + "</p>")
        buf.clear()

    for line in text.splitlines():
        s = line.strip()
        h = re.match(r"(#{1,4}) +(.*)", s)
        kind = "h" if h else "li" if re.match(r"[-*] +", s) else "tr" if s.startswith("|") else "p" if s else None
        if buf and kind != buf[0][0]:
            flush()
        if kind == "h":
            out.append(f"<h{len(h.group(1))}>{inline(h.group(2))}</h{len(h.group(1))}>")
        elif kind:
            buf.append((kind, re.sub(r"^[-*] +", "", s) if kind == "li" else s))
    flush()
    return "\n".join(out)


def starter_library(ctx):
    idea, prf, mny = ctx["idea"], proof(ctx), money(ctx)
    facts = {"price": f"Fair question on cost. {mny}".strip(), "timing": "Understood on timing. " + (f"The first step is small: {idea['mvp'][0]}." if idea.get("mvp") else "Starting is quick."),
             "authority": "Thank you. I can send a short summary to pass on: " + txt(idea.get("problem", ""), 120), "need": "Fair challenge. The gap we cover: " + txt(idea.get("gap", ""), 160),
             "competitor": "Good to know what you use. Where we differ: " + txt(idea.get("gap", ""), 160), "trust": "Reasonable to ask. " + (f"Evidence so far: {prf}" if prf else "I can show it working first.")}
    return [{"id": f"starter-{t}", "type": t, "label": t.title() + " (starter)", "phrasings": [], "rebuttal": facts[t], "uses": 0, "advanced": 0, "win_rate": None, "status": "untested"} for t in OBJECTION_TYPES]
