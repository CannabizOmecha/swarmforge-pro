import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from swarm import Swarm

swarm = Swarm()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await swarm.start()
    yield
    await swarm.shutdown()


app = FastAPI(title="SwarmForge Pro", version="3.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    """Control-plane guard. Set SWARMFORGE_ADMIN_TOKEN in any shared deployment."""
    expected = os.environ.get("SWARMFORGE_ADMIN_TOKEN")
    if expected and x_admin_token != expected:
        raise HTTPException(401, "missing or invalid X-Admin-Token")


def _or_404(fn, *args):
    try:
        return fn(*args)
    except KeyError as exc:
        raise HTTPException(404, str(exc).strip("'\"")) from exc


# ------------------------------------------------------------------ request models
class TaskIn(BaseModel):
    role: str
    payload: dict = Field(default_factory=dict)


class ScaleIn(BaseModel):
    count: int = Field(ge=0, le=64)


class ProposalIn(BaseModel):
    action: str
    params: dict = Field(default_factory=dict)
    reason: str = ""


class DecisionIn(BaseModel):
    approve: bool
    by: str = "human"


# ------------------------------------------------------------------ legacy routes
@app.get("/")
def home():
    return {"SwarmForge": "Pro 3.0 LIVE", "dashboard": "/dashboard", "docs": "/docs"}


@app.post("/deploy")
async def deploy():
    """Kept for the old dashboard: reports real agent state instead of fixed strings."""
    snap = swarm.snapshot()
    live = [a for a in snap["agents"] if a["state"] != "stopped"]
    return {
        "status": "SUCCESS" if live else "DEGRADED",
        "agents": {a["role"]: a["state"] for a in live},
        "revenue": snap["revenue"],
    }


@app.get("/revenue")
async def revenue():
    return swarm.revenue()


@app.get("/dashboard")
def dashboard():
    return FileResponse(Path(__file__).with_name("dashboard.html"))


# ------------------------------------------------------------------ omniscience
@app.get("/health")
async def health():
    snap = swarm.snapshot()
    live = sum(a["state"] != "stopped" for a in snap["agents"])
    return {"ok": live > 0, "live_agents": live, "uptime_s": snap["uptime_s"]}


@app.get("/omniscience/state")
async def state():
    return swarm.snapshot()


@app.get("/omniscience/agents/{agent_id}")
async def agent(agent_id: str):
    return _or_404(swarm._agent, agent_id).view()


@app.get("/omniscience/tasks")
async def tasks(status: str | None = None, role: str | None = None, limit: int = 100):
    items = [t.view() for t in swarm.tasks.values()
             if (status is None or t.status == status) and (role is None or t.role == role)]
    return items[-limit:]


@app.get("/omniscience/tasks/{task_id}")
async def task(task_id: str):
    return _or_404(swarm.tasks.__getitem__, task_id).view()


@app.get("/omniscience/events")
async def events(since: int = 0, kind: str | None = None, limit: int = 200):
    return swarm.events.since(since, kind, limit)


@app.get("/omniscience/stream")
async def stream():
    """Server-Sent Events: every swarm event, live."""
    q = swarm.events.subscribe()

    async def gen():
        try:
            yield f"data: {json.dumps({'kind': 'stream.open'})}\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=15)
                    yield f"data: {json.dumps(event, default=str)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            swarm.events.unsubscribe(q)

    return StreamingResponse(gen(), media_type="text/event-stream")


# ------------------------------------------------------------------ omnipotence
admin = [Depends(require_admin)]


@app.post("/omnipotence/tasks", dependencies=admin, status_code=202)
async def dispatch(body: TaskIn):
    return _or_404(swarm.dispatch, body.role, body.payload).view()


@app.post("/omnipotence/broadcast", dependencies=admin, status_code=202)
async def broadcast(body: dict):
    return [t.view() for t in swarm.broadcast(body)]


@app.post("/omnipotence/tasks/{task_id}/cancel", dependencies=admin)
async def cancel(task_id: str):
    return _or_404(swarm.cancel, task_id).view()


@app.post("/omnipotence/agents/{role}", dependencies=admin, status_code=201)
async def spawn(role: str):
    return swarm.spawn(role).view()


@app.post("/omnipotence/roles/{role}/scale", dependencies=admin)
async def scale(role: str, body: ScaleIn):
    return {"spawned": [a.view() for a in swarm.scale(role, body.count)],
            "note": "scaling down stops agents; propose 'stop_agent' for each instead"}


@app.post("/omnipotence/agents/{agent_id}/pause", dependencies=admin)
async def pause(agent_id: str):
    return _or_404(swarm.pause, agent_id).view()


@app.post("/omnipotence/agents/{agent_id}/resume", dependencies=admin)
async def resume(agent_id: str):
    return _or_404(swarm.resume, agent_id).view()


# Irreversible actions: propose -> a human approves -> executed.
@app.post("/omnipotence/proposals", dependencies=admin, status_code=202)
async def propose(body: ProposalIn):
    try:
        return swarm.propose(body.action, body.params, body.reason)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/omnipotence/proposals")
async def proposals(status: str | None = None):
    return [p for p in swarm.approvals.values() if status is None or p["status"] == status]


@app.post("/omnipotence/proposals/{approval_id}/decide", dependencies=admin)
async def decide(approval_id: str, body: DecisionIn):
    if approval_id not in swarm.approvals:
        raise HTTPException(404, f"no proposal '{approval_id}'")
    try:
        return await swarm.decide(approval_id, body.approve, body.by)
    except (ValueError, KeyError) as exc:
        raise HTTPException(409, str(exc)) from exc


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
