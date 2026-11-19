"""SwarmForge runtime: real agents, a shared event log, and a guarded control plane.

Omniscience  -> every state change is recorded as an event and every agent, task and
                metric can be inspected live.
Omnipotence  -> agents can be spawned, paused, resumed, scaled and given work at runtime.
                Irreversible actions (stopping agents, purging queues, recording revenue
                corrections) are proposed, not executed, until a human approves them.
"""
from __future__ import annotations

import asyncio
import itertools
import os
import resource
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

Handler = Callable[["Task"], Awaitable[Any]]

DEFAULT_ROLES = ("developer", "marketer", "analyst", "compliance")


# --------------------------------------------------------------------------- events
class EventLog:
    """Ring buffer of everything that happens, plus live fan-out to subscribers."""

    def __init__(self, maxlen: int = 2000) -> None:
        self._events: deque[dict] = deque(maxlen=maxlen)
        self._seq = itertools.count(1)
        self._subscribers: set[asyncio.Queue] = set()

    def emit(self, kind: str, **data: Any) -> dict:
        event = {"seq": next(self._seq), "ts": time.time(), "kind": kind, **data}
        self._events.append(event)
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass  # slow subscriber; it can catch up via /events?since=
        return event

    def since(self, seq: int = 0, kind: str | None = None, limit: int = 200) -> list[dict]:
        out = [e for e in self._events if e["seq"] > seq and (kind is None or e["kind"] == kind)]
        return out[-limit:]

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)


# --------------------------------------------------------------------------- tasks
@dataclass
class Task:
    role: str
    payload: dict
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: str = "queued"  # queued | running | done | failed | cancelled
    agent_id: str | None = None
    result: Any = None
    error: str | None = None
    created: float = field(default_factory=time.time)
    started: float | None = None
    finished: float | None = None

    def view(self) -> dict:
        return {k: getattr(self, k) for k in (
            "id", "role", "payload", "status", "agent_id", "result", "error",
            "created", "started", "finished")}


# --------------------------------------------------------------------------- agents
@dataclass
class Agent:
    role: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    state: str = "idle"  # idle | busy | paused | stopped
    completed: int = 0
    failed: int = 0
    current_task: str | None = None
    started: float = field(default_factory=time.time)
    _resume: asyncio.Event = field(default_factory=asyncio.Event, repr=False)
    _runner: asyncio.Task | None = field(default=None, repr=False)

    def view(self) -> dict:
        return {
            "id": self.id, "role": self.role, "state": self.state,
            "completed": self.completed, "failed": self.failed,
            "current_task": self.current_task, "uptime_s": round(time.time() - self.started, 1),
        }


async def _default_handler(task: Task) -> dict:
    """Built-in work: acknowledge and summarise the payload. Replace per role via
    Swarm.register_handler() to plug in real work (LLM calls, builds, reports...)."""
    await asyncio.sleep(float(task.payload.get("simulate_seconds", 0)))
    if task.payload.get("fail"):
        raise RuntimeError(str(task.payload["fail"]))
    return {"role": task.role, "handled": sorted(task.payload.keys())}


# --------------------------------------------------------------------------- swarm
class Swarm:
    def __init__(self) -> None:
        self.events = EventLog()
        self.agents: dict[str, Agent] = {}
        self.queues: dict[str, asyncio.Queue[Task]] = {}
        self.tasks: dict[str, Task] = {}
        self.handlers: dict[str, Handler] = {}
        self.approvals: dict[str, dict] = {}
        self.revenue_ledger: list[dict] = []
        self.started = time.time()

    # ---- lifecycle
    async def start(self, roles: tuple[str, ...] = DEFAULT_ROLES) -> None:
        for role in roles:
            self.spawn(role)
        self.events.emit("swarm.started", roles=list(roles))

    async def shutdown(self) -> None:
        for agent in list(self.agents.values()):
            await self._stop(agent.id)
        self.events.emit("swarm.shutdown")

    # ---- omnipotence: direct (reversible) powers
    def register_handler(self, role: str, handler: Handler) -> None:
        self.handlers[role] = handler

    def spawn(self, role: str) -> Agent:
        agent = Agent(role=role)
        agent._resume.set()
        self.queues.setdefault(role, asyncio.Queue())
        self.agents[agent.id] = agent
        agent._runner = asyncio.create_task(self._work(agent))
        self.events.emit("agent.spawned", agent_id=agent.id, role=role)
        return agent

    def scale(self, role: str, count: int) -> list[Agent]:
        """Grow a role up to `count` live agents. Shrinking is irreversible -> approval."""
        live = [a for a in self.agents.values() if a.role == role and a.state != "stopped"]
        return [self.spawn(role) for _ in range(max(0, count - len(live)))]

    def pause(self, agent_id: str) -> Agent:
        agent = self._agent(agent_id)
        agent._resume.clear()
        if agent.state != "busy":
            agent.state = "paused"
        self.events.emit("agent.paused", agent_id=agent_id)
        return agent

    def resume(self, agent_id: str) -> Agent:
        agent = self._agent(agent_id)
        agent._resume.set()
        if agent.state == "paused":
            agent.state = "idle"
        self.events.emit("agent.resumed", agent_id=agent_id)
        return agent

    def dispatch(self, role: str, payload: dict) -> Task:
        if role not in self.queues:
            raise KeyError(f"no agents for role '{role}'")
        task = Task(role=role, payload=payload)
        self.tasks[task.id] = task
        self.queues[role].put_nowait(task)
        self.events.emit("task.queued", task_id=task.id, role=role)
        return task

    def broadcast(self, payload: dict) -> list[Task]:
        return [self.dispatch(role, payload) for role in list(self.queues)]

    def cancel(self, task_id: str) -> Task:
        task = self.tasks[task_id]
        if task.status == "queued":
            task.status = "cancelled"
            self.events.emit("task.cancelled", task_id=task_id)
        return task

    # ---- omnipotence: irreversible powers go through human approval
    IRREVERSIBLE = {"stop_agent", "purge_queue", "record_revenue"}

    def propose(self, action: str, params: dict, reason: str = "") -> dict:
        if action not in self.IRREVERSIBLE:
            raise ValueError(f"unknown irreversible action '{action}'")
        if action == "stop_agent" and params.get("agent_id") not in self.agents:
            raise ValueError("stop_agent needs an existing 'agent_id'")
        if action == "purge_queue" and params.get("role") not in self.queues:
            raise ValueError("purge_queue needs an existing 'role'")
        if action == "record_revenue":
            try:
                float(params["amount"])
            except (KeyError, TypeError, ValueError):
                raise ValueError("record_revenue needs a numeric 'amount'") from None
        proposal = {"id": uuid.uuid4().hex[:10], "action": action, "params": params,
                    "reason": reason, "status": "pending", "created": time.time()}
        self.approvals[proposal["id"]] = proposal
        self.events.emit("approval.requested", approval_id=proposal["id"], action=action)
        return proposal

    async def decide(self, approval_id: str, approve: bool, by: str = "human") -> dict:
        proposal = self.approvals[approval_id]
        if proposal["status"] != "pending":
            raise ValueError(f"approval already {proposal['status']}")
        proposal.update(status="approved" if approve else "rejected", decided_by=by,
                        decided=time.time())
        self.events.emit(f"approval.{proposal['status']}", approval_id=approval_id, by=by)
        if approve:
            proposal["outcome"] = await self._execute(proposal["action"], proposal["params"])
        return proposal

    async def _execute(self, action: str, p: dict) -> Any:
        if action == "stop_agent":
            await self._stop(p["agent_id"])
            return {"stopped": p["agent_id"]}
        if action == "purge_queue":
            q, n = self.queues[p["role"]], 0
            while not q.empty():
                t = q.get_nowait()
                t.status = "cancelled"
                n += 1
            self.events.emit("queue.purged", role=p["role"], cancelled=n)
            return {"cancelled": n}
        if action == "record_revenue":
            entry = {"amount": float(p["amount"]), "source": p.get("source", "manual"),
                     "ts": time.time()}
            self.revenue_ledger.append(entry)
            self.events.emit("revenue.recorded", **entry)
            return entry
        raise ValueError(action)

    async def _stop(self, agent_id: str) -> None:
        agent = self._agent(agent_id)
        if agent._runner:
            agent._runner.cancel()
            try:
                await agent._runner
            except asyncio.CancelledError:
                pass
        agent.state = "stopped"
        self.events.emit("agent.stopped", agent_id=agent_id)

    # ---- omniscience
    def snapshot(self) -> dict:
        by_status: dict[str, int] = {}
        for t in self.tasks.values():
            by_status[t.status] = by_status.get(t.status, 0) + 1
        done = [t for t in self.tasks.values() if t.finished and t.started]
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return {
            "uptime_s": round(time.time() - self.started, 1),
            "agents": [a.view() for a in self.agents.values()],
            "queues": {r: q.qsize() for r, q in self.queues.items()},
            "tasks": {"total": len(self.tasks), "by_status": by_status,
                      "avg_runtime_s": round(sum(t.finished - t.started for t in done)
                                             / len(done), 4) if done else None},
            "approvals_pending": [a for a in self.approvals.values() if a["status"] == "pending"],
            "revenue": self.revenue(),
            "process": {"pid": os.getpid(), "max_rss_mb": round(usage.ru_maxrss / 1024, 1),
                        "cpu_user_s": round(usage.ru_utime, 2)},
            "last_event_seq": self.events.since(0, limit=1)[-1]["seq"] if self.events._events else 0,
        }

    def revenue(self) -> dict:
        """Only revenue that was actually recorded. No invented projections."""
        total = sum(e["amount"] for e in self.revenue_ledger)
        return {"recorded_total": round(total, 2), "entries": len(self.revenue_ledger),
                "projection": None if not self.revenue_ledger else
                self._monthly_run_rate()}

    def _monthly_run_rate(self) -> float | None:
        if len(self.revenue_ledger) < 2:
            return None
        span = self.revenue_ledger[-1]["ts"] - self.revenue_ledger[0]["ts"]
        if span <= 0:
            return None
        total = sum(e["amount"] for e in self.revenue_ledger)
        return round(total / span * 30 * 86400, 2)

    # ---- internals
    def _agent(self, agent_id: str) -> Agent:
        if agent_id not in self.agents:
            raise KeyError(f"no agent '{agent_id}'")
        return self.agents[agent_id]

    async def _work(self, agent: Agent) -> None:
        queue = self.queues[agent.role]
        while True:
            await agent._resume.wait()
            task = await queue.get()
            if task.status == "cancelled":
                continue
            if not agent._resume.is_set():  # paused while waiting: hand it back
                queue.put_nowait(task)
                continue
            agent.state, agent.current_task = "busy", task.id
            task.status, task.agent_id, task.started = "running", agent.id, time.time()
            self.events.emit("task.started", task_id=task.id, agent_id=agent.id)
            try:
                handler = self.handlers.get(agent.role, _default_handler)
                task.result = await handler(task)
                task.status = "done"
                agent.completed += 1
            except asyncio.CancelledError:
                task.status, task.error = "failed", "agent stopped"
                raise
            except Exception as exc:  # noqa: BLE001 - surface any handler failure
                task.status, task.error = "failed", f"{type(exc).__name__}: {exc}"
                agent.failed += 1
            finally:
                task.finished = time.time()
                agent.current_task = None
                agent.state = "idle" if agent._resume.is_set() else "paused"
                self.events.emit(f"task.{task.status}", task_id=task.id, agent_id=agent.id,
                                 error=task.error)
