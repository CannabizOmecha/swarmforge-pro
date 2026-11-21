from __future__ import annotations

import sqlite3
from typing import Any
from uuid import uuid4

from .engine import canonical_hash, execute_synthetic_run
from .models import EvidenceRecord, Finding, RunRecord, TestRequest
from .observability import workflow_stage
from .policy import AuthorizationError, authorize
from .store import Store, WorkflowStateConflict


class IdempotencyConflict(ValueError):
    pass


class WorkflowExecutionError(RuntimeError):
    def __init__(self, workflow_id: str, stage: str):
        super().__init__(f"Workflow {stage} stage failed.")
        self.workflow_id = workflow_id
        self.stage = stage


class WorkflowRetryExhausted(RuntimeError):
    def __init__(self, workflow_id: str):
        super().__init__("Workflow execution retry budget exhausted.")
        self.workflow_id = workflow_id


class WorkflowNotFound(LookupError):
    pass


def _request_payload(request: TestRequest) -> dict[str, Any]:
    return request.model_dump(exclude={"idempotency_key"})


def _load_committed_response(store: Store, workflow_id: str) -> dict[str, Any]:
    workflow = store.get_workflow(workflow_id)
    if workflow is None or workflow["state"] != "committed" or workflow["stage_payload"] is None:
        raise WorkflowStateConflict("Committed workflow is missing its response checkpoint.")
    return workflow["stage_payload"]


def _drive_workflow(store: Store, workflow_id: str) -> dict[str, Any]:
    while True:
        workflow = store.get_workflow(workflow_id)
        if workflow is None:
            raise WorkflowNotFound(workflow_id)

        state = workflow["state"]
        request = TestRequest.model_validate(workflow["request_payload"])

        if state == "committed":
            return _load_committed_response(store, workflow_id)
        if state == "rejected":
            raise AuthorizationError("Workflow scope is not authorized.")
        if state == "exhausted":
            raise WorkflowRetryExhausted(workflow_id)

        if state == "accepted":
            try:
                with workflow_stage("authorize"):
                    authorize(request.scope_id, "execute", request.batch_size)
            except AuthorizationError:
                store.reject_workflow(workflow_id)
                raise
            store.transition_workflow(workflow_id, "accepted", "authorized")
            continue

        if state == "authorized":
            try:
                store.begin_workflow_attempt(workflow_id)
            except WorkflowStateConflict as exc:
                latest = store.get_workflow(workflow_id)
                if latest and latest["state"] == "exhausted":
                    raise WorkflowRetryExhausted(workflow_id) from exc
                if latest and latest["state"] == "committed":
                    return _load_committed_response(store, workflow_id)
                raise
            try:
                with workflow_stage("execute"):
                    run, findings, evidence = execute_synthetic_run(
                        request.scope_id, request.batch_size, request.seed
                    )
            except Exception as exc:
                latest = store.record_workflow_failure(workflow_id, "execution_failed")
                if latest["state"] == "exhausted":
                    raise WorkflowRetryExhausted(workflow_id) from exc
                raise WorkflowExecutionError(workflow_id, "execution") from exc

            stage_payload = {
                "run": run.model_dump(mode="json"),
                "findings": [item.model_dump(mode="json") for item in findings],
                "evidence": [item.model_dump(mode="json") for item in evidence],
            }
            try:
                with workflow_stage("checkpoint"):
                    store.transition_workflow(
                        workflow_id, "authorized", "executed", stage_payload=stage_payload
                    )
            except WorkflowStateConflict:
                latest = store.get_workflow(workflow_id)
                if latest and latest["state"] == "committed":
                    return _load_committed_response(store, workflow_id)
                if latest and latest["state"] == "executed":
                    continue
                raise
            continue

        if state == "executed":
            payload = workflow["stage_payload"]
            run = RunRecord.model_validate(payload["run"])
            findings = [Finding.model_validate(item) for item in payload["findings"]]
            evidence = [EvidenceRecord.model_validate(item) for item in payload["evidence"]]
            response = {"workflow_id": workflow_id, **payload}
            try:
                with workflow_stage("commit"):
                    store.save_bundle(
                        run,
                        findings,
                        evidence,
                        response_payload=response,
                        workflow_id=workflow_id,
                    )
            except Exception as exc:
                latest = store.get_workflow(workflow_id)
                if latest and latest["state"] == "committed":
                    return _load_committed_response(store, workflow_id)
                raise WorkflowExecutionError(workflow_id, "commit") from exc
            return response

        raise WorkflowStateConflict(f"Unknown workflow state: {state}")


def process_run(store: Store, request: TestRequest) -> dict[str, Any]:
    payload = _request_payload(request)
    fingerprint = canonical_hash(payload)
    workflow = None
    if request.idempotency_key is not None:
        workflow = store.get_workflow_by_idempotency_key(request.idempotency_key)
        if workflow is not None and workflow["request_fingerprint"] != fingerprint:
            raise IdempotencyConflict("Idempotency key was reused with different request data.")
        if workflow is None:
            legacy = store.get_idempotency_result(request.idempotency_key)
            if legacy is not None:
                if legacy["fingerprint"] != fingerprint:
                    raise IdempotencyConflict(
                        "Idempotency key was reused with different request data."
                    )
                return legacy["response"]

    if workflow is None:
        workflow_id = str(uuid4())
        try:
            store.create_workflow(
                workflow_id,
                request.idempotency_key,
                fingerprint,
                payload,
            )
        except sqlite3.IntegrityError:
            if request.idempotency_key is None:
                raise
            workflow = store.get_workflow_by_idempotency_key(request.idempotency_key)
            if workflow is None or workflow["request_fingerprint"] != fingerprint:
                raise IdempotencyConflict(
                    "Idempotency key was concurrently used for different request data."
                )
            workflow_id = workflow["id"]
    else:
        workflow_id = workflow["id"]

    return _drive_workflow(store, workflow_id)


def resume_workflow(store: Store, workflow_id: str) -> dict[str, Any]:
    workflow = store.get_workflow(workflow_id)
    if workflow is None:
        raise WorkflowNotFound(workflow_id)
    with workflow_stage("resume"):
        store.append_audit_event(
            "workflow.resume_requested",
            workflow_id,
            {"state": workflow["state"]},
        )
    return _drive_workflow(store, workflow_id)
