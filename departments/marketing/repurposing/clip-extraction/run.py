"""Clip Extraction: GitHub implementation of departments/marketing/repurposing/clip-extraction/SKILL.md.

Cuts one recording Charlie owns (launch/inputs/recordings) into short vertical clips: audio through ffmpeg, Groq
Whisper for word timings (GROQ_API_KEY) or a transcript file Charlie supplies, sentence windows scored by the free
model (or a speech rate heuristic), cut and captioned with ffmpeg. Never fetches anyone else's video. Without
ffmpeg the transcript, windows and index are written and the render is pending.
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from foundry import jobkit as k

FFMPEG, FFPROBE = shutil.which("ffmpeg"), shutil.which("ffprobe")
EXT = (".mp4", ".mov", ".wav")
CHUNK_S = 1500


def tidy(text):
    return re.sub(r"\s+", " ", re.sub(r"\s*[\u2013\u2014]\s*", ", ", re.sub(r"!+", ".", str(text)).replace(" - ", ", "))).strip()


def sh(args, cwd=None, timeout=900):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return r.returncode == 0, r.stdout
    except Exception:  # noqa: BLE001
        return False, ""


def duration(path):
    ok, out = sh([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], timeout=60) if FFPROBE else (False, "")
    try:
        return float(out.strip()) if ok else 0.0
    except ValueError:
        return 0.0


def transcribe(src, key, skipped):
    words, offset = [], 0.0
    with tempfile.TemporaryDirectory() as tmp:  # mono 16 kHz at 32 kbps keeps an hour under the free file cap
        ok, _ = sh([FFMPEG, "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "aac", "-b:a", "32k", "-f", "segment", "-segment_time", str(CHUNK_S), "-reset_timestamps", "1", str(Path(tmp) / "a%03d.m4a")])
        for f in sorted(Path(tmp).glob("a*.m4a")) if ok else []:
            try:
                r = k.requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers={"Authorization": f"Bearer {key}"}, files={"file": (f.name, f.read_bytes())},
                                    data={"model": "whisper-large-v3-turbo", "response_format": "verbose_json", "timestamp_granularities[]": "word"}, timeout=300)
                words += [{"word": w["word"], "start": w["start"] + offset, "end": w["end"] + offset} for w in r.json().get("words", [])] if r.ok else []
                skipped += [] if r.ok else [f"groq whisper: HTTP {r.status_code}"]
            except Exception as exc:  # noqa: BLE001
                skipped.append(f"groq whisper: {type(exc).__name__}")
            offset += duration(f) or CHUNK_S
    return words


def sentences(words):
    out, cur = [], []
    for w in words:
        if cur and (w["start"] - cur[-1]["end"] > 1.2):
            out.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.?!]$", str(w["word"]).strip()):
            out.append(cur)
            cur = []
    return out + ([cur] if cur else [])


def windows(sents, lo, hi):
    out, i = [], 0
    while i < len(sents):
        j = i
        while j < len(sents) and sents[j][-1]["end"] - sents[i][0]["start"] < lo:
            j += 1
        if j < len(sents) and sents[j][-1]["end"] - sents[i][0]["start"] <= hi:
            ws = [w for s in sents[i:j + 1] for w in s]
            out.append({"start": ws[0]["start"], "end": ws[-1]["end"], "words": ws, "text": " ".join(str(w["word"]).strip() for w in ws)})
        i += max(1, (j - i) // 2)
    step = max(1, len(out) // 120)
    return out[::step]


def heuristic(win, product_words):
    rate = len(win["words"]) / max(win["end"] - win["start"], 1)
    text = win["text"].lower()
    return 3 + 2 * bool(re.search(r"\d", text)) + 2 * any(p in text for p in product_words) + (1 if 2 <= rate <= 3.4 else 0), "heuristic: speech rate, a number, a product mention"


def srt(words, start, path):
    cues, t = [], lambda s: f"{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{int(s % 60):02d},{int(s % 1 * 1000):03d}"
    for i in range(0, len(words), 6):
        chunk = words[i:i + 6]
        cues.append(f"{len(cues) + 1}\n{t(max(chunk[0]['start'] - start, 0))} --> {t(max(chunk[-1]['end'] - start, 0.1))}\n{' '.join(str(w['word']).strip() for w in chunk)}\n")
    Path(path).write_text("\n".join(cues), encoding="utf-8")


def main(ctx):
    folder, idea, skipped = ctx["folder"], ctx["idea"], []
    rec_dir = folder / "launch/inputs/recordings"
    recs = [p for p in sorted(rec_dir.glob("*")) if p.suffix.lower() in EXT and not (folder / "launch/clips" / p.stem / "index.json").exists()] if rec_dir.is_dir() else []
    if not recs:
        return {"skipped": "no new recording in launch/inputs/recordings (only files Charlie owns go there)"}
    src, name = recs[0], recs[0].stem
    if ctx["dry_run"]:
        return {"summary": f"dry run: would cut clips from {src.name}"}
    req = k.read(ctx, "launch/inputs/clip-request.json", {}) or {}
    req = req if isinstance(req, dict) else {}
    count, lo, hi = int(req.get("count", 8) or 8), float(req.get("min_s", 20) or 20), float(req.get("max_s", 60) or 60)
    tpath = f"launch/clips/{name}.transcript.json"
    words = (k.read(ctx, tpath, {}) or {}).get("words", [])
    if not words:
        if not FFMPEG:
            return {"skipped": "no transcript and ffmpeg is not on this runner"}
        if not k.secret("GROQ_API_KEY"):
            return {"skipped": f"no transcript and GROQ_API_KEY missing: add {tpath} or the key"}
        words = transcribe(src, k.secret("GROQ_API_KEY"), skipped)
        if not words:
            return {"skipped": "transcription returned no words: " + "; ".join(skipped)[:140]}
        k.write(ctx, tpath, {"source": src.name, "words": words})
    wins = windows(sentences(words), lo, hi)
    if not wins:
        return {"skipped": f"no sentence window of {lo:g} to {hi:g} seconds in the transcript"}
    product = [w.lower() for w in re.findall(r"[A-Za-z]{4,}", f"{idea.get('title', '')} {' '.join(map(str, idea.get('mvp', [])))}")][:12]
    scores = {}
    for b in range(0, len(wins), 12):
        batch = wins[b:b + 12]
        answer = k.ask('Return JSON only: {"scores": [{"window": 0, "score": 0, "hook_text": "...", "reason": "..."}]}. Score 0 to 10 each window: it makes sense alone (starts on a clear claim, ends on a finished thought, no "as I said earlier"), has a number or specific example, mentions the product.\n\n'
                       + "\n".join(f"{i}: {w['text'][:350]}" for i, w in enumerate(batch)))
        for s in (answer.get("scores") if isinstance(answer, dict) and isinstance(answer.get("scores"), list) else []):
            if isinstance(s, dict) and isinstance(s.get("window"), int) and 0 <= s["window"] < len(batch) and isinstance(s.get("score"), (int, float)):
                scores[b + s["window"]] = (float(s["score"]), tidy(s.get("reason", "")), tidy(s.get("hook_text", "")))
    used_heuristic = len(scores) < len(wins)
    for i, w in enumerate(wins):
        sc, why = scores.get(i, heuristic(w, product))[:2]
        w["score"], w["reason"], w["hook"] = sc, why, (scores.get(i, ("", "", ""))[2] or " ".join(w["text"].split()[:14]))
    picked = []
    for w in sorted(wins, key=lambda w: -w["score"]):
        if len(picked) < count and all(w["end"] <= p["start"] or w["start"] >= p["end"] for p in picked):
            picked.append(w)
    picked.sort(key=lambda w: w["start"])
    d = folder / "launch/clips" / name
    d.mkdir(parents=True, exist_ok=True)
    can_burn = bool(FFMPEG) and "subtitles" in sh([FFMPEG, "-hide_banner", "-filters"], timeout=30)[1]
    rows, cut = [], 0
    for n, w in enumerate(picked, 1):
        cid = f"clip-{n:02d}"
        srt(w["words"], w["start"] - 0.2, d / f"{cid}.srt")
        ctx["outputs"].append(f"launch/clips/{name}/{cid}.srt")
        row = {"clip_id": cid, "source": src.name, "start": round(w["start"], 2), "end": round(w["end"], 2), "hook_text": w["hook"], "score": w["score"], "reason": w["reason"]}
        if FFMPEG:
            vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" + (f",subtitles={cid}.srt:original_size=1080x1920:force_style='Alignment=2,MarginV=250,FontSize=64,Outline=3'" if can_burn else "")
            ok, _ = sh([FFMPEG, "-y", "-ss", f"{max(w['start'] - 0.2, 0):.2f}", "-to", f"{w['end'] + 0.2:.2f}", "-i", str(src), "-vf", vf, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-c:a", "aac", "-movflags", "+faststart", f"{cid}.mp4"], cwd=str(d))
            dur = duration(d / f"{cid}.mp4") if ok else 0
            has_audio = ok and "audio" in sh([FFPROBE, "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(d / f"{cid}.mp4")], timeout=60)[1] if FFPROBE else False
            row["checked"] = bool(ok and lo - 1 <= dur <= hi + 1 and has_audio)
            cut += bool(ok)
            ctx["outputs"] += [f"launch/clips/{name}/{cid}.mp4"] * bool(ok)
        else:
            row["render"] = "pending: ffmpeg not found"
        rows.append(row)
    k.write(ctx, f"launch/clips/{name}/index.json", [{**r, "heuristic": used_heuristic} for r in rows])
    md = [f"# Clips from {src.name}", f"{len(rows)} clips. " + ("Some windows scored by a speech rate heuristic: no model answered for them. " if used_heuristic else "") + ("Captions burned in." if can_burn else "Captions are in the .srt files only."), "",
          "| Clip | Start | End | Score | Hook text |", "|---|---|---|---|---|"] + [f"| {r['clip_id']} | {r['start']} | {r['end']} | {r['score']} | {r['hook_text'].replace('|', '/')} |" for r in rows]
    k.write(ctx, f"launch/clips/{name}.md", "\n".join(md))
    return {"summary": f"{len(rows)} clips planned from {src.name}, {cut} cut." + ("" if FFMPEG else " Render pending: ffmpeg not found.") + (" Heuristic scores used." if used_heuristic else ""), "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
