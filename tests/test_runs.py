"""Every run.py runs offline, with the model, search and fetch replaced by fakes, writes something,
and names its department's stage. This is the contract between foundry.jobs and the job scripts."""
import importlib.util
import json

import pytest
import requests

from foundry import jobkit, util

SCRIPTS = sorted(util.DEPARTMENTS.glob("*/*/*/run.py"))


def load(path):
    spec = importlib.util.spec_from_file_location("job_" + path.parent.name.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fake_ask(prompt, prefer=None):
    """A plausible answer for any JSON request: every key the prompt hints at gets a stub value."""
    keys = set(json.loads(json.dumps([k.strip('"') for k in __import__("re").findall(r'"([a-z_]{3,30})":', prompt)])))
    out = {k: ("clear" if k == "flag" else "stub" if k not in ("items", "rows", "list", "results", "segments", "keep") else []) for k in keys}
    out.setdefault("summary", "stub")
    out.setdefault("flag", "clear")
    return out


@pytest.mark.parametrize("script", SCRIPTS, ids=[f"{p.parents[2].name}/{p.parent.name}" for p in SCRIPTS])
def test_run_py_runs_offline(script, tmp_path, monkeypatch):
    monkeypatch.setattr(jobkit, "ask", fake_ask)
    monkeypatch.setattr(jobkit, "search", lambda q, n=5, topic="general": [{"title": "t", "url": "https://example.com", "content": "c"}])
    monkeypatch.setattr(jobkit, "fetch", lambda url, limit=12000: "page text")
    monkeypatch.setattr(jobkit, "secret", lambda name: "")
    monkeypatch.setattr(util, "ask_json", lambda prompt, skipped=None, prefer=None: (fake_ask(prompt), "fake"))

    def offline(*a, **kw):  # no script may depend on the network: a public API that is down must be a logged skip
        raise ConnectionError("offline test")
    for name in ("get", "post", "put", "patch", "delete", "head", "request"):
        monkeypatch.setattr(requests, name, offline)
    monkeypatch.setattr(requests.Session, "request", offline)
    kind = "tiktok-shop" if script.parents[2].name == "commerce" else "service"
    idea = {"slug": "t", "title": "Test", "kind": kind, "problem": "p", "who": "business owners", "gap": "g", "mvp": ["one"],
            "money": "m", "channels": ["web"], "budget_gbp": 50}
    ctx = jobkit.test_ctx(tmp_path / "t", idea, board={"jobs": [], "gates": {}, "verdict": "pending"})
    util.write_json(tmp_path / "t" / "audit.json", {"business_model": "b2b", "jobs": [], "dropped": []})
    mod = load(script)
    result = mod.main(ctx) or {}
    assert isinstance(result, dict)
    assert ctx["outputs"] or result.get("skipped"), "a run.py writes something or says why not"
    for rel in ctx["outputs"]:
        assert (tmp_path / "t" / rel).exists(), rel
