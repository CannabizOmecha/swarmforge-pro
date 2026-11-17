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
    agents = client.get("/agents").json()["agents"]
    assert any(agent["name"] == "critic" for agent in agents)
    assert client.get("/routing/not-a-task").status_code == 404


def test_agent_task_endpoint_runs_only_bounded_synthetic_fixture(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch)
    response = client.post(
        "/agent-tasks",
        json={
            "task_type": "validate_fixture",
            "payload": {"fixture_id": "authz-deny-v1", "observed_decision": "allow"},
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["expert_name"] == "security_validator"
    assert result["status"] == "completed"
    assert result["output"]["violation_confirmed"] is True
    assert result["adapter_mode"] == "deterministic_mock"


def test_agent_task_endpoint_rejects_untrusted_payloads(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch)
    response = client.post(
        "/agent-tasks",
        json={
            "task_type": "inspect_fixture",
            "payload": {"fixture_id": "authz-deny-v1", "target_url": "https://example.com"},
        },
    )
    assert response.status_code == 422
    malformed = client.post(
        "/agent-tasks",
        json={
            "task_type": "validate_fixture",
            "payload": {"fixture_id": "authz-deny-v1", "observed_decision": "execute"},
        },
    )
    assert malformed.status_code == 422


def test_agent_pipeline_endpoint_runs_three_independent_experts(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch)
    response = client.post(
        "/agent-pipelines/validate",
        json={"fixture_id": "authz-deny-v1", "observed_decision": "allow"},
    )
    assert response.status_code == 200
    result = response.json()
    assert [stage["expert_name"] for stage in result["stages"]] == [
        "test_generator",
        "security_validator",
        "critic",
    ]
    assert result["summary"]["violation_confirmed"] is True
    assert result["summary"]["critic_accepted"] is True
    assert result["summary"]["persistence"] == "not_performed"


def test_agent_pipeline_endpoint_rejects_non_synthetic_scope(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch)
    response = client.post(
        "/agent-pipelines/validate",
        json={
            "scope_id": "production",
            "fixture_id": "authz-deny-v1",
            "observed_decision": "allow",
        },
    )
    assert response.status_code == 422


def test_run_persistence_and_evidence_verification(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch)
    response = client.post(
        "/runs", json={"scope_id": "local-synthetic", "batch_size": 10, "seed": 7}
    )
    assert response.status_code == 200
    payload = response.json()
    run_id = payload["run"]["run_id"]
    workflow_id = payload["workflow_id"]
    assert client.get(f"/workflows/{workflow_id}").json()["state"] == "committed"
    assert client.get(f"/runs/{run_id}").status_code == 200
    assert len(payload["findings"]) == 1
    evidence_id = payload["evidence"][0]["evidence_id"]
    assert client.get(f"/evidence/{evidence_id}").status_code == 200
    verification = client.get(f"/evidence/{evidence_id}/verify").json()
    assert verification["valid"] is True
    assert verification["schema_valid"] is True
    assert verification["algorithm"] == "sha256"
    assert client.get("/metrics").json()["validated_findings"] == 1


def test_idempotency_returns_original_run_and_rejects_key_reuse(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch)
    request = {
        "scope_id": "local-synthetic",
        "batch_size": 10,
        "seed": 7,
        "idempotency_key": "request-key-00000001",
    }
    first = client.post("/runs", json=request)
    repeated = client.post("/runs", json=request)
    assert first.status_code == 200
    assert repeated.status_code == 200
    assert repeated.json() == first.json()
    assert client.get("/metrics").json()["runs"] == 1

    conflicting = {**request, "seed": 8}
    assert client.post("/runs", json=conflicting).status_code == 409
    assert client.get("/metrics").json()["runs"] == 1


def test_run_replay_reproduces_semantic_fingerprint(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch)
    response = client.post(
        "/runs", json={"scope_id": "local-synthetic", "batch_size": 10, "seed": 17}
    )
    run_id = response.json()["run"]["run_id"]
    replay = client.get(f"/runs/{run_id}/replay")
    assert replay.status_code == 200
    assert replay.json()["reproducible"] is True
    assert replay.json()["expected_fingerprint"] == replay.json()["actual_fingerprint"]


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
    invalid_key = client.post(
        "/runs",
        json={
            "scope_id": "local-synthetic",
            "batch_size": 5,
            "seed": 1,
            "idempotency_key": "short",
        },
    )
    assert invalid_key.status_code == 422
    unknown = client.get("/runs/not-found")
    assert unknown.status_code == 404
    assert client.get("/evidence/not-found/verify").status_code == 404
