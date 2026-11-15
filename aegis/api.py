from fastapi import FastAPI, HTTPException
from jsonschema.exceptions import ValidationError

from .engine import canonical_hash, execute_synthetic_run
from .experts import EXPERTS, route
from .models import TestRequest
from .policy import SCOPES, AuthorizationError
from .store import Store
from .validation import validate_evidence_manifest

app = FastAPI(
    title="AEGIS-MoE",
    version="0.3.0",
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
            {"name": e.name, "specialties": list(e.specialties), "mode": e.mode}
            for e in EXPERTS
        ]
    }


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


@app.post("/runs")
def create_run(request: TestRequest):
    try:
        run, findings, evidence = execute_synthetic_run(
            request.scope_id, request.batch_size, request.seed
        )
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    store.save_bundle(run, findings, evidence)
    return {
        "run": run.model_dump(mode="json"),
        "findings": [f.model_dump(mode="json") for f in findings],
        "evidence": [e.model_dump(mode="json") for e in evidence],
    }


@app.get("/runs/{run_id}")
def get_run(run_id: str):
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


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
