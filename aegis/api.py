import sqlite3

from fastapi import FastAPI, HTTPException
from jsonschema.exceptions import ValidationError

from .agent_runtime import (
    EXPERT_CAPABILITIES,
    AgentContractError,
    AgentInputError,
    AgentPipelineRequest,
    AgentTask,
    execute_agent_task,
    execute_validation_pipeline,
)
from .engine import canonical_hash
from .experts import EXPERTS, route
from .models import TestRequest
from .policy import SCOPES, AuthorizationError
from .store import Store, WorkflowStateConflict
from .validation import validate_evidence_manifest
from .workflow import (
    IdempotencyConflict,
    WorkflowExecutionError,
    WorkflowNotFound,
    WorkflowRetryExhausted,
    process_run,
    resume_workflow,
)

app = FastAPI(
    title="AEGIS-MoE",
    version="0.6.0",
    description="Local-first policy-constrained security assurance foundation",
)
store = Store()


@app.get("/health")
def health():
    return {"status": "ok", "mode": "local-synthetic-only", "network_testing": False}


@app.get("/agents")
def agents():
    return {
        "agents": [
            {
                "name": e.name,
                "specialties": list(e.specialties),
                "mode": e.mode,
                "capabilities": sorted(
                    capability.value for capability in EXPERT_CAPABILITIES.get(e.name, ())
                ),
            }
            for e in EXPERTS
        ]
        + [
            {
                "name": name,
                "specialties": ["candidate_critique"],
                "mode": "deterministic",
                "capabilities": sorted(capability.value for capability in capabilities),
            }
            for name, capabilities in EXPERT_CAPABILITIES.items()
            if name not in {expert.name for expert in EXPERTS}
        ]
    }


@app.post("/agent-tasks")
async def run_agent_task(request: AgentTask):
    try:
        result = await execute_agent_task(request)
        return result.model_dump(mode="json")
    except AgentInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AgentContractError as exc:
        raise HTTPException(status_code=502, detail="Expert adapter violated its execution contract.") from exc


@app.post("/agent-pipelines/validate")
async def run_agent_validation_pipeline(request: AgentPipelineRequest):
    try:
        result = await execute_validation_pipeline(request)
        return result.model_dump(mode="json")
    except AgentInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AgentContractError as exc:
        raise HTTPException(
            status_code=502, detail="Expert pipeline violated its execution contract."
        ) from exc


@app.get("/routing/{task}")
def routing(task: str):
    if task not in {"run", "validate", "evaluate"}:
        raise HTTPException(status_code=404, detail="Unknown workflow task")
    return {"task": task, "sequence": route(task), "execution_mode": "deterministic"}


@app.get("/scope")
def scope():
    return {
        "scopes": [
            {
                "scope_id": s.scope_id,
                "environment": s.environment,
                "allowed_operations": sorted(s.allowed_operations),
                "max_batch_size": s.max_batch_size,
                "network_enabled": s.network_enabled,
            }
            for s in SCOPES.values()
        ]
    }


def _workflow_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AuthorizationError):
        return HTTPException(status_code=403, detail="Workflow scope is not authorized.")
    if isinstance(exc, IdempotencyConflict):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, WorkflowNotFound):
        return HTTPException(status_code=404, detail="Workflow not found.")
    if isinstance(exc, WorkflowStateConflict):
        return HTTPException(status_code=409, detail="Workflow state changed; inspect and resume.")
    if isinstance(exc, WorkflowRetryExhausted):
        return HTTPException(
            status_code=503,
            detail="Workflow retry budget exhausted; manual inspection is required.",
            headers={"X-Workflow-ID": exc.workflow_id},
        )
    if isinstance(exc, WorkflowExecutionError):
        return HTTPException(
            status_code=503,
            detail=f"Workflow {exc.stage} stage failed; retry or resume using the workflow ID.",
            headers={"X-Workflow-ID": exc.workflow_id},
        )
    return HTTPException(status_code=503, detail="Workflow could not be completed.")


@app.post("/runs")
def create_run(request: TestRequest):
    try:
        return process_run(store, request)
    except (
        AuthorizationError,
        IdempotencyConflict,
        WorkflowExecutionError,
        WorkflowRetryExhausted,
        WorkflowNotFound,
        WorkflowStateConflict,
    ) as exc:
        raise _workflow_http_error(exc) from exc
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=503, detail="Workflow persistence is temporarily unavailable."
        ) from exc


@app.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str):
    workflow = store.get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {
        "workflow_id": workflow["id"],
        "state": workflow["state"],
        "attempt_count": workflow["attempt_count"],
        "last_error_code": workflow["last_error_code"],
        "created_at": workflow["created_at"],
        "updated_at": workflow["updated_at"],
    }


@app.post("/workflows/{workflow_id}/resume")
def resume_workflow_endpoint(workflow_id: str):
    try:
        return resume_workflow(store, workflow_id)
    except (
        AuthorizationError,
        IdempotencyConflict,
        WorkflowExecutionError,
        WorkflowRetryExhausted,
        WorkflowNotFound,
        WorkflowStateConflict,
    ) as exc:
        raise _workflow_http_error(exc) from exc
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=503, detail="Workflow persistence is temporarily unavailable."
        ) from exc


@app.get("/runs/{run_id}")
def get_run(run_id: str):
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.get("/runs/{run_id}/replay")
def replay_run(run_id: str):
    stored = store.get_run(run_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Run not found")
    from .engine import execute_synthetic_run

    replayed, _, _ = execute_synthetic_run(
        stored["scope_id"], len(stored["observations"]), stored.get("seed", 7)
    )
    expected = stored.get("replay_fingerprint")
    actual = replayed.replay_fingerprint
    return {
        "run_id": run_id,
        "reproducible": expected is not None and expected == actual,
        "generator_version": replayed.generator_version,
        "expected_fingerprint": expected,
        "actual_fingerprint": actual,
    }


@app.get("/evidence/{evidence_id}")
def get_evidence(evidence_id: str):
    record = store.get_evidence(evidence_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return record


@app.get("/evidence/{evidence_id}/verify")
def verify_evidence(evidence_id: str):
    record = store.get_evidence(evidence_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Evidence not found")
    actual = canonical_hash(record["manifest"])
    try:
        validate_evidence_manifest(record["manifest"])
        schema_valid = True
    except ValidationError:
        schema_valid = False
    valid = schema_valid and actual == record["payload_sha256"]
    return {
        "evidence_id": evidence_id,
        "valid": valid,
        "schema_valid": schema_valid,
        "algorithm": "sha256",
        "expected_sha256": record["payload_sha256"],
        "actual_sha256": actual,
    }


@app.get("/findings")
def get_findings():
    return {"findings": store.list_findings()}


@app.get("/metrics")
def metrics():
    counts = store.counts()
    findings = store.list_findings()
    return {
        **counts,
        "validated_findings": sum(1 for f in findings if f["state"] == "validated"),
        "false_positive_findings": sum(1 for f in findings if f["state"] == "false_positive"),
    }
