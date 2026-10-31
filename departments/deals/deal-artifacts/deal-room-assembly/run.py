"""Deal Room Assembly: GitHub implementation of departments/deals/deal-artifacts/deal-room-assembly/SKILL.md.

Builds one password-gated page per prospect from the latest sell/proposals/<deal_id>-v<n>.md (and .pdf): the body is
encrypted with openssl (AES-256-CBC, PBKDF2 200000 rounds) and a gate page decrypts it in the browser with WebCrypto.
Only ciphertext is written. The job cannot post the passphrase: it is a fresh random 16 characters per room (or the
ROOM_PASS secret when Charlie sets one of 16 or more) and is printed once to the job log, never to a file.
"""
import base64
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import dealkit as D  # noqa: E402
from foundry import jobkit as k  # noqa: E402

ALNUM = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
STYLE = "body{font-family:Georgia,serif;max-width:720px;margin:2em auto;padding:0 1em;line-height:1.5;color:#222}h1,h2{font-family:Arial,sans-serif}table{border-collapse:collapse}td{border:1px solid #bbb;padding:4px 8px}input,button{font-size:1em;padding:.4em}"
GATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>Deal room</title><style>__STYLE__</style></head>
<body><main><h1>Deal room</h1><form id="f"><label>Passphrase <input id="p" type="password" autocomplete="off"></label> <button>Open</button></form><p id="e" role="alert"></p></main>
<script>
const BODY="__BODY__", HAS_PDF=__HAS_PDF__, PING="__PING__", ROOM="__ROOM__";
let pass="";
async function dec(b64,pw){
 const raw=Uint8Array.from(atob(b64),c=>c.charCodeAt(0));
 if(String.fromCharCode(...raw.slice(0,8))!=="Salted__")throw new Error("bad");
 const base=await crypto.subtle.importKey("raw",new TextEncoder().encode(pw),"PBKDF2",false,["deriveBits"]);
 const bits=new Uint8Array(await crypto.subtle.deriveBits({name:"PBKDF2",salt:raw.slice(8,16),iterations:200000,hash:"SHA-256"},base,384));
 const key=await crypto.subtle.importKey("raw",bits.slice(0,32),"AES-CBC",false,["decrypt"]);
 return new Uint8Array(await crypto.subtle.decrypt({name:"AES-CBC",iv:bits.slice(32,48)},key,raw.slice(16)));
}
document.getElementById("f").onsubmit=async ev=>{
 ev.preventDefault();
 try{
  const pw=document.getElementById("p").value;
  const html=new TextDecoder().decode(await dec(BODY,pw));
  pass=pw;document.body.innerHTML=html;
  if(PING)fetch(PING+(PING.includes("?")?"&":"?")+"room="+ROOM,{mode:"no-cors"}).catch(()=>{});
 }catch(x){document.getElementById("e").textContent="Password not recognised";}
};
document.addEventListener("click",async ev=>{
 if(ev.target.id!=="pdf"||HAS_PDF===false)return;
 ev.preventDefault();
 const t=await (await fetch("proposal.pdf.enc")).text();
 const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([await dec(t.trim(),pass)],{type:"application/pdf"}));a.download="proposal.pdf";a.click();
});
</script></body></html>
"""


def encrypt(data, passphrase):
    r = subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-md", "sha256", "-salt", "-pass", "env:ROOM_PASS"],
                       input=data, capture_output=True, env=dict(os.environ, ROOM_PASS=passphrase), timeout=60)
    if r.returncode:
        raise RuntimeError("openssl failed")
    return base64.b64encode(r.stdout).decode()


def main(ctx):
    gate = D.gate(ctx)
    if gate:
        return gate
    if not shutil.which("openssl"):
        return {"skipped": "openssl not found on this runner"}
    rooms = k.read(ctx, "sell/rooms.json", []) or []
    live = {r.get("deal_id"): r for r in rooms if isinstance(r, dict) and r.get("status") not in ("superseded", "revoked")}
    latest = {}
    for p in D.files(ctx, "sell/proposals/*-v*.md"):
        m = re.match(r"(.+)-v(\d+)\.md$", p.name)
        if m and int(m.group(2)) >= latest.get(m.group(1), (0, None))[0]:
            latest[m.group(1)] = (int(m.group(2)), p)
    rows, ping, fixed = {r.get("id"): r for r in D.pipeline(ctx)}, k.secret("DEAL_ROOM_PING_URL"), k.secret("ROOM_PASS")
    built, lines, shown = 0, [], []
    for deal, (n, path) in sorted(latest.items()):
        if int((live.get(deal) or {}).get("proposal_version", 0)) >= n:
            continue
        company = (rows.get(deal) or {}).get("company") or "your team"
        body_md = D.front(path.read_text(encoding="utf-8"))[1]
        pdf = path.with_suffix(".pdf")
        demo, url = ctx["folder"] / "sell" / "demos" / deal / "index.html", k.secret("CALCOM_BOOKING_URL")
        page = [f"<h1>Welcome, {D.html.escape(company)}</h1>", D.md_html(body_md)]
        page += ['<p><a id="pdf" href="#">Download the proposal (PDF)</a></p>'] if pdf.exists() else []
        page += [f'<p><a href="../../demos/{deal}/index.html">See the prototype</a> (sample data)</p>'] if demo.exists() else []
        page += [f'<h2>Next step</h2><p>Book a call: <a href="{D.html.escape(url)}">{D.html.escape(url)}</a></p>'] if url else ["<h2>Next step</h2><p>Reply to the email to agree the next step.</p>"]
        token = "".join(secrets.choice(ALNUM) for _ in range(16))
        passphrase = fixed if len(fixed) >= 16 else "".join(secrets.choice(ALNUM) for _ in range(16))
        try:
            cipher = encrypt(f'<style>{STYLE}</style>{"".join(page)}'.encode(), passphrase)
            pdf_cipher = encrypt(pdf.read_bytes(), passphrase) if pdf.exists() else ""
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
            lines.append(f"Room for {company} not built: {exc}")
            continue
        html = GATE.replace("__STYLE__", STYLE).replace("__BODY__", cipher).replace("__HAS_PDF__", "true" if pdf_cipher else "false").replace("__PING__", ping.replace('"', "")).replace("__ROOM__", token)
        k.write(ctx, f"sell/rooms/{token}/index.html", html)
        if pdf_cipher:
            k.write(ctx, f"sell/rooms/{token}/proposal.pdf.enc", pdf_cipher)
        if live.get(deal):
            live[deal]["status"] = "superseded"
        rooms.append({"deal_id": deal, "token": token, "created": D.today(), "proposal_version": n, "tracking": bool(ping), "status": "built"})
        lines.append(f"Room built for {company}: sell/rooms/{token}/index.html. Publish it to the venture's Pages folder, then send the link and the passphrase by different channels." + ("" if ping else " Views are unknown: no DEAL_ROOM_PING_URL."))
        if not (fixed and len(fixed) >= 16):
            shown.append((deal, passphrase))
        built += 1
    if not built:
        return {"skipped": "no proposal without a current room" + ("; " + lines[0] if lines else "")}
    k.write(ctx, "sell/rooms.json", rooms)
    D.alert(ctx, "deal-room-assembly", lines)
    if not ctx["dry_run"]:
        for deal, pw in shown:  # the only place a passphrase appears: the job log, masked first
            print(f"::add-mask::{pw}", file=sys.stderr)
            print(f"room passphrase for {deal}: {pw}", file=sys.stderr)
    return {"summary": f"{built} deal rooms built (ciphertext only). " + ("Passphrases are in the job log only." if shown else "Passphrase is the ROOM_PASS secret."), "flag": "caution" if shown else "ok"}


if __name__ == "__main__":
    k.run(main)
