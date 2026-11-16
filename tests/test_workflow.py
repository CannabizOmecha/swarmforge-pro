import pytest

from aegis import workflow
from aegis.models import TestRequest
from aegis.store import Store
from aegis.workflow import (
    WorkflowExecutionError,
    WorkflowRetryExhausted,
    process_run,
    resume_workflow,
)


def request(key="workflow-test-key-0001"):
    return TestRequest(scope_id="local-synthetic", batch_size=10, seed=41, idempotency_key=key)


def test_workflow_persists_checkpoints_and_commits_bundle_atomically(tmp_path):
    store = Store(str(tmp_path / "workflow.sqlite3"))
    result = process_run(store, request())
    state = store.get_workflow(result["workflow_id"])

    assert state["state"] == "committed"
    assert state["attempt_count"] == 1
    assert state["stage_payload"]["workflow_id"] == result["workflow_id"]
    assert store.counts()["runs"] == 1
    assert store.counts()["workflows"] == 1
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
