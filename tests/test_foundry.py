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
    assert all(jobs.can_run(board, j) for j in validate)
    assert not any(jobs.can_run(board, j) for j in later)
    board["gates"]["validate"] = "passed"
    assert any(jobs.can_run(board, j) for j in later if j["stage"] == "clear")
    monkeypatch.setattr(util, "VENTURES", tmp_path)
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

    monkeypatch.setattr(util, "ask_json", fake)
    monkeypatch.setattr(util, "VENTURES", tmp_path)
    dst = tmp_path / "sample"
    dst.mkdir()
    (dst / "idea.json").write_text((ROOT / "tests" / "fixtures" / "sample-idea.json").read_text())
    launch.run_one("sample", root=tmp_path)
    assert jobs.run_venture("sample", 3) == 3
    board = json.loads((dst / "board.json").read_text())
    ran = [j for j in board["jobs"] if j["status"] in ("done", "review")]
    assert len(ran) == 3 and all(j["stage"] == "validate" for j in ran)
    assert (dst / "validate" / "out.md").exists() and (dst / "validate" / "out.json").exists()
    assert board["log"][0]["model"] == "fake"
    monkeypatch.setattr(util, "DATA", tmp_path)
    monkeypatch.setattr(dashboards, "OUT", tmp_path / "radar-data.json")
    data = dashboards.main()
    assert data["ventures"][0]["stages"]["validate"]["done"] >= 1
