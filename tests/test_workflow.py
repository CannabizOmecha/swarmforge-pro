import pytest

from aegis import workflow
from aegis.engine import canonical_hash, execute_synthetic_run
from aegis.models import TestRequest as RunRequest
from aegis.store import Store
from aegis.workflow import (
    IdempotencyConflict,
    WorkflowExecutionError,
    WorkflowRetryExhausted,
    process_run,
    resume_workflow,
)


def request(key="workflow-test-key-0001"):
    return RunRequest(scope_id="local-synthetic", batch_size=10, seed=41, idempotency_key=key)


def test_workflow_persists_checkpoints_and_commits_bundle_atomically(tmp_path):
    store = Store(str(tmp_path / "workflow.sqlite3"))
    result = process_run(store, request())
    state = store.get_workflow(result["workflow_id"])

    assert state["state"] == "committed"
    assert state["attempt_count"] == 1
    assert state["stage_payload"]["workflow_id"] == result["workflow_id"]
    assert store.counts()["runs"] == 1
    assert store.counts()["workflows"] == 1
    audit = store.list_audit_events(100)
    event_types = {event["event_type"] for event in audit}
    assert {
        "workflow.accepted",
        "workflow.state_transition",
        "workflow.attempt_started",
        "run.bundle_saved",
        "workflow.committed",
    } <= event_types
    assert store.verify_audit_chain()["valid"] is True
    assert process_run(store, request()) == result
    assert store.counts()["runs"] == 1


def test_execution_failure_resumes_same_workflow_without_duplicate_run(tmp_path, monkeypatch):
    store = Store(str(tmp_path / "retry.sqlite3"))
    original = workflow.execute_synthetic_run
    calls = 0

    def fail_once(*args):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("synthetic transient failure")
        return original(*args)

    monkeypatch.setattr(workflow, "execute_synthetic_run", fail_once)
    with pytest.raises(WorkflowExecutionError) as caught:
        process_run(store, request("workflow-retry-key-0001"))

    workflow_id = caught.value.workflow_id
    checkpoint = store.get_workflow(workflow_id)
    assert checkpoint["state"] == "authorized"
    assert checkpoint["attempt_count"] == 1
    assert checkpoint["last_error_code"] == "execution_failed"

    result = resume_workflow(store, workflow_id)
    completed = store.get_workflow(workflow_id)
    assert result["workflow_id"] == workflow_id
    assert completed["state"] == "committed"
    assert completed["attempt_count"] == 2
    assert store.counts()["runs"] == 1


def test_workflow_retry_budget_is_bounded(tmp_path, monkeypatch):
    store = Store(str(tmp_path / "exhausted.sqlite3"))
    calls = 0

    def always_fail(*args):
        nonlocal calls
        calls += 1
        raise RuntimeError("synthetic failure")

    monkeypatch.setattr(workflow, "execute_synthetic_run", always_fail)
    workflow_id = None
    for attempt in range(3):
        with pytest.raises((WorkflowExecutionError, WorkflowRetryExhausted)) as caught:
            process_run(store, request("workflow-exhaust-key-0001"))
        workflow_id = caught.value.workflow_id

    assert store.get_workflow(workflow_id)["state"] == "exhausted"
    with pytest.raises(WorkflowRetryExhausted):
        resume_workflow(store, workflow_id)
    assert calls == 3
    assert store.counts()["runs"] == 0


def test_executed_checkpoint_resumes_commit_without_rerunning_engine(tmp_path, monkeypatch):
    store = Store(str(tmp_path / "commit-retry.sqlite3"))
    original_execute = workflow.execute_synthetic_run
    original_save = store.save_bundle
    calls = 0
    fail_commit = True

    def count_execute(*args):
        nonlocal calls
        calls += 1
        return original_execute(*args)

    def fail_commit_once(*args, **kwargs):
        nonlocal fail_commit
        if fail_commit:
            fail_commit = False
            raise RuntimeError("simulated storage interruption")
        return original_save(*args, **kwargs)

    monkeypatch.setattr(workflow, "execute_synthetic_run", count_execute)
    monkeypatch.setattr(store, "save_bundle", fail_commit_once)
    with pytest.raises(WorkflowExecutionError) as caught:
        process_run(store, request("workflow-commit-key-0001"))

    workflow_id = caught.value.workflow_id
    assert store.get_workflow(workflow_id)["state"] == "executed"
    result = resume_workflow(store, workflow_id)
    assert result["workflow_id"] == workflow_id
    assert store.get_workflow(workflow_id)["state"] == "committed"
    assert calls == 1
    assert store.counts()["runs"] == 1


def test_invalid_workflow_transition_is_rejected(tmp_path):
    store = Store(str(tmp_path / "transition.sqlite3"))
    store.create_workflow(
        "workflow-transition-test",
        None,
        "a" * 64,
        {"scope_id": "local-synthetic", "batch_size": 1, "seed": 1},
    )
    with pytest.raises(ValueError):
        store.transition_workflow(
            "workflow-transition-test", "accepted", "committed"
        )


def test_legacy_idempotency_records_survive_workflow_upgrade(tmp_path):
    store = Store(str(tmp_path / "legacy-idempotency.sqlite3"))
    key = "legacy-request-key-0001"
    request_payload = {"scope_id": "local-synthetic", "batch_size": 10, "seed": 41}
    run, findings, evidence = execute_synthetic_run("local-synthetic", 10, 41)
    legacy_response = {
        "run": run.model_dump(mode="json"),
        "findings": [item.model_dump(mode="json") for item in findings],
        "evidence": [item.model_dump(mode="json") for item in evidence],
    }
    store.save_bundle(
        run,
        findings,
        evidence,
        idempotency_key=key,
        request_fingerprint=canonical_hash(request_payload),
        response_payload=legacy_response,
    )

    same_request = RunRequest(**request_payload, idempotency_key=key)
    assert process_run(store, same_request) == legacy_response
    assert store.counts()["runs"] == 1
    assert store.counts()["workflows"] == 0

    different_request = RunRequest(
        scope_id="local-synthetic", batch_size=10, seed=42, idempotency_key=key
    )
    with pytest.raises(IdempotencyConflict):
        process_run(store, different_request)
    assert store.counts()["runs"] == 1


def test_retry_and_recovery_outcomes_are_counted_without_identifiers(tmp_path, monkeypatch):
    from aegis.observability import RELIABILITY_METRICS

    store = Store(str(tmp_path / "reliability-retry.sqlite3"))
    before = RELIABILITY_METRICS.snapshot()
    original = workflow.execute_synthetic_run
    calls = 0

    def fail_once(*args):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("private synthetic diagnostic")
        return original(*args)

    monkeypatch.setattr(workflow, "execute_synthetic_run", fail_once)
    with pytest.raises(WorkflowExecutionError) as caught:
        process_run(store, request("reliability-retry-key-001"))
    workflow_id = caught.value.workflow_id
    after_failure = RELIABILITY_METRICS.snapshot()
    assert after_failure["workflow_retries"]["scheduled"] == (
        before["workflow_retries"]["scheduled"] + 1
    )
    assert after_failure["workflow_stage_failures"]["execute"] == (
        before["workflow_stage_failures"]["execute"] + 1
    )

    resume_workflow(store, workflow_id)
    after_resume = RELIABILITY_METRICS.snapshot()
    assert after_resume["workflow_recovery_outcomes"]["completed"] == (
        before["workflow_recovery_outcomes"]["completed"] + 1
    )
    serialized = repr(after_resume)
    assert workflow_id not in serialized
    assert "private synthetic diagnostic" not in serialized
