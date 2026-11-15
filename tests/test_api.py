import json
import sqlite3

from fastapi.testclient import TestClient

from aegis import api
from aegis.store import Store


def client_for(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "store", Store(str(tmp_path / "test.sqlite3")))
    return TestClient(api.app)


def test_health_scope_and_agent_routing(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch)
    assert client.get("/health").json()["network_testing"] is False
    scopes = client.get("/scope").json()["scopes"]
    assert len(scopes) == 1
    assert scopes[0]["scope_id"] == "local-synthetic"
    assert client.get("/routing/run").json()["execution_mode"] == "deterministic"
    assert client.get("/routing/not-a-task").status_code == 404


def test_run_persistence_and_evidence_verification(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch)
    response = client.post(
        "/runs", json={"scope_id": "local-synthetic", "batch_size": 10, "seed": 7}
    )
    assert response.status_code == 200
    payload = response.json()
    run_id = payload["run"]["run_id"]
    assert client.get(f"/runs/{run_id}").status_code == 200
    assert len(payload["findings"]) == 1
    evidence_id = payload["evidence"][0]["evidence_id"]
    assert client.get(f"/evidence/{evidence_id}").status_code == 200
    verification = client.get(f"/evidence/{evidence_id}/verify").json()
    assert verification["valid"] is True
    assert verification["schema_valid"] is True
    assert verification["algorithm"] == "sha256"
    assert client.get("/metrics").json()["validated_findings"] == 1


def test_evidence_verification_detects_manifest_tampering(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch)
    response = client.post(
        "/runs", json={"scope_id": "local-synthetic", "batch_size": 10, "seed": 7}
    )
    evidence_id = response.json()["evidence"][0]["evidence_id"]
    store = api.store
    with sqlite3.connect(store.path) as db:
        row = db.execute("SELECT payload FROM evidence WHERE id=?", (evidence_id,)).fetchone()
        payload = json.loads(row[0])
        payload["manifest"]["actual"] = "tampered but schema-valid"
        db.execute(
            "UPDATE evidence SET payload=? WHERE id=?",
            (json.dumps(payload), evidence_id),
        )
    verification = client.get(f"/evidence/{evidence_id}/verify").json()
    assert verification["schema_valid"] is True
    assert verification["valid"] is False
    assert verification["expected_sha256"] != verification["actual_sha256"]


def test_unknown_scope_and_invalid_request_are_rejected(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch)
    denied = client.post(
        "/runs", json={"scope_id": "production", "batch_size": 5, "seed": 1}
    )
    assert denied.status_code == 403
    malformed = client.post(
        "/runs", json={"scope_id": "local-synthetic", "batch_size": 999, "seed": 1}
    )
    assert malformed.status_code == 422
    unknown = client.get("/runs/not-found")
    assert unknown.status_code == 404
    assert client.get("/evidence/not-found/verify").status_code == 404
