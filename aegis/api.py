from fastapi import FastAPI, HTTPException

from .engine import execute_synthetic_run
from .experts import EXPERTS
from .models import TestRequest
from .policy import AuthorizationError, SCOPES
from .store import Store

app = FastAPI(title="AEGIS-MoE", version="0.1.0", description="Local-first policy-constrained security assurance foundation")
store = Store()


@app.get("/health")
def health():
    return {"status": "ok", "mode": "local-synthetic-only", "network_testing": False}


@app.get("/agents")
def agents():
    return {"agents": [{"name": e.name, "specialties": list(e.specialties), "mode": e.mode} for e in EXPERTS]}


@app.get("/scope")
def scope():
    return {"scopes": [{"scope_id": s.scope_id, "environment": s.environment, "allowed_operations": sorted(s.allowed_operations), "max_batch_size": s.max_batch_size, "network_enabled": s.network_enabled} for s in SCOPES.values()]}


@app.post("/runs")
def create_run(request: TestRequest):
    try:
        run, findings, evidence = execute_synthetic_run(request.scope_id, request.batch_size, request.seed)
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    store.save_run(run)
    for finding in findings:
        store.save_finding(finding)
    for record in evidence:
        store.save_evidence(record)
    return {"run": run.model_dump(mode="json"), "findings": [f.model_dump(mode="json") for f in findings], "evidence": [e.model_dump(mode="json") for e in evidence]}


@app.get("/runs/{run_id}")
def get_run(run_id: str):
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.get("/findings")
def get_findings():
    return {"findings": store.list_findings()}


@app.get("/metrics")
def metrics():
    counts = store.counts()
    return {**counts, "validated_findings": sum(1 for f in store.list_findings() if f["state"] == "validated")}
