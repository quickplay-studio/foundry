"""The seams between departments: a writer's file is read by the next job in the shape it expects.

Each chain runs the scripts in order on one venture folder, offline with the fake model, and checks that every
seam file the reader asked for was there when it asked (so the writer's path and the reader's path agree) and that
the reader did not stop for want of it. test_runs.py checks each script alone; this checks them together."""
import json
import re

import pytest
import requests

from foundry import jobkit, util
from tests.test_runs import fake_ask, load

SCRIPTS = {p.parent.name: p for p in util.DEPARTMENTS.glob("*/*/*/run.py")}


def setup(tmp_path, monkeypatch, kind="service", who="business owners"):
    monkeypatch.setattr(jobkit, "ask", fake_ask)
    monkeypatch.setattr(jobkit, "search", lambda q, n=5, topic="general": [{"title": "t", "url": "https://example.com", "content": "c"}])
    monkeypatch.setattr(jobkit, "fetch", lambda url, limit=12000: "page text")
    monkeypatch.setattr(jobkit, "secret", lambda name: "")
    monkeypatch.setattr(util, "ask_json", lambda prompt, skipped=None, prefer=None: (fake_ask(prompt), "fake"))

    def offline(*a, **kw):
        raise ConnectionError("offline test")
    for name in ("get", "post", "put", "patch", "delete", "head", "request"):
        monkeypatch.setattr(requests, name, offline)
    monkeypatch.setattr(requests.Session, "request", offline)
    idea = {"slug": "t", "title": "Test", "kind": kind, "problem": "p", "who": who, "gap": "g", "mvp": ["one"], "money": "m", "channels": ["web"], "budget_gbp": 50}
    ctx = jobkit.test_ctx(tmp_path / "t", idea, board={"jobs": [], "gates": {}, "verdict": "pending"})
    util.write_json(tmp_path / "t" / "audit.json", {"business_model": "b2b", "jobs": [], "dropped": []})
    reads = []
    real = jobkit.read

    def spy(c, rel, default=None):
        reads.append((rel, (c["folder"] / rel).exists()))
        return real(c, rel, default)
    monkeypatch.setattr(jobkit, "read", spy)
    return ctx, reads


def run(ctx, reads, job, seams=()):
    """Run one script; every seam it reads must exist, and it must not skip for want of one."""
    ctx["outputs"], reads[:] = [], []
    result = load(SCRIPTS[job]).main(ctx) or {}
    seen = {rel: ok for rel, ok in reads}
    for seam in seams:
        hits = [rel for rel in seen if re.fullmatch(seam.replace("*", "[^/]+"), rel)]
        assert hits, f"{job} never read {seam}; it read {sorted(seen)}"
        found = [h for h in hits if seen[h]]  # a glob read may ask for files no job wrote yet; an exact path must exist
        assert found and ("*" in seam or found == hits), f"{job} read {hits} before a writer made it; found {found}"
    assert not (result.get("skipped") and any(s.split("/")[-1].split("*")[0] in result["skipped"] for s in seams)), f"{job} skipped on a seam: {result['skipped']}"
    return result


@pytest.mark.parametrize("kind,who", [("service", "business owners"), ("app", "parents"), ("tiktok-shop", "shoppers")])
def test_validate_chain(tmp_path, monkeypatch, kind, who):
    ctx, reads = setup(tmp_path, monkeypatch, kind, who)
    for writer in ("regulatory-screen", "trend-monitoring", "audience-analysis", "vertical-analysis", "competitor-teardown"):
        run(ctx, reads, writer)
    run(ctx, reads, "pricing-research", ["validate/competitor-teardown.json"])
    run(ctx, reads, "tam-market-sizing", ["validate/pricing-research.json", "validate/vertical-analysis.json"])
    run(ctx, reads, "data-visualisation")
    run(ctx, reads, "research-reports", ["validate/*.json"])
    assert (ctx["folder"] / "validate" / "report.md").exists() and (ctx["folder"] / "validate" / "verdict.json").exists()
    run(ctx, reads, "adversarial-verification", ["validate/report.md"])
    run(ctx, reads, "news-and-mention-tracking", ["validate/competitor-teardown.json"])
    if kind == "tiktok-shop":  # commerce prices from the validate research once the landed cost is known
        util.write_json(ctx["folder"] / "commerce" / "data" / "costs.json", {"selling_price": 24.99, "unit_cost_gbp": 6.5, "qty": 100})
        r = run(ctx, reads, "landed-cost-modelling")
        assert not r.get("skipped"), r
        run(ctx, reads, "pricing-and-offers", ["commerce/landed-cost.json", "validate/pricing-research.json"])
    for name in ("competitor-teardown", "pricing-research", "vertical-analysis"):  # tam-market-sizing skips offline: no official count
        data = json.loads((ctx["folder"] / "validate" / f"{name}.json").read_text(encoding="utf-8"))
        assert isinstance(data, dict) and data, name


def test_market_map_feeds_account_monitoring(tmp_path, monkeypatch):
    """market-mapping's CSV (Companies House faked) is the target list account-monitoring reads through intelkit."""
    ctx, reads = setup(tmp_path, monkeypatch)
    monkeypatch.setattr(jobkit, "secret", lambda name: "fake-key" if name == "COMPANIES_HOUSE_API_KEY" else "")
    util.write_json(ctx["folder"] / "sell" / "icp.json", {"segments": [{"name": "Indie agencies", "sic_prefixes": ["7311"], "regions": ["London"], "exclusions": []}]})
    mod = load(SCRIPTS["market-mapping"])
    monkeypatch.setattr(mod, "ch_search", lambda key, params: {"items": [{"company_number": "12345678", "company_name": "Acme Studio Ltd", "company_type": "ltd",
                                                                           "company_status": "active", "sic_codes": ["73110"], "date_of_creation": "2019-01-01",
                                                                           "registered_office_address": {"postal_code": "EC1A 1AA", "locality": "London"}}]})
    ctx["outputs"], reads[:] = [], []
    r = mod.main(ctx) or {}
    assert not r.get("skipped"), r
    text = (ctx["folder"] / "sell" / "market-map.csv").read_text(encoding="utf-8")
    assert text.splitlines()[0].startswith("company_number,company,") and "Acme Studio Ltd" in text
    r = run(ctx, reads, "account-monitoring")
    assert "no target list" not in str(r.get("skipped", "")), r


def test_qa_result_feeds_handoff_and_status(tmp_path, monkeypatch):
    """qa-and-verification runs in Claude Code; its documented result.json shape is what the GitHub readers get."""
    ctx, reads = setup(tmp_path, monkeypatch)
    util.write_json(ctx["folder"] / "qa" / "result.json", {"verdict": "PASS", "sha": "abc1234", "date": "2026-11-01", "checks": [{"id": "home-200", "result": "pass"}]})
    r = run(ctx, reads, "handoff-docs", ["qa/result.json"])
    assert r.get("skipped") != "QA not passed"
    ctx["board"] = {"jobs": [{"id": "a", "stage": "build", "status": "done", "updated": "2026-11-01"}], "gates": {"build": "open"}, "verdict": "pending", "stage": "build"}
    run(ctx, reads, "status-updates", ["qa/result.json"])
    assert "QA: PASS on abc1234 (1 checks, 0 failed, 2026-11-01)." in (ctx["folder"] / "status" / "latest.md").read_text(encoding="utf-8")


def test_transcript_feeds_meeting_follow_ups(tmp_path, monkeypatch):
    ctx, reads = setup(tmp_path, monkeypatch)
    inbox = ctx["folder"] / "meetings" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "2026-11-01-acme-intro.txt").write_text("Charlie: Thanks for joining.\nDana (Acme): We need this by March. Can you send pricing?\nCharlie: I will send the proposal on Friday.\n", encoding="utf-8")
    run(ctx, reads, "transcript-processing")
    made = [p for p in (ctx["folder"] / "meetings").glob("*-*.json") if p.name != "index.json"]
    assert made, "transcript-processing writes meetings/<date>-<title>.json"
    rec = json.loads(made[0].read_text(encoding="utf-8"))
    assert isinstance(rec, dict) and rec, made[0].name
    r = run(ctx, reads, "meeting-follow-ups")  # reads the meeting records by glob, not through jobkit.read
    assert not r.get("skipped"), r
    assert list((ctx["folder"] / "meetings").glob("*-recap.md")), "meeting-follow-ups writes a recap next to each record"
