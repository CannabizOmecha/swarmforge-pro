from datetime import UTC, datetime
import json
import sqlite3

import pytest
from pydantic import ValidationError

from aegis.backfill import rebuild_finding_groups
from aegis.engine import execute_synthetic_run
from aegis.store import Store


def _persist_legacy_finding(store, finding):
    with sqlite3.connect(store.path) as db:
        db.execute(
            "INSERT INTO findings (id, payload) VALUES (?, ?)",
            (finding.finding_id, finding.model_dump_json()),
        )


def test_backfill_reconciles_historical_findings_and_is_idempotent(tmp_path):
    store = Store(str(tmp_path / "backfill.sqlite3"))
    first_run, first_findings, _ = execute_synthetic_run("local-synthetic", 10, 7)
    second_run, second_findings, second_evidence = execute_synthetic_run(
        "local-synthetic", 10, 8
    )
    older = first_findings[0].model_copy(
        update={"created_at": datetime(2024, 1, 1, tzinfo=UTC)}
    )
    newer = second_findings[0].model_copy(
        update={"created_at": datetime(2024, 2, 1, tzinfo=UTC)}
    )

    # Simulate a database where only post-feature findings were grouped.
    store.save_bundle(second_run, [newer], second_evidence)
    _persist_legacy_finding(store, older)
    audit_before = store.counts()["audit_events"]

    preview = rebuild_finding_groups(store)
    assert preview == {
        "mode": "dry_run",
        "changed": True,
        "applied": False,
        "source_finding_count": 2,
        "expected_group_count": 1,
        "previous_group_count": 1,
    }
    assert store.list_finding_groups()[0]["occurrence_count"] == 1
    assert store.counts()["audit_events"] == audit_before

    applied = rebuild_finding_groups(store, apply=True)
    assert applied["applied"] is True
    group = store.list_finding_groups()[0]
    assert group["occurrence_count"] == 2
    assert group["first_run_id"] == first_run.run_id
    assert group["last_run_id"] == second_run.run_id
    assert group["last_finding_id"] == newer.finding_id
    assert store.counts()["audit_events"] == audit_before + 1
    assert store.verify_audit_chain()["valid"] is True

    repeated = rebuild_finding_groups(store, apply=True)
    assert repeated["changed"] is False
    assert repeated["applied"] is False
    assert store.counts()["audit_events"] == audit_before + 1


def test_backfill_aborts_without_partial_changes_on_malformed_source(tmp_path):
    store = Store(str(tmp_path / "backfill-invalid.sqlite3"))
    run, findings, evidence = execute_synthetic_run("local-synthetic", 10, 7)
    store.save_bundle(run, findings, evidence)
    groups_before = store.list_finding_groups()
    audit_before = store.counts()["audit_events"]

    with sqlite3.connect(store.path) as db:
        db.execute(
            "INSERT INTO findings (id, payload) VALUES (?, ?)",
            ("malformed-finding", "{not-json"),
        )

    with pytest.raises(ValidationError):
        rebuild_finding_groups(store, apply=True)

    assert store.list_finding_groups() == groups_before
    assert store.counts()["audit_events"] == audit_before
    assert store.verify_audit_chain()["valid"] is True


def test_backfill_rejects_mismatched_storage_and_payload_ids(tmp_path):
    store = Store(str(tmp_path / "backfill-mismatch.sqlite3"))
    _, findings, _ = execute_synthetic_run("local-synthetic", 10, 7)
    payload = json.loads(findings[0].model_dump_json())
    with sqlite3.connect(store.path) as db:
        db.execute(
            "INSERT INTO findings (id, payload) VALUES (?, ?)",
            ("different-id", json.dumps(payload)),
        )

    with pytest.raises(ValueError, match="identifier"):
        rebuild_finding_groups(store, apply=True)
    assert store.list_finding_groups() == []
