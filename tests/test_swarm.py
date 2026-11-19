import time

import pytest
from fastapi.testclient import TestClient

import main
from swarm import Swarm


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("SWARMFORGE_ADMIN_TOKEN", raising=False)
    main.swarm = Swarm()
    with TestClient(main.app) as c:
        yield c


def wait_for(client, task_id, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        t = client.get(f"/omniscience/tasks/{task_id}").json()
        if t["status"] in ("done", "failed", "cancelled"):
            return t
        time.sleep(0.02)
    raise AssertionError(f"task {task_id} never finished")


def test_boot_and_legacy_routes(client):
    assert client.get("/").status_code == 200
    d = client.post("/deploy").json()
    assert d["status"] == "SUCCESS"
    assert set(d["agents"]) == {"developer", "marketer", "analyst", "compliance"}
    assert client.get("/revenue").json() == {"recorded_total": 0, "entries": 0, "projection": None}
    assert client.get("/health").json()["live_agents"] == 4


def test_dispatch_runs_and_is_observable(client):
    t = client.post("/omnipotence/tasks", json={"role": "analyst", "payload": {"q": 1}}).json()
    done = wait_for(client, t["id"])
    assert done["status"] == "done" and done["result"]["handled"] == ["q"]
    kinds = [e["kind"] for e in client.get("/omniscience/events").json()]
    assert {"task.queued", "task.started", "task.done"} <= set(kinds)
    state = client.get("/omniscience/state").json()
    assert state["tasks"]["by_status"]["done"] == 1


def test_failures_are_captured(client):
    t = client.post("/omnipotence/tasks", json={"role": "developer", "payload": {"fail": "boom"}}).json()
    done = wait_for(client, t["id"])
    assert done["status"] == "failed" and "boom" in done["error"]


def test_unknown_role_404(client):
    assert client.post("/omnipotence/tasks", json={"role": "nope"}).status_code == 404


def test_pause_holds_work_until_resume(client):
    agent = next(a for a in client.get("/omniscience/state").json()["agents"] if a["role"] == "marketer")
    client.post(f"/omnipotence/agents/{agent['id']}/pause")
    t = client.post("/omnipotence/tasks", json={"role": "marketer", "payload": {}}).json()
    time.sleep(0.2)
    assert client.get(f"/omniscience/tasks/{t['id']}").json()["status"] == "queued"
    client.post(f"/omnipotence/agents/{agent['id']}/resume")
    assert wait_for(client, t["id"])["status"] == "done"


def test_scale_and_broadcast(client):
    r = client.post("/omnipotence/roles/analyst/scale", json={"count": 3}).json()
    assert len(r["spawned"]) == 2
    tasks = client.post("/omnipotence/broadcast", json={"ping": True}).json()
    assert len(tasks) == 4
    for t in tasks:
        assert wait_for(client, t["id"])["status"] == "done"


def test_irreversible_actions_need_approval(client):
    agent = client.get("/omniscience/state").json()["agents"][0]
    p = client.post("/omnipotence/proposals",
                    json={"action": "stop_agent", "params": {"agent_id": agent["id"]}}).json()
    assert p["status"] == "pending"
    assert client.get(f"/omniscience/agents/{agent['id']}").json()["state"] != "stopped"
    d = client.post(f"/omnipotence/proposals/{p['id']}/decide", json={"approve": True}).json()
    assert d["status"] == "approved"
    assert client.get(f"/omniscience/agents/{agent['id']}").json()["state"] == "stopped"
    # cannot decide twice
    assert client.post(f"/omnipotence/proposals/{p['id']}/decide", json={"approve": True}).status_code == 409


def test_rejected_and_invalid_proposals(client):
    p = client.post("/omnipotence/proposals",
                    json={"action": "record_revenue", "params": {"amount": 50}}).json()
    client.post(f"/omnipotence/proposals/{p['id']}/decide", json={"approve": False})
    assert client.get("/revenue").json()["entries"] == 0
    assert client.post("/omnipotence/proposals", json={"action": "rm_rf"}).status_code == 400
    assert client.post("/omnipotence/proposals",
                       json={"action": "stop_agent", "params": {"agent_id": "x"}}).status_code == 400


def test_revenue_only_counts_recorded(client):
    for amt in (100, 25.5):
        p = client.post("/omnipotence/proposals",
                        json={"action": "record_revenue", "params": {"amount": amt}}).json()
        client.post(f"/omnipotence/proposals/{p['id']}/decide", json={"approve": True})
    rev = client.get("/revenue").json()
    assert rev["recorded_total"] == 125.5 and rev["entries"] == 2


def test_admin_token_guards_control_plane(client, monkeypatch):
    monkeypatch.setenv("SWARMFORGE_ADMIN_TOKEN", "s3cret")
    body = {"role": "analyst", "payload": {}}
    assert client.post("/omnipotence/tasks", json=body).status_code == 401
    assert client.post("/omnipotence/tasks", json=body, headers={"X-Admin-Token": "s3cret"}).status_code == 202
    assert client.get("/omniscience/state").status_code == 200  # read side stays open
