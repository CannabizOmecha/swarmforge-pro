import sqlite3

import pytest

from aegis.baseline import is_anomalous, mad, robust_anomaly_score
from aegis.dedup import finding_fingerprint
from aegis.engine import canonical_hash, execute_synthetic_run
from aegis.policy import AuthorizationError, authorize
from aegis.privacy import minimize_attributes, redact_text
from aegis.store import Store


def test_mad_and_robust_score():
    assert mad([1, 2, 3, 4, 100]) == 1
    assert robust_anomaly_score([10, 10, 10], 10) == 0
    assert is_anomalous([10, 10, 10], 99)


def test_policy_fails_closed():
    authorize("local-synthetic", "execute", 2)
    for scope, operation, count in [
        ("unknown", "execute", 1),
        ("local-synthetic", "execute", 201),
        ("local-synthetic", "publish", 1),
    ]:
        with pytest.raises(AuthorizationError):
            authorize(scope, operation, count)


def test_privacy_minimization():
    assert "[REDACTED_EMAIL]" in redact_text("contact a.person@example.com")
    clean = minimize_attributes(
        {"operation": "read", "email": "a.person@example.com", "status_code": 200}
    )
    assert "email" not in clean
    assert clean["operation"] == "read"


def test_synthetic_run_produces_reproducible_evidence():
    run, findings, evidence = execute_synthetic_run("local-synthetic", 10, 7)
    assert run.status == "completed"
    assert len(run.observations) == 10
    assert len(findings) == 1
    assert findings[0].state.value == "validated"
    assert len(evidence[0].payload_sha256) == 64
    assert canonical_hash(evidence[0].manifest) == evidence[0].payload_sha256
    assert run.replay_fingerprint is not None


def test_store_bundle_is_atomic_on_constraint_failure(tmp_path):
    store = Store(str(tmp_path / "atomic.sqlite3"))
    run_one, findings_one, evidence_one = execute_synthetic_run("local-synthetic", 10, 7)
    store.save_bundle(run_one, findings_one, evidence_one)
    before = store.counts()

    run_two, findings_two, evidence_two = execute_synthetic_run("local-synthetic", 10, 8)
    findings_two[0].finding_id = findings_one[0].finding_id
    with pytest.raises(sqlite3.IntegrityError):
        store.save_bundle(run_two, findings_two, evidence_two)

    assert store.get_run(run_two.run_id) is None
    assert store.counts() == before


def test_store_additive_migration_preserves_existing_tables(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE runs (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE findings (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE evidence (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        """)
    Store(str(path))
    with sqlite3.connect(path) as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"runs", "findings", "evidence", "idempotency", "audit_events"} <= tables


def test_remote_scope_is_not_supported():
    with pytest.raises(AuthorizationError):
        execute_synthetic_run("production", 5, 1)


def test_audit_chain_is_append_only_and_verifiable(tmp_path):
    store = Store(str(tmp_path / "audit.sqlite3"))
    store.append_audit_event(
        "agent.task.completed", "task-1", {"status": "completed", "expert": "critic"}
    )
    store.append_audit_event(
        "agent.task.abstained", "task-2", {"status": "abstained", "expert": "critic"}
    )
    verification = store.verify_audit_chain()
    assert verification["valid"] is True
    assert verification["event_count"] == 2
    assert len(store.list_audit_events()) == 2

    with sqlite3.connect(store.path) as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE audit_events SET payload='{}' WHERE sequence=1")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("DELETE FROM audit_events WHERE sequence=1")


def test_audit_chain_detects_payload_tampering(tmp_path):
    store = Store(str(tmp_path / "audit-tamper.sqlite3"))
    store.append_audit_event("agent.task.completed", "task-1", {"status": "completed"})
    with sqlite3.connect(store.path) as db:
        db.execute("DROP TRIGGER audit_events_no_update")
        db.execute("UPDATE audit_events SET payload='{}' WHERE sequence=1")
    verification = store.verify_audit_chain()
    assert verification["valid"] is False
    assert verification["failed_sequence"] == 1
    assert verification["reason"] == "event_hash_mismatch"


def test_finding_fingerprint_ignores_run_specific_identifiers():
    _, first_findings, _ = execute_synthetic_run("local-synthetic", 10, 7)
    _, second_findings, _ = execute_synthetic_run("local-synthetic", 10, 8)
    assert first_findings[0].finding_id != second_findings[0].finding_id
    assert first_findings[0].run_id != second_findings[0].run_id
    assert finding_fingerprint(first_findings[0]) == finding_fingerprint(second_findings[0])
