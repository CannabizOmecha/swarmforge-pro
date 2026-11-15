from __future__ import annotations
import hashlib, json, sqlite3, time, uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

class TaskState(str, Enum):
    PROPOSED="proposed"; APPROVAL_REQUIRED="approval_required"; AUTHORIZED="authorized"
    RUNNING="running"; EVALUATING="evaluating"; COMPLETED="completed"; REJECTED="rejected"; FAILED="failed"
class Risk(str, Enum):
    LOW="low"; MEDIUM="medium"; HIGH="high"; CRITICAL="critical"
class GovernanceError(RuntimeError): pass

@dataclass(frozen=True)
class TaskRequest:
    title:str; objective:str; project_id:str; agent_role:str="planner"; risk:Risk=Risk.LOW
    estimated_cost_usd:float=0.0; requires_external_side_effect:bool=False
    idempotency_key:str=""; metadata:dict[str,Any]=field(default_factory=dict)
    def validate(self):
        if not self.title.strip() or not self.objective.strip() or not self.project_id.strip(): raise ValueError("title, objective, project_id required")
        if self.estimated_cost_usd<0: raise ValueError("negative cost")
        if self.estimated_cost_usd>0 and self.requires_external_side_effect: raise ValueError("paid external side effects require separate approval")

class Store:
    def __init__(self,path:str|Path="asya.sqlite3"):
        self.path=str(path)
        with self.connect() as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,idempotency_key TEXT UNIQUE,state TEXT NOT NULL,payload TEXT NOT NULL,result TEXT,created_at REAL NOT NULL,updated_at REAL NOT NULL)")
            c.execute("CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT,task_id TEXT NOT NULL,event_type TEXT NOT NULL,actor TEXT NOT NULL,payload TEXT NOT NULL,created_at REAL NOT NULL,previous_hash TEXT NOT NULL,event_hash TEXT NOT NULL)")
    def connect(self):
        c=sqlite3.connect(self.path); c.row_factory=sqlite3.Row; return c
    def event(self,task_id,event_type,actor,payload):
        with self.connect() as c:
            row=c.execute("SELECT event_hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
            prev=row["event_hash"] if row else "GENESIS"; now=time.time()
            body=json.dumps(dict(task_id=task_id,event_type=event_type,actor=actor,payload=payload,created_at=now,previous_hash=prev),sort_keys=True,separators=(",",":"))
            digest=hashlib.sha256(body.encode()).hexdigest()
            c.execute("INSERT INTO events(task_id,event_type,actor,payload,created_at,previous_hash,event_hash) VALUES(?,?,?,?,?,?,?)",(task_id,event_type,actor,json.dumps(payload,sort_keys=True),now,prev,digest))
        return digest
    def create(self,req,state):
        req.validate(); key=req.idempotency_key or str(uuid.uuid4())
        with self.connect() as c:
            old=c.execute("SELECT id FROM tasks WHERE idempotency_key=?",(key,)).fetchone()
            if old: return old["id"],False
            tid=str(uuid.uuid4()); now=time.time(); payload={**asdict(req),"risk":req.risk.value}
            c.execute("INSERT INTO tasks(id,idempotency_key,state,payload,created_at,updated_at) VALUES(?,?,?,?,?,?)",(tid,key,state.value,json.dumps(payload,sort_keys=True),now,now))
        self.event(tid,"task_created","system",{"state":state.value,"title":req.title}); return tid,True
    def get(self,tid):
        with self.connect() as c: row=c.execute("SELECT * FROM tasks WHERE id=?",(tid,)).fetchone()
        if not row:return None
        d=dict(row); d["payload"]=json.loads(d["payload"]); d["result"]=json.loads(d["result"]) if d["result"] else None; return d
    def transition(self,tid,new,actor,result=None):
        allowed={TaskState.PROPOSED:{TaskState.APPROVAL_REQUIRED,TaskState.AUTHORIZED,TaskState.REJECTED},TaskState.APPROVAL_REQUIRED:{TaskState.AUTHORIZED,TaskState.REJECTED},TaskState.AUTHORIZED:{TaskState.RUNNING,TaskState.REJECTED},TaskState.RUNNING:{TaskState.EVALUATING,TaskState.FAILED},TaskState.EVALUATING:{TaskState.COMPLETED,TaskState.FAILED}}
        with self.connect() as c:
            row=c.execute("SELECT state FROM tasks WHERE id=?",(tid,)).fetchone()
            if not row:raise KeyError(tid)
            old=TaskState(row["state"])
            if new not in allowed.get(old,set()):raise GovernanceError(f"invalid transition {old.value}->{new.value}")
            c.execute("UPDATE tasks SET state=?,result=?,updated_at=? WHERE id=?",(new.value,json.dumps(result,sort_keys=True) if result is not None else None,time.time(),tid))
        self.event(tid,"state_transition",actor,{"from":old.value,"to":new.value,"result":result or {}})
    def verify_chain(self):
        with self.connect() as c: rows=c.execute("SELECT * FROM events ORDER BY seq").fetchall()
        prev="GENESIS"
        for r in rows:
            body=json.dumps(dict(task_id=r["task_id"],event_type=r["event_type"],actor=r["actor"],payload=json.loads(r["payload"]),created_at=r["created_at"],previous_hash=prev),sort_keys=True,separators=(",",":"))
            digest=hashlib.sha256(body.encode()).hexdigest()
            if r["previous_hash"]!=prev or r["event_hash"]!=digest:return False
            prev=digest
        return True

class GovernanceKernel:
    def __init__(self,store:Store,max_task_cost_usd:float=0.0):self.store=store;self.max_task_cost_usd=max_task_cost_usd
    def submit(self,req):
        req.validate()
        if req.estimated_cost_usd>self.max_task_cost_usd:raise GovernanceError("task exceeds cost ceiling")
        approval=req.risk in {Risk.HIGH,Risk.CRITICAL} or req.requires_external_side_effect
        tid,created=self.store.create(req,TaskState.APPROVAL_REQUIRED if approval else TaskState.AUTHORIZED)
        return {"task_id":tid,"state":self.store.get(tid)["state"],"created":created,"approval_required":approval}
    def approve(self,tid,approver,explicit_authorization):
        if not explicit_authorization or not approver.strip():raise GovernanceError("named human authorization required")
        self.store.transition(tid,TaskState.AUTHORIZED,approver)
    def execute_local(self,tid,executor,artifact):
        task=self.store.get(tid)
        if not task or task["state"]!=TaskState.AUTHORIZED.value:raise GovernanceError("only authorized tasks may execute")
        self.store.transition(tid,TaskState.RUNNING,executor); self.store.transition(tid,TaskState.EVALUATING,"evidence_gate")
        passed=bool(artifact.get("acceptance_criteria") and artifact.get("tests_passed") is True and artifact.get("evidence_ref"))
        result={"evaluation":"passed" if passed else "failed","artifact":artifact,"evaluator":"local_evidence_contract_gate","independent_verification":False}
        self.store.transition(tid,TaskState.COMPLETED if passed else TaskState.FAILED,"independent_evaluator",result); return result
