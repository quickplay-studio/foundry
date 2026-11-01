import json
import re
import subprocess
from pathlib import Path

from foundry import audit, launch, scaffold, util

ROOT = util.ROOT
DASH = re.compile("[" + chr(0x2013) + chr(0x2014) + "]")


def text_files():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    names = out.stdout.split() if out.returncode == 0 else [str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file()]
    return [ROOT / n for n in names if n.endswith((".md", ".py", ".json", ".yml", ".html", ".txt"))]


def test_no_dashes_anywhere():
    bad = [str(p) for p in text_files() if DASH.search(p.read_text(encoding="utf-8", errors="ignore"))]
    assert not bad, bad


def test_tree_is_consistent():
    tree = util.load_tree()
    jobs = util.all_jobs(tree)
    ids = [j["id"] for j in jobs]
    assert len(ids) == len(set(ids)), "duplicate job id"
    assert len(ids) >= 151
    assert {d["id"] for d in tree["departments"]} == {"sales", "deals", "marketing", "operations", "intelligence", "customer", "back-office", "legal", "commerce"}
    for j in jobs:
        assert j["autonomy"] in ("solo", "assisted", "human"), j["id"]
        assert j.get("stage") in (None, *audit.STAGE_ORDER), j["id"]
        for b in j["builds_on"]:
            assert b in ids, f"{j['id']} builds on unknown {b}"
    legal = [j for j in jobs if j["department"] == "legal"]
    assert all(j["autonomy"] != "solo" or j["id"] in ("trademark-and-name-check", "licence-audit", "platform-and-ad-compliance") for j in legal)


def test_scaffold_matches_tree():
    created, kept = scaffold.main(check=True)
    assert len(created) + len(kept) == len(util.all_jobs())
    for rel in created + kept:
        assert (ROOT / rel).exists() or created, rel


def test_heuristic_audit_and_order():
    idea = json.loads((ROOT / "tests" / "fixtures" / "sample-idea.json").read_text())
    result = audit.heuristic(idea, util.all_jobs())
    assert result["model"] == "b2b"
    assert not any(k["id"] == "order-routing" for k in result["keep"])  # an app keeps no commerce jobs
    shop = audit.heuristic(dict(idea, kind="tiktok-shop"), util.all_jobs())
    assert any(k["id"] == "order-routing" for k in shop["keep"])
    ordered = audit.topo_order([j for j in util.all_jobs() if j["id"] in {k["id"] for k in result["keep"]}])
    seen = set()
    for j in ordered:
        for b in j["builds_on"]:
            if b in {x["id"] for x in ordered}:
                assert b in seen, f"{j['id']} before its dependency {b}"
        seen.add(j["id"])
    stages = [j["stage"] for j in ordered]
    assert stages == sorted(stages, key=audit.STAGE_ORDER.index)


def test_dry_run_writes_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(util, "ask_json", lambda prompt, skipped=None: (None, None))
    dst = tmp_path / "sample"
    dst.mkdir()
    (dst / "idea.json").write_text((ROOT / "tests" / "fixtures" / "sample-idea.json").read_text())
    out = launch.run_one("sample", dry_run=True, root=tmp_path)
    assert set(dst.iterdir()) == {dst / "idea.json"}
    assert out["board.json"]["jobs"] and out["board.json"]["model_used"] == "heuristic"
    assert "## Validate" in out["plan.md"]


def test_launch_writes_all_files(monkeypatch, tmp_path):
    monkeypatch.setattr(util, "ask_json", lambda prompt, skipped=None: (None, None))
    dst = tmp_path / "sample"
    dst.mkdir()
    (dst / "idea.json").write_text((ROOT / "tests" / "fixtures" / "sample-idea.json").read_text())
    launch.run_one("sample", root=tmp_path)
    assert {p.name for p in dst.iterdir()} == {"idea.json", "brain.md", "plan.md", "board.json", "budget.json", "audit.json", "README.md"}
    assert json.loads((dst / "budget.json").read_text())["ad_budget"] == 100


def test_jobs_gates_and_skip(monkeypatch, tmp_path):
    from foundry import jobs
    monkeypatch.setattr(util, "ask_json", lambda prompt, skipped=None: (None, None))
    dst = tmp_path / "sample"
    dst.mkdir()
    (dst / "idea.json").write_text((ROOT / "tests" / "fixtures" / "sample-idea.json").read_text())
    launch.run_one("sample", root=tmp_path)
    board = json.loads((dst / "board.json").read_text())
    validate = [j for j in board["jobs"] if j["stage"] == "validate"]
    later = [j for j in board["jobs"] if j["stage"] != "validate"]
    assert any(jobs.can_run(board, j) for j in validate)
    assert all(jobs.can_run(board, j) for j in validate if jobs.deps_done(board, j))
    assert not any(jobs.can_run(board, j) for j in later)
    board["gates"]["validate"] = "passed"
    assert any(jobs.can_run(board, j) for j in later if j["stage"] == "clear" and jobs.deps_done(board, j))
    monkeypatch.setattr(util, "VENTURES", tmp_path)
    monkeypatch.setattr(jobs, "run_script", lambda script, folder, job, dry_run=False: {"skipped": "no free model answered: test"})
    assert jobs.run_venture("sample", 1) == 0  # no free model: nothing runs, nothing is lost
    board = json.loads((dst / "board.json").read_text())
    assert {j["status"] for j in board["jobs"]} == {"todo"}
    assert board["skipped"] and board["skipped"][0]["reason"].startswith("no free model")


def test_every_read_has_a_writer_or_an_owner():
    from foundry import contracts
    rows = contracts.scan()
    missing = contracts.gaps(rows)
    assert not missing, missing
    # the seams the department agents guessed at are now explicit
    writes = {w for r in rows for w in r["writes"]}
    for path in ("sell/icp.json", "sell/market-map.csv", "sell/ctas.json", "launch/brand.json", "launch/publish-log.json",
                 "launch/ad-brief.md", "commerce/landed-cost.json", "clear/platform-and-ad-compliance.md", "validate/report.md"):
        assert any(contracts.matches(path, [w]) for w in writes), path


def test_end_to_end_with_a_fake_model(monkeypatch, tmp_path):
    """A venture moves through validate with a model that answers, outputs land, gates and stage advance."""
    from foundry import dashboards, jobs

    def fake(prompt, skipped=None, prefer=None):
        if prompt.startswith("You are the audit engine"):
            return None, None  # heuristic audit
        return {"files": [{"path": "validate/out.md", "content": "# done"}, {"path": "validate/out.json", "content": "{}"}],
                "summary": "ok", "flag": "clear"}, "fake"

    def fake_script(script, folder, job, dry_run=False):
        (folder / "validate").mkdir(exist_ok=True)
        (folder / "validate" / f"{job['id']}.md").write_text("# done\n")
        return {"output": f"validate/{job['id']}.md", "outputs": [f"validate/{job['id']}.md"], "summary": "ok", "flag": "clear", "model": "fake"}

    monkeypatch.setattr(util, "ask_json", fake)
    monkeypatch.setattr(util, "VENTURES", tmp_path)
    monkeypatch.setattr(jobs, "run_script", fake_script)
    dst = tmp_path / "sample"
    dst.mkdir()
    (dst / "idea.json").write_text((ROOT / "tests" / "fixtures" / "sample-idea.json").read_text())
    launch.run_one("sample", root=tmp_path)
    assert jobs.run_venture("sample", 3) == 3
    board = json.loads((dst / "board.json").read_text())
    ran = [j for j in board["jobs"] if j["status"] in ("done", "review")]
    assert len(ran) == 3 and all(j["stage"] == "validate" for j in ran)
    assert any((dst / "validate").glob("*.md"))
    assert board["log"][0]["model"] == "fake"
    monkeypatch.setattr(util, "DATA", tmp_path)
    monkeypatch.setattr(dashboards, "OUT", tmp_path / "radar-data.json")
    data = dashboards.main()
    assert data["ventures"][0]["stages"]["validate"]["done"] >= 1


def test_dependencies_and_halt_gate_the_runner(monkeypatch, tmp_path):
    from foundry import jobs
    monkeypatch.setattr(util, "ask_json", lambda prompt, skipped=None, prefer=None: (None, None))
    dst = tmp_path / "sample"
    dst.mkdir()
    (dst / "idea.json").write_text((ROOT / "tests" / "fixtures" / "sample-idea.json").read_text())
    launch.run_one("sample", root=tmp_path)
    board = json.loads((dst / "board.json").read_text())
    by_id = {j["id"]: j for j in board["jobs"]}
    assert jobs.can_run(board, by_id["vertical-analysis"])
    assert not jobs.can_run(board, by_id["research-reports"]), "waits for the validate jobs it builds on"
    by_id["vertical-analysis"]["status"] = "done"
    for dep in ("vertical-analysis", "competitor-teardown", "tam-market-sizing", "pricing-research"):
        by_id[dep]["status"] = "done"
    assert jobs.can_run(board, by_id["research-reports"])
    board["verdict"] = "blocked"
    assert not jobs.can_run(board, by_id["vertical-analysis"]), "a blocked venture waits for Charlie"


def test_digest_lists_what_needs_charlie(monkeypatch, tmp_path):
    from foundry import digest
    monkeypatch.setattr(util, "ask_json", lambda prompt, skipped=None, prefer=None: (None, None))
    dst = tmp_path / "ventures" / "sample"
    dst.mkdir(parents=True)
    (dst / "idea.json").write_text((ROOT / "tests" / "fixtures" / "sample-idea.json").read_text())
    launch.run_one("sample", root=tmp_path / "ventures")
    board = json.loads((dst / "board.json").read_text())
    for j in board["jobs"]:
        if j["stage"] == "validate":
            j["status"] = "done"
    board["jobs"][0].update(status="review", outputs=["validate/report.md"])
    board["jobs"][1]["status"] = "skipped"
    board["skipped"] = [{"job": board["jobs"][1]["id"], "reason": "App Store: no answer", "date": "2026-11-01", "attempts": 3}]
    board["verdict"] = "blocked"
    board["log"] = [{"date": "2026-11-01", "job": "regulatory-screen", "status": "review", "flag": "stop", "summary": "licence needed", "model": "run.py"}]
    (dst / "board.json").write_text(json.dumps(board))
    monkeypatch.setattr(util, "VENTURES", tmp_path / "ventures")
    monkeypatch.setattr(digest, "OUT", tmp_path / "office" / "digest.md")
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    text = digest.main()
    assert "**Blocked** (regulatory-screen: licence needed)" in text
    assert "set `gates.validate: passed`" in text
    assert f"Review `{board['jobs'][0]['id']}`" in text and "foundry-ventures/blob/main/ventures/sample/validate/report.md" in text
    assert "gave up after 3 days" in text
    assert summary.read_text() == text + "\n" and (tmp_path / "office" / "digest.md").read_text() == text


def test_smoke_rehearses_stage_by_stage(monkeypatch, tmp_path):
    from foundry import jobs, smoke
    monkeypatch.setattr(util, "ask_json", lambda prompt, skipped=None, prefer=None: (None, None))
    monkeypatch.setattr(util, "VENTURES", tmp_path)
    dst = tmp_path / "sample"
    dst.mkdir()
    (dst / "idea.json").write_text((ROOT / "tests" / "fixtures" / "sample-idea.json").read_text())
    launch.run_one("sample", root=tmp_path)
    ran = []

    def fake_script(script, folder, job, dry_run=False):
        ran.append(job["id"])
        return {"output": f"{job['stage']}/{job['id']}.md", "outputs": [], "summary": "ok", "flag": "clear", "model": "fake"}
    monkeypatch.setattr(jobs, "run_script", fake_script)
    assert smoke.main(["--slug", "sample", "--through", "clear", "--limit", "2"]) == 0
    board = json.loads((dst / "board.json").read_text())
    assert board["gates"]["validate"] == "passed" and board["gates"]["clear"] == "passed" and board["gates"]["build"] == "open"
    stages = {j["stage"] for j in board["jobs"] if j["status"] in ("done", "review")}
    assert stages == {"validate", "clear"} and len(ran) == 4
    assert all(j["status"] == "skipped" for j in board["jobs"] if j["stage"] == "validate" and j["id"] not in ran)
    assert any(s["reason"].startswith("smoke:") for s in board["skipped"])


def test_keyless_search_drops_off_topic_rows(monkeypatch):
    """Bing serves suspected bots results for some other query; those rows never reach a job."""
    html = ('<li class="b_algo"><h2><a href="https://www.bing.com/ck/a?!&amp;&amp;p=x&amp;u=a1aHR0cHM6Ly93d3cuYm9vdHMuY29tL3BlYXJz&amp;ntb=1">Pears Transparent Soap</a></h2><p>Prices may vary.</p></li>'
            '<li class="b_algo"><h2><a href="https://www.mealime.com/">Mealime <b>Meal</b> Planner</a></h2><div><p class="b_lineclamp2">Plan meals &amp; shop in minutes.</p></div></li>')

    class R:
        status_code, text, url = 200, html, "https://www.bing.com/search"
    monkeypatch.setattr(util.requests, "get", lambda *a, **k: R())
    util._DOWN.pop("bing", None)
    rows = util.bing_search("meal planning app", 5)
    assert rows == [{"title": "Mealime Meal Planner", "url": "https://www.mealime.com/", "content": "Plan meals & shop in minutes.", "source": "bing"}]
    assert util.bing_target("https://www.bing.com/ck/a?!&amp;&amp;p=x&amp;u=a1aHR0cHM6Ly93d3cuYm9vdHMuY29tL3BlYXJz&amp;ntb=1") == "https://www.boots.com/pears"


def test_notify_keeps_one_needs_you_issue(monkeypatch, tmp_path):
    from foundry import digest, notify
    text = "# Foundry digest, 2026-11-01\n\n## Sample (`sample`)\nStage **validate**.\n\n### Needs you\n- Review `vertical-analysis` (assisted): [validate/vertical-analysis.md](https://github.com/x/y).\n- Stage **validate** is finished: set `gates.validate: passed`.\n\n## Other (`other`)\n\n### Needs you\n- Nothing. The workforce is running.\n"
    monkeypatch.setattr(digest, "OUT", tmp_path / "office" / "digest.md")
    monkeypatch.setattr(notify, "LAST", tmp_path / "office" / "needs-last.json")
    digest.OUT.parent.mkdir(parents=True)
    digest.OUT.write_text(text)
    items = notify.needs(text)
    assert list(items) == ["Sample (`sample`)"] and len(items["Sample (`sample`)"]) == 2
    monkeypatch.setenv("VENTURES_TOKEN", "")
    notify.main()
    assert not notify.LAST.exists(), "without a token nothing is recorded, so the next run with one still posts"
    calls = []

    class R:
        def __init__(self, data, status=200):
            self._d, self.status_code = data, status
        def json(self):
            return self._d
        def raise_for_status(self):
            pass
    monkeypatch.setenv("VENTURES_TOKEN", "t")
    monkeypatch.setattr(notify.requests, "get", lambda url, **kw: calls.append(("get", url)) or R([]))
    monkeypatch.setattr(notify.requests, "post", lambda url, **kw: calls.append(("post", url, kw["json"])) or R({"number": 7, "url": "u", "comments_url": "c"}))
    monkeypatch.setattr(notify.requests, "patch", lambda url, **kw: calls.append(("patch", url, kw["json"])) or R({}))
    notify.main()
    posts = [c for c in calls if c[0] == "post"]
    assert posts[0][1].endswith("/issues") and posts[0][2]["title"] == "Needs you" and "vertical-analysis" in posts[0][2]["body"]
    assert posts[1][1] == "c" and "New: Sample" in posts[1][2]["body"]
    assert json.loads(notify.LAST.read_text())["items"] == items
    calls.clear()
    notify.main()
    assert not calls, "an unchanged list makes no request"
    digest.OUT.write_text("# Foundry digest\n\n## Sample (`sample`)\n\n### Needs you\n- Nothing. The workforce is running.\n")
    monkeypatch.setattr(notify.requests, "get", lambda url, **kw: R([{"title": "Needs you", "url": "u", "comments_url": "c", "number": 7}]))
    notify.main()
    assert calls and calls[-1][0] == "patch" and calls[-1][2]["state"] == "closed"
