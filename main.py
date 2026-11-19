"""SwarmForge API. Runs a real expert swarm; nothing is hardcoded or simulated unless SWARMFORGE_DEMO=1."""
import os
import threading

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from swarmforge import AuditLog, ClaudeLLM, FakeLLM, Swarm
from swarmforge.schemas import RunResult, RunStatus
from swarmforge.swarm import MAX_GOAL_CHARS

DEMO = os.getenv("SWARMFORGE_DEMO") == "1"
audit = AuditLog(os.getenv("SWARMFORGE_AUDIT", "audit/log.jsonl"))
swarm = Swarm(FakeLLM() if DEMO else ClaudeLLM(), audit)
runs: dict[str, RunResult] = {}
_lock = threading.Lock()

app = FastAPI(title="SwarmForge", version="3.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
                   allow_methods=["GET", "POST"], allow_headers=["*"])


class RunRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=MAX_GOAL_CHARS)


class Decision(BaseModel):
    approve: bool
    note: str = Field(default="", max_length=2000)


@app.get("/")
def dashboard():
    return FileResponse(os.path.join(os.path.dirname(__file__), "dashboard.html"))


@app.get("/health")
def health():
    return {"ok": True, "mode": "demo" if DEMO else "live", "audit_intact": audit.verify()}


@app.post("/runs", response_model=RunResult)
def create_run(req: RunRequest):
    try:
        res = swarm.run(req.goal)
    except ValueError as e:
        raise HTTPException(422, str(e))
    with _lock:
        runs[res.id] = res
    return res


@app.get("/runs/{run_id}", response_model=RunResult)
def get_run(run_id: str):
    if run_id not in runs:
        raise HTTPException(404, "run not found")
    return runs[run_id]


@app.post("/runs/{run_id}/decision", response_model=RunResult)
def decide(run_id: str, d: Decision):
    with _lock:
        res = runs.get(run_id)
        if res is None:
            raise HTTPException(404, "run not found")
        if res.status != RunStatus.awaiting_approval:
            raise HTTPException(409, f"run is {res.status.value}, not awaiting approval")
        res.status = RunStatus.approved if d.approve else RunStatus.rejected
        res.decided_by = "human"
    audit.append("human_decision", {"id": run_id, "approve": d.approve, "note": d.note})
    return res


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
