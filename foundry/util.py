"""Shared helpers: dates, slugs, JSON, HTTP and the free model chain."""
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
TREE = ROOT / "map" / "tree.json"
DATA = ROOT / "data"  # private checkout of quickplay-studio/foundry-ventures
VENTURES = DATA / "ventures"
OFFICE = DATA / "office"
DEPARTMENTS = ROOT / "departments"


def today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(text):
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return text[:60] or "venture"


def read_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_tree():
    return read_json(TREE)


def all_jobs(tree=None):
    """Flat list of jobs with department and function attached."""
    tree = tree or load_tree()
    out = []
    for dept in tree["departments"]:
        for fn in dept["functions"]:
            for job in fn["jobs"]:
                item = dict(job)
                item["department"] = dept["id"]
                item["function"] = fn["id"]
                out.append(item)
    return out


def http_post_json(url, payload, headers=None, timeout=60):
    r = requests.post(url, json=payload, headers=headers or {}, timeout=timeout)
    if r.status_code >= 400:
        raise RuntimeError(f"{url.split('?')[0]} returned HTTP {r.status_code}")
    return r.json()


def _gemini(prompt, model):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY missing")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}}
    data = http_post_json(url, body)
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _groq(prompt, model):
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY missing")
    body = {"model": model, "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": prompt}]}
    data = http_post_json("https://api.groq.com/openai/v1/chat/completions", body,
                          {"Authorization": f"Bearer {key}"})
    return data["choices"][0]["message"]["content"]


def _freellm(prompt, model="auto"):
    """The FreeLLMAPI router started on the runner by foundry.freellm (OpenAI-compatible, free tiers only)."""
    key, base = os.environ.get("FREELLM_KEY", "").strip(), os.environ.get("FREELLM_BASE", "").strip().rstrip("/")
    if not (key and base):
        raise RuntimeError("FREELLM router not running")
    body = {"model": model, "temperature": 0.2, "max_tokens": 4000,
            "messages": [{"role": "system", "content": "Answer with one JSON object and nothing else."},
                         {"role": "user", "content": prompt}]}
    data = http_post_json(base + "/chat/completions", body, {"Authorization": f"Bearer {key}"}, timeout=180)
    return data["choices"][0]["message"]["content"]


MODEL_CHAIN = [
    ("freellm/auto", lambda p: _freellm(p)),
    ("gemini/gemini-2.5-flash", lambda p: _gemini(p, "gemini-2.5-flash")),
    ("gemini/gemini-2.5-flash-lite", lambda p: _gemini(p, "gemini-2.5-flash-lite")),
    ("groq/llama-3.3-70b-versatile", lambda p: _groq(p, "llama-3.3-70b-versatile")),
]


def search(query, n=5, topic="general"):
    """Web search through the router (POST FREELLM_BASE/search) while it is up; [] otherwise or on any failure."""
    key, base = os.environ.get("FREELLM_KEY", "").strip(), os.environ.get("FREELLM_BASE", "").strip().rstrip("/")
    if not (key and base):
        return []
    try:
        data = http_post_json(base + "/search", {"query": query, "max_results": n, "topic": topic},
                              {"Authorization": f"Bearer {key}"}, timeout=40)
        rows = data.get("results", []) if isinstance(data, dict) else data
        return [{"title": r.get("title", ""), "url": r.get("url", ""), "content": str(r.get("content", ""))[:1500]} for r in rows][:n]
    except Exception:  # noqa: BLE001
        return []


def ask_json(prompt, skipped=None, prefer=None):
    """Try each free model in turn; return (parsed JSON, model name) or (None, None).

    prefer="groq" or "gemini" moves that family to the front, for a second opinion
    from a different model family (adversarial-verification)."""
    chain = sorted(MODEL_CHAIN, key=lambda m: 0 if prefer and m[0].startswith(prefer) else 1) if prefer else MODEL_CHAIN
    for name, call in chain:
        try:
            text = call(prompt)
            start, end = text.find("{"), text.rfind("}")
            return json.loads(text[start:end + 1]), name
        except Exception as exc:  # noqa: BLE001
            if skipped is not None:
                skipped.append({"model": name, "reason": f"{type(exc).__name__}: {exc}"[:160]})
            time.sleep(1)
    return None, None
