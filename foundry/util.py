"""Shared helpers: dates, slugs, JSON, HTTP and the free model chain."""
import json
import os
import re
import sys
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


LAST_VIA = {"model": ""}  # which upstream model answered the last router call (X-Routed-Via), for the board log
_MODELS = {}  # the router's model order for this process, resolved once


def router_models(key, base):
    """The upstream models to ask, best first: config.json freellm.prefer matched against what the router lists as available,
    never the guard, safety or tiny ones, then auto as the last resort. The router's own auto routing has landed on a
    safety classifier ("Safety: Safe") and on 2B models, so a named order is more reliable than auto."""
    if "order" in _MODELS:
        return _MODELS["order"]
    cfg = read_json(ROOT / "config.json", {}).get("freellm", {}) if (ROOT / "config.json").exists() else {}
    prefer, never = [str(p).lower() for p in cfg.get("prefer", [])], [str(p).lower() for p in cfg.get("never", [])]
    order = []
    try:
        r = requests.get(base + "/models?available=true", headers={"Authorization": f"Bearer {key}"}, timeout=30)
        ids = [str(m.get("id")) for m in (r.json().get("data") or []) if isinstance(m, dict) and m.get("id") and m.get("available") is not False] if r.ok else []
        ids = [i for i in ids if i not in ("auto", "fusion") and not i.startswith("auto:") and not any(w in i.lower() for w in never)]
        for p in prefer:
            order += [i for i in ids if p in i.lower() and i not in order]
    except Exception:  # noqa: BLE001
        order = []
    _MODELS["order"] = (order[:6] or []) + ["auto"]
    return _MODELS["order"]


COOL_S = 32  # seconds before the same upstream model is asked again: OVHcloud allows two calls a minute per model


def _freellm(prompt, model=None, attempts=9):
    """The FreeLLMAPI router started on the runner by foundry.freellm (OpenAI-compatible, free tiers only).
    Each call goes to the preferred model that has rested longest (router_models order breaks ties), waiting out its
    cooldown first. A 429 rests that model for a minute; a 5xx, timeout or empty answer counts a fault against it, three
    faults and this process stops asking it."""
    key, base = os.environ.get("FREELLM_KEY", "").strip(), os.environ.get("FREELLM_BASE", "").strip().rstrip("/")
    if not (key and base):
        raise RuntimeError("FREELLM router not running")
    order = [model] if model else router_models(key, base)
    last_call, bad, last = _MODELS.setdefault("last", {}), _MODELS.setdefault("bad", {}), None
    for n in range(attempts):
        models = [m for m in order if bad.get(m, 0) < 3] or ["auto"]
        m = min(models, key=lambda x: (last_call.get(x, 0), models.index(x)))
        wait = last_call.get(m, 0) + COOL_S - time.time()
        if wait > 0:
            time.sleep(min(wait, 90))
        last_call[m] = time.time()
        body = {"model": m, "temperature": 0.2, "max_tokens": 6000,
                "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]}
        try:
            r = requests.post(base + "/chat/completions", json=body, headers={"Authorization": f"Bearer {key}"}, timeout=150)
            if r.status_code == 429:
                raise _RateLimited(f"router returned HTTP 429 for {m}")
            if r.status_code in (500, 502, 503, 504):
                raise RuntimeError(f"router returned HTTP {r.status_code} for {m}")
            if r.status_code >= 400:
                raise RuntimeError(f"router returned HTTP {r.status_code} for {m}: {r.text[:100]}")
            data = r.json()
            LAST_VIA["model"] = (requests.utils.unquote(r.headers.get("X-Routed-Via", "")) or m)[:60]
            choice = data["choices"][0]
            text = choice["message"]["content"] or ""
            if not text.strip():
                raise RuntimeError(f"router answer empty from {m}" + (" (finish_reason length)" if choice.get("finish_reason") == "length" else ""))
            return text
        except _RateLimited as exc:
            last = exc
            last_call[m] = time.time() + 60 - COOL_S  # rest it for a minute
            print(f"freellm: {m} rate limited, resting it", file=sys.stderr, flush=True)
        except (requests.RequestException, RuntimeError, KeyError, ValueError) as exc:
            last = exc
            bad[m] = bad.get(m, 0) + 1
            print(f"freellm: {m} failed: {type(exc).__name__}: {str(exc)[:100]}", file=sys.stderr, flush=True)
            time.sleep(2)
    raise RuntimeError(str(last)[:160])


class _RateLimited(RuntimeError):
    pass


SYSTEM = ("Answer with one JSON object and nothing else: no prose, no code fence. The JSON shape in the request is a template: "
          "put real content in every field and never copy its placeholder text, angle brackets or option lists.")
PLACEHOLDER = re.compile(r"^\s*<[^<>]{1,80}>\s*$")


def scrub(obj):
    """Blank the placeholders a weak model echoes back from a JSON template ("<two sentences>"), recursively."""
    if isinstance(obj, dict):
        return {k: scrub(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub(v) for v in obj]
    if isinstance(obj, str) and PLACEHOLDER.match(obj):
        return ""
    return obj


MODEL_CHAIN = [
    ("freellm/auto", lambda p: _freellm(p)),
    ("gemini/gemini-2.5-flash", lambda p: _gemini(p, "gemini-2.5-flash")),
    ("gemini/gemini-2.5-flash-lite", lambda p: _gemini(p, "gemini-2.5-flash-lite")),
    ("groq/llama-3.3-70b-versatile", lambda p: _groq(p, "llama-3.3-70b-versatile")),
]


def search(query, n=5, topic="general"):
    """Web search through the router (POST FREELLM_BASE/search) while it is up; [] otherwise or on any failure."""
    if os.environ.get("FOUNDRY_FAKE_MODEL"):
        return [{"title": f"stub result for {query[:40]}", "url": "https://example.com/stub", "content": "stub page content"}][:n]
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


_DOWN = {}  # engines that refused this process, so later calls skip them


def keyless_search(query, n=5):
    """Search with no key at all: DuckDuckGo's HTML page, then Bing's, then Hacker News (Algolia) as the last resort. [] on failure."""
    if os.environ.get("FOUNDRY_FAKE_MODEL"):
        return []
    rows = []
    try:
        r = None if _DOWN.get("ddg") else requests.post("https://html.duckduckgo.com/html/", data={"q": query}, timeout=25,
                                                         headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Foundry research bot"})
        if r is not None and r.status_code != 200:  # 202 is DuckDuckGo's bot challenge (GitHub runners get it every time): stop asking
            _DOWN["ddg"] = True
        if r is not None and r.ok:
            links = re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r.text, flags=re.S)
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', r.text, flags=re.S)
            for i, (href, title) in enumerate(links[:n]):
                m = re.search(r"uddg=([^&]+)", href)
                url = requests.utils.unquote(m.group(1)) if m else href
                clean = lambda t: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t)).strip()  # noqa: E731
                rows.append({"title": clean(title), "url": url, "content": clean(snippets[i]) if i < len(snippets) else "", "source": "duckduckgo"})
    except Exception:  # noqa: BLE001
        rows = []
    if rows:
        return rows[:n]
    rows = bing_search(query, n)
    if rows:
        return rows
    try:
        short = " ".join(re.sub(r"\b(OR|AND|tool|app|service|alternatives?|best|uk)\b", " ", query, flags=re.I).split()[:10])
        r = requests.get("https://hn.algolia.com/api/v1/search", params={"query": short or query, "hitsPerPage": n}, timeout=20)
        hits = r.json().get("hits", []) if r.ok else []
        return [{"title": h.get("title") or h.get("story_title") or "", "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                 "content": re.sub(r"<[^>]+>", " ", str(h.get("story_text") or h.get("comment_text") or ""))[:1500], "source": "hackernews"} for h in hits][:n]
    except Exception:  # noqa: BLE001
        return []


BROWSER_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def strip_tags(text):
    return re.sub(r"\s+([.,;:!?)])", r"\1", re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(text)))).strip()


def bing_search(query, n=5):
    """Bing's plain HTML results page, which answers GitHub runners (DuckDuckGo, Brave and Mojeek do not). [] on failure."""
    if _DOWN.get("bing"):
        return []
    try:
        r = requests.get("https://www.bing.com/search", params={"q": query, "setlang": "en-GB", "cc": "GB"}, timeout=25, headers={"User-Agent": BROWSER_UA, "Accept-Language": "en-GB,en;q=0.8"})
    except Exception:  # noqa: BLE001
        return []
    if os.environ.get("FOUNDRY_PROBE_DEBUG"):
        i = r.text.find('class="b_algo"')
        print(f"bing: HTTP {r.status_code}, {len(r.text)} bytes, b_algo at {i}, final url {r.url}\n{r.text[i:i + 700] if i >= 0 else r.text[:700]}", file=sys.stderr)
    if r.status_code != 200:
        _DOWN["bing"] = True
        return []
    rows = []
    for block in re.findall(r'<li class="b_algo"(.*?)</li>', r.text, flags=re.S)[: n * 2]:
        m = re.search(r'<h2[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, flags=re.S)
        if not m or not m.group(1).startswith("http") or "bing.com" in m.group(1).split("/")[2]:
            continue
        snippet = re.search(r"<p[^>]*>(.*?)</p>", block, flags=re.S)
        rows.append({"title": strip_tags(m.group(2))[:200], "url": m.group(1), "content": strip_tags(snippet.group(1))[:1500] if snippet else "", "source": "bing"})
        if len(rows) >= n:
            break
    return rows


def fake_answer(prompt):
    """FOUNDRY_FAKE_MODEL=1: a stub answer shaped by the keys the prompt asks for, for local end-to-end runs."""
    keys = sorted(set(re.findall(r'"([a-z_]{3,30})":', prompt)))
    lists = ("items", "rows", "list", "results", "segments", "keep", "areas", "facts", "hooks", "claims", "sources", "steps", "products", "questions", "objections", "drop")
    out = {k: ([] if k in lists else "clear" if k == "flag" else "stub") for k in keys}
    out.setdefault("summary", "stub answer from the fake model")
    out.setdefault("flag", "clear")
    return out


def ask_json(prompt, skipped=None, prefer=None):
    """Try each free model in turn; return (parsed JSON, model name) or (None, None).

    prefer="groq" or "gemini" moves that family to the front, for a second opinion
    from a different model family (adversarial-verification)."""
    if os.environ.get("FOUNDRY_FAKE_MODEL"):
        if prompt.startswith("You are the audit engine"):
            return None, None  # the heuristic audit keeps every staged job, which is what a dry lifecycle wants
        return fake_answer(prompt), "fake"
    chain = sorted(MODEL_CHAIN, key=lambda m: 0 if prefer and m[0].startswith(prefer) else 1) if prefer else MODEL_CHAIN
    for name, call in chain:
        for n in range(2):  # a second go when the answer was not JSON: the next upstream usually is
            try:
                text = call(prompt if n == 0 else prompt + "\n\nReturn the JSON object only, complete and valid.")
                start, end = text.find("{"), text.rfind("}")
                if start < 0 or end < 0:
                    raise ValueError("no JSON object in the answer: " + text.strip()[:80])
                parsed = scrub(json.loads(text[start:end + 1]))
                via = LAST_VIA["model"] if name.startswith("freellm") else ""
                return parsed, (name + "/" + via if via else name)
            except Exception as exc:  # noqa: BLE001
                if skipped is not None:
                    skipped.append({"model": name, "reason": f"{type(exc).__name__}: {exc}"[:160]})
                if not isinstance(exc, ValueError):  # json.JSONDecodeError is a ValueError
                    break  # the model did not answer at all: move down the chain, do not ask it twice
                time.sleep(1)
    return None, None
