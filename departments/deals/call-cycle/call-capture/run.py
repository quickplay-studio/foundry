"""Call Capture: GitHub implementation of departments/deals/call-cycle/call-capture/SKILL.md.

Files a transcript for each ended meeting with recorded consent: from Fireflies (FIREFLIES_API_KEY) or an uploaded
recording in sell/calls/<deal_id>/ (ffmpeg chunks, Groq Whisper with GROQ_API_KEY). Without a yes in sell/meetings.json
nothing is transcribed; typed notes.md from Charlie are filed instead. Uploaded audio is deleted after the transcript is written.
"""
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import dealkit as D  # noqa: E402
from foundry import jobkit as k  # noqa: E402

AUDIO = (".mp3", ".m4a", ".wav", ".mp4", ".webm", ".ogg", ".mov", ".aac", ".flac")
UTC = dt.timezone.utc
CHUNK = 600  # seconds per chunk: about 3.6 MB at 48 kbps, well under the 20 MB limit


def fireflies(entry, key):
    def gql(query, **variables):
        try:
            r = requests.post("https://api.fireflies.ai/graphql", json={"query": query, "variables": variables}, headers={"Authorization": f"Bearer {key}"}, timeout=60)
            return (r.json().get("data") or {}) if r.ok else {}
        except Exception:  # noqa: BLE001
            return {}
    start, email = D.parse_dt(entry.get("start")), str(entry.get("attendee_email", "")).lower()
    for t in D.lst(gql("query { transcripts(limit: 25) { id date participants } }").get("transcripts")):
        try:
            when = dt.datetime.fromtimestamp(float(t.get("date") or 0) / 1000, UTC)
        except (TypeError, ValueError):
            continue
        if start and abs((when - start).total_seconds()) <= 900 and email and email in str(t.get("participants", "")).lower():
            body = gql("query { transcript(id: " + json.dumps(str(t.get("id"))) + ") { sentences { speaker_name text start_time } } }").get("transcript") or {}
            return [(float(s.get("start_time") or 0), D.txt(s.get("speaker_name"), 60) or "Speaker", D.txt(s.get("text"), 1000)) for s in D.lst(body.get("sentences")) if isinstance(s, dict)]
    return []


def whisper(src, key):
    """(seconds, speaker, text) lines from an audio or video file, or [] when ffmpeg or Groq is unavailable."""
    if not shutil.which("ffmpeg") or not key:
        return []
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", "-b:a", "48k", "-f", "segment", "-segment_time", str(CHUNK), "-reset_timestamps", "1", f"{tmp}/chunk%03d.mp3"]
        if subprocess.run(cmd, capture_output=True, timeout=900).returncode != 0:
            return []
        for i, part in enumerate(sorted(Path(tmp).glob("chunk*.mp3"))):
            try:
                r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers={"Authorization": f"Bearer {key}"}, timeout=300,
                                  files={"file": (part.name, part.read_bytes())}, data={"model": "whisper-large-v3", "response_format": "verbose_json"})
                segs = r.json().get("segments", []) if r.ok else []
            except Exception:  # noqa: BLE001
                return []
            out += [(i * CHUNK + float(s.get("start", 0)), "Speaker", D.txt(s.get("text"), 1000)) for s in segs if isinstance(s, dict)]
    return out


def main(ctx):
    gate = D.gate(ctx)
    if gate:
        return gate
    meets = k.read(ctx, "sell/meetings.json", []) or []
    now, rows, filed, notes, lines = dt.datetime.now(UTC), D.pipeline(ctx), 0, [], []
    for m in meets:
        end = D.parse_dt(m.get("end"))
        if m.get("transcript") or m.get("status") in ("cancelled", "no_show") or not end or end > now:
            continue
        deal = str(m.get("deal_id"))
        folder = ctx["folder"] / "sell" / "calls" / deal
        typed = k.read(ctx, f"sell/calls/{deal}/notes.md", "") or ""
        consent = str(m.get("consent", "unknown")).lower()
        lines_out, head, audio, used = [], "", None, False
        if consent != "yes":
            if typed.strip():
                head = f"consent: {consent} (typed notes by Charlie, nothing recorded)"
                lines_out = [(None, "", typed.strip())]
            else:
                notes.append(f"{deal}: consent {consent}, no typed notes, nothing filed")
                continue
        else:
            head = f"consent: yes ({D.txt(m.get('consent_note'), 120) or 'recorded in sell/meetings.json'})"
            key = k.secret("FIREFLIES_API_KEY")
            lines_out = fireflies(m, key) if key else []
            audio = next((p for p in sorted(folder.glob("*")) if p.suffix.lower() in AUDIO), None) if folder.exists() else None
            if not lines_out and audio:
                lines_out = whisper(audio, k.secret("GROQ_API_KEY"))
                used = bool(lines_out)
            if not lines_out and typed.strip():
                lines_out = [(None, "", typed.strip())]
                head = "consent: yes (typed notes by Charlie; no recording or transcript found)"
            if not lines_out:
                notes.append(f"{deal}: no Fireflies transcript or readable recording" + ("" if key else " (no FIREFLIES_API_KEY)"))
                continue
        body = [(f"[{int(t) // 60:02d}:{int(t) % 60:02d}] {who}: {text}" if t is not None else text) for t, who, text in lines_out]
        words = sum(len(b.split()) for b in body)
        short = words < 200 and not lines_out[0][0] is None  # Charlie's typed notes are never "short"
        k.write(ctx, f"sell/calls/{deal}/transcript.md", "\n".join([head] + (["short: yes (under 200 words, do not debrief)"] if short else []) + [""] + body))
        m.update(status="held", transcript=f"sell/calls/{deal}/transcript.md")
        row = next((r for r in rows if r.get("id") == deal), None)
        if row and row.get("stage") == "meeting_booked":
            row.update(stage="discovery_done", updated=D.today())
        if short:
            lines.append(f"Transcript for {deal} is short ({words} words): it will not be debriefed")
        if used and not ctx["dry_run"]:
            audio.unlink()  # audio never stays on the runner or in git
        filed += 1
    if not filed:
        return {"skipped": "no ended meeting with a recording or notes to file" + (": " + "; ".join(notes[:3]) if notes else "")}
    k.write(ctx, "sell/meetings.json", meets)
    if rows:
        D.save_pipeline(ctx, rows)
    D.alert(ctx, "call-capture", lines)
    return {"summary": f"Filed {filed} transcripts." + (" " + "; ".join(notes[:2]) if notes else "")}


if __name__ == "__main__":
    k.run(main)
