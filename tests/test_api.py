from fastapi.testclient import TestClient

import aegis.api as api
from aegis.store import Store


def test_health_and_agents():
    client = TestClient(api.app)
    assert client.get("/health").json()["status"] == "ok"
    names = {agent["name"] for agent in client.get("/agents").json()["agents"]}
    assert {"governance", "security_validator", "evidence"} <= names


def test_scope_rejection_and_run_persistence(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "store", Store(str(tmp_path / "test.sqlite3")))
    client = TestClient(api.app)

    denied = client.post("/runs", json={"scope_id": "production", "batch_size": 5, "seed": 1})
    assert denied.status_code == 403

    response = client.post("/runs", json={"scope_id": "local-synthetic", "batch_size": 10, "seed": 11})
    assert response.status_code == 200
    payload = response.json()
    run_id = payload["run"]["run_id"]
    assert payload["run"]["status"] == "completed"
    assert payload["run"]["validated_count"] == 1
    assert len(payload["evidence"]) == 1

    fetched = client.get(f"/runs/{run_id}")
    assert fetched.status_code == 200
    assert fetched.json()["run_id"] == run_id
    assert client.get("/metrics").json()["runs"] == 1


def test_missing_run_returns_404():
    client = TestClient(api.app)
    assert client.get("/runs/not-a-run").status_code == 404
