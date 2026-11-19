import json
import os

os.environ["SWARMFORGE_DEMO"] = "1"

import pytest
from fastapi.testclient import TestClient

from swarmforge import AuditLog, FakeLLM, Swarm
from swarmforge.llm import _strict_schema
from swarmforge.schemas import Proposal, RunStatus


def make(tmp_path, **kw):
    return Swarm(FakeLLM(**kw), AuditLog(tmp_path / "a.jsonl"))


def test_reversible_plan_completes(tmp_path):
    r = make(tmp_path).run("Validate demand for a reskilling newsletter")
    assert r.status == RunStatus.completed
    assert len(r.proposals) == 5 and r.chosen is not None


def test_irreversible_plan_requires_human(tmp_path):
    r = make(tmp_path, irreversible=True).run("Launch paid ads")
    assert r.status == RunStatus.awaiting_approval


def test_partial_expert_failure_is_contained(tmp_path):
    r = make(tmp_path, fail_experts={"contrarian", "pragmatist"}).run("x")
    errs = [p for p in r.proposals if p.error]
    assert len(errs) == 2 and r.status == RunStatus.completed


def test_all_fail_reports_failure(tmp_path):
    names = {"first_principles", "pragmatist", "contrarian", "safety_engineer", "user_advocate"}
    r = make(tmp_path, fail_experts=names).run("x")
    assert r.status == RunStatus.failed and r.error


@pytest.mark.parametrize("goal", ["", "   ", "x" * 5000])
def test_bad_goal_rejected(tmp_path, goal):
    with pytest.raises(ValueError):
        make(tmp_path).run(goal)


def test_audit_chain_detects_tampering(tmp_path):
    s = make(tmp_path)
    s.run("a"); s.run("b")
    assert s.audit.verify()
    lines = s.audit.path.read_text().splitlines()
    rec = json.loads(lines[0]); rec["data"]["goal"] = "tampered"
    lines[0] = json.dumps(rec, sort_keys=True)
    s.audit.path.write_text("\n".join(lines) + "\n")
    assert not s.audit.verify()


def test_strict_schema_closes_objects():
    s = _strict_schema(Proposal)
    assert s["additionalProperties"] is False and set(s["required"]) == set(s["properties"])


def test_api_approval_flow(tmp_path, monkeypatch):
    import main

    monkeypatch.setattr(main, "swarm", Swarm(FakeLLM(irreversible=True), AuditLog(tmp_path / "b.jsonl")))
    monkeypatch.setattr(main, "audit", main.swarm.audit)
    c = TestClient(main.app)
    assert c.get("/health").json()["ok"]
    run = c.post("/runs", json={"goal": "Sign a lease"}).json()
    assert run["status"] == "awaiting_approval"
    d = c.post(f"/runs/{run['id']}/decision", json={"approve": True}).json()
    assert d["status"] == "approved" and d["decided_by"] == "human"
    assert c.post(f"/runs/{run['id']}/decision", json={"approve": True}).status_code == 409
    assert c.get("/runs/nope").status_code == 404
    assert c.post("/runs", json={"goal": ""}).status_code == 422
