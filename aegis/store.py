from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .models import EvidenceRecord, Finding, RunRecord

WORKFLOW_TRANSITIONS = {
    "accepted": {"authorized", "rejected"},
    "authorized": {"executed", "exhausted"},
    "executed": {"committed"},
    "rejected": set(),
    "exhausted": set(),
    "committed": set(),
}

AUDIT_GENESIS = "0" * 64
AUDIT_EVENT_TYPES = frozenset(
    {
        "workflow.accepted",
        "workflow.state_transition",
        "workflow.attempt_started",
        "workflow.execution_failed",
        "workflow.exhausted",
        "workflow.rejected",
        "workflow.committed",
        "workflow.resume_requested",
        "run.bundle_saved",
        "agent.task.completed",
        "agent.task.abstained",
        "agent.task.rejected",
        "agent.pipeline.completed",
        "agent.pipeline.abstained",
        "agent.pipeline.rejected",
    }
)


class WorkflowStateConflict(RuntimeError):
    """Raised when a checkpoint transition loses its compare-and-set race."""


class Store:
    """Transactional SQLite store for the single-node synthetic MVP."""

    def __init__(self, path: str = "data/aegis.sqlite3"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _init(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode = WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS findings (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS evidence (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS idempotency (
                    key TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    response_payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    idempotency_key TEXT UNIQUE,
                    request_fingerprint TEXT NOT NULL,
                    request_payload TEXT NOT NULL,
                    state TEXT NOT NULL,
                    stage_payload TEXT,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    last_error_code TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    sequence INTEGER PRIMARY KEY,
                    event_id TEXT NOT NULL UNIQUE,
                    event_type TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS audit_events_no_update
                BEFORE UPDATE ON audit_events
                BEGIN
                    SELECT RAISE(ABORT, 'audit events are append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS audit_events_no_delete
                BEFORE DELETE ON audit_events
                BEGIN
                    SELECT RAISE(ABORT, 'audit events are append-only');
                END;
            """)

    @staticmethod
    def _audit_hash(
        sequence: int,
        event_id: str,
        event_type: str,
        subject_id: str,
        payload: str,
        previous_hash: str,
        created_at: str,
    ) -> str:
        canonical = json.dumps(
            {
                "sequence": sequence,
                "event_id": event_id,
                "event_type": event_type,
                "subject_id": subject_id,
                "payload": payload,
                "previous_hash": previous_hash,
                "created_at": created_at,
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def _append_audit_event(
        self,
        db: sqlite3.Connection,
        event_type: str,
        subject_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if event_type not in AUDIT_EVENT_TYPES:
            raise ValueError("Unsupported audit event type.")
        if not subject_id or len(subject_id) > 128:
            raise ValueError("Audit subject identifier is invalid.")
        encoded_payload = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        if len(encoded_payload.encode("utf-8")) > 4096:
            raise ValueError("Audit event payload exceeds its size budget.")
        if not db.in_transaction:
            db.execute("BEGIN IMMEDIATE")
        last = db.execute(
            "SELECT sequence, event_hash FROM audit_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        sequence = 1 if last is None else int(last["sequence"]) + 1
        previous_hash = AUDIT_GENESIS if last is None else last["event_hash"]
        event_id = str(uuid4())
        created_at = datetime.now(UTC).isoformat()
        event_hash = self._audit_hash(
            sequence,
            event_id,
            event_type,
            subject_id,
            encoded_payload,
            previous_hash,
            created_at,
        )
        db.execute(
            """
            INSERT INTO audit_events (
                sequence, event_id, event_type, subject_id, payload,
                previous_hash, event_hash, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sequence,
                event_id,
                event_type,
                subject_id,
                encoded_payload,
                previous_hash,
                event_hash,
                created_at,
            ),
        )
        return {
            "sequence": sequence,
            "event_id": event_id,
            "event_type": event_type,
            "subject_id": subject_id,
            "payload": payload,
            "previous_hash": previous_hash,
            "event_hash": event_hash,
            "created_at": created_at,
        }

    def append_audit_event(
        self, event_type: str, subject_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        with self._connect() as db:
            return self._append_audit_event(db, event_type, subject_id, payload)

    def verify_audit_chain(self) -> dict[str, Any]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM audit_events ORDER BY sequence ASC"
            ).fetchall()
        previous_hash = AUDIT_GENESIS
        verified_count = 0
        expected_sequence = 1
        for row in rows:
            sequence = int(row["sequence"])
            if sequence != expected_sequence:
                return {
                    "valid": False,
                    "event_count": len(rows),
                    "verified_count": verified_count,
                    "failed_sequence": sequence,
                    "reason": "sequence_gap",
                }
            if row["previous_hash"] != previous_hash:
                return {
                    "valid": False,
                    "event_count": len(rows),
                    "verified_count": verified_count,
                    "failed_sequence": sequence,
                    "reason": "previous_hash_mismatch",
                }
            expected = self._audit_hash(
                sequence,
                row["event_id"],
                row["event_type"],
                row["subject_id"],
                row["payload"],
                row["previous_hash"],
                row["created_at"],
            )
            if expected != row["event_hash"]:
                return {
                    "valid": False,
                    "event_count": len(rows),
                    "verified_count": verified_count,
                    "failed_sequence": sequence,
                    "reason": "event_hash_mismatch",
                }
            previous_hash = row["event_hash"]
            verified_count += 1
            expected_sequence += 1
        return {
            "valid": True,
            "event_count": len(rows),
            "verified_count": verified_count,
            "failed_sequence": None,
            "reason": None,
            "last_hash": previous_hash,
        }

    def list_audit_events(self, limit: int = 100) -> list[dict[str, Any]]:
        if limit < 1 or limit > 500:
            raise ValueError("Audit event limit must be between 1 and 500.")
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM audit_events ORDER BY sequence DESC LIMIT ?", (limit,)
            ).fetchall()
        events = []
        for row in rows:
            event = dict(row)
            event["payload"] = json.loads(event["payload"])
            events.append(event)
        return events

    def create_workflow(
        self,
        workflow_id: str,
        idempotency_key: str | None,
        request_fingerprint: str,
        request_payload: dict[str, Any],
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO workflows (
                    id, idempotency_key, request_fingerprint, request_payload,
                    state, stage_payload, attempt_count, last_error_code,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'accepted', NULL, 0, NULL, ?, ?)
                """,
                (
                    workflow_id,
                    idempotency_key,
                    request_fingerprint,
                    json.dumps(request_payload, sort_keys=True, separators=(",", ":")),
                    now,
                    now,
                ),
            )
            self._append_audit_event(
                db,
                "workflow.accepted",
                workflow_id,
                {"state": "accepted", "request_fingerprint": request_fingerprint},
            )

    @staticmethod
    def _workflow_payload(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        result = dict(row)
        result["request_payload"] = json.loads(result["request_payload"])
        if result["stage_payload"] is not None:
            result["stage_payload"] = json.loads(result["stage_payload"])
        return result

    def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM workflows WHERE id=?", (workflow_id,)).fetchone()
        return self._workflow_payload(row)

    def get_workflow_by_idempotency_key(self, key: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM workflows WHERE idempotency_key=?", (key,)
            ).fetchone()
        return self._workflow_payload(row)

    def transition_workflow(
        self,
        workflow_id: str,
        expected_state: str,
        next_state: str,
        stage_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if next_state not in WORKFLOW_TRANSITIONS.get(expected_state, set()):
            raise ValueError(f"Invalid workflow transition: {expected_state} -> {next_state}")
        encoded_payload = (
            json.dumps(stage_payload, sort_keys=True, separators=(",", ":"))
            if stage_payload is not None
            else None
        )
        now = datetime.now(UTC).isoformat()
        with self._connect() as db:
            cursor = db.execute(
                """
                UPDATE workflows
                SET state=?, stage_payload=COALESCE(?, stage_payload),
                    last_error_code=NULL, updated_at=?
                WHERE id=? AND state=?
                """,
                (next_state, encoded_payload, now, workflow_id, expected_state),
            )
            if cursor.rowcount == 1:
                self._append_audit_event(
                    db,
                    "workflow.state_transition",
                    workflow_id,
                    {"from_state": expected_state, "to_state": next_state},
                )
            else:
                row = db.execute(
                    "SELECT state FROM workflows WHERE id=?", (workflow_id,)
                ).fetchone()
                if row is None or row["state"] != next_state:
                    raise WorkflowStateConflict(
                        f"Workflow {workflow_id} was not in expected state {expected_state}."
                    )
        result = self.get_workflow(workflow_id)
        if result is None:
            raise WorkflowStateConflict(f"Workflow {workflow_id} disappeared.")
        return result

    def begin_workflow_attempt(self, workflow_id: str) -> int:
        now = datetime.now(UTC).isoformat()
        exhausted = False
        attempt_count = 0
        with self._connect() as db:
            cursor = db.execute(
                """
                UPDATE workflows
                SET attempt_count=attempt_count+1, updated_at=?
                WHERE id=? AND state='authorized' AND attempt_count < 3
                """,
                (now, workflow_id),
            )
            if cursor.rowcount == 1:
                row = db.execute(
                    "SELECT attempt_count FROM workflows WHERE id=?", (workflow_id,)
                ).fetchone()
                attempt_count = int(row["attempt_count"])
                self._append_audit_event(
                    db,
                    "workflow.attempt_started",
                    workflow_id,
                    {"attempt_count": attempt_count},
                )
            else:
                row = db.execute(
                    "SELECT state, attempt_count FROM workflows WHERE id=?", (workflow_id,)
                ).fetchone()
                if row is not None and row["state"] == "authorized" and row["attempt_count"] >= 3:
                    db.execute(
                        """
                        UPDATE workflows
                        SET state='exhausted', last_error_code='retry_budget_exhausted',
                            updated_at=?
                        WHERE id=? AND state='authorized'
                        """,
                        (now, workflow_id),
                    )
                    self._append_audit_event(
                        db,
                        "workflow.exhausted",
                        workflow_id,
                        {"attempt_count": int(row["attempt_count"]), "reason": "retry_budget_exhausted"},
                    )
                    exhausted = True
                else:
                    raise WorkflowStateConflict(
                        f"Workflow {workflow_id} cannot start another execution attempt."
                    )
        if exhausted:
            raise WorkflowStateConflict(
                f"Workflow {workflow_id} exhausted its execution retry budget."
            )
        return attempt_count

    def record_workflow_failure(self, workflow_id: str, error_code: str) -> dict[str, Any]:
        now = datetime.now(UTC).isoformat()
        with self._connect() as db:
            db.execute(
                """
                UPDATE workflows
                SET state=CASE WHEN attempt_count >= 3 THEN 'exhausted' ELSE state END,
                    last_error_code=?, updated_at=?
                WHERE id=? AND state='authorized'
                """,
                (error_code, now, workflow_id),
            )
            row = db.execute(
                "SELECT state, attempt_count FROM workflows WHERE id=?", (workflow_id,)
            ).fetchone()
            if row is not None:
                self._append_audit_event(
                    db,
                    "workflow.execution_failed",
                    workflow_id,
                    {"error_code": error_code, "state": row["state"], "attempt_count": row["attempt_count"]},
                )
                if row["state"] == "exhausted":
                    self._append_audit_event(
                        db,
                        "workflow.exhausted",
                        workflow_id,
                        {"attempt_count": row["attempt_count"], "reason": error_code},
                    )
        result = self.get_workflow(workflow_id)
        if result is None:
            raise WorkflowStateConflict(f"Workflow {workflow_id} disappeared.")
        return result

    def reject_workflow(self, workflow_id: str) -> dict[str, Any]:
        now = datetime.now(UTC).isoformat()
        with self._connect() as db:
            cursor = db.execute(
                """
                UPDATE workflows
                SET state='rejected', last_error_code='authorization_denied', updated_at=?
                WHERE id=? AND state='accepted'
                """,
                (now, workflow_id),
            )
            if cursor.rowcount == 1:
                self._append_audit_event(
                    db,
                    "workflow.rejected",
                    workflow_id,
                    {"state": "rejected", "reason": "authorization_denied"},
                )
            else:
                row = db.execute(
                    "SELECT state FROM workflows WHERE id=?", (workflow_id,)
                ).fetchone()
                if row is None or row["state"] != "rejected":
                    raise WorkflowStateConflict("Workflow authorization state changed.")
        result = self.get_workflow(workflow_id)
        if result is None:
            raise WorkflowStateConflict(f"Workflow {workflow_id} disappeared.")
        return result

    def save_bundle(
        self,
        run: RunRecord,
        findings: list[Finding],
        evidence: list[EvidenceRecord],
        *,
        idempotency_key: str | None = None,
        request_fingerprint: str | None = None,
        response_payload: dict[str, Any] | None = None,
        workflow_id: str | None = None,
    ):
        """Persist run outputs and workflow completion in one transaction."""
        if idempotency_key is not None and (
            request_fingerprint is None or response_payload is None
        ):
            raise ValueError("Idempotency metadata must be complete.")
        if workflow_id is not None and response_payload is None:
            raise ValueError("Workflow completion requires a response payload.")

        with self._connect() as db:
            db.execute("INSERT INTO runs VALUES (?, ?)", (run.run_id, run.model_dump_json()))
            db.executemany(
                "INSERT INTO findings VALUES (?, ?)",
                [(item.finding_id, item.model_dump_json()) for item in findings],
            )
            db.executemany(
                "INSERT INTO evidence VALUES (?, ?)",
                [(item.evidence_id, item.model_dump_json()) for item in evidence],
            )
            self._append_audit_event(
                db,
                "run.bundle_saved",
                run.run_id,
                {"finding_count": len(findings), "evidence_count": len(evidence)},
            )
            if idempotency_key is not None:
                db.execute(
                    "INSERT INTO idempotency VALUES (?, ?, ?)",
                    (
                        idempotency_key,
                        request_fingerprint,
                        json.dumps(response_payload, sort_keys=True, separators=(",", ":")),
                    ),
                )
            if workflow_id is not None:
                now = datetime.now(UTC).isoformat()
                cursor = db.execute(
                    """
                    UPDATE workflows
                    SET state='committed', stage_payload=?, last_error_code=NULL, updated_at=?
                    WHERE id=? AND state='executed'
                    """,
                    (
                        json.dumps(response_payload, sort_keys=True, separators=(",", ":")),
                        now,
                        workflow_id,
                    ),
                )
                if cursor.rowcount != 1:
                    raise WorkflowStateConflict(
                        f"Workflow {workflow_id} is not ready for atomic commit."
                    )
                self._append_audit_event(
                    db,
                    "workflow.committed",
                    workflow_id,
                    {"run_id": run.run_id, "finding_count": len(findings), "evidence_count": len(evidence)},
                )

    def get_idempotency_result(self, key: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT fingerprint, response_payload FROM idempotency WHERE key=?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        return {
            "fingerprint": row["fingerprint"],
            "response": json.loads(row["response_payload"]),
        }

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT payload FROM runs WHERE id=?", (run_id,)).fetchone()
        return json.loads(row["payload"]) if row else None

    def get_evidence(self, evidence_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT payload FROM evidence WHERE id=?", (evidence_id,)).fetchone()
        return json.loads(row["payload"]) if row else None

    def list_findings(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT payload FROM findings ORDER BY rowid DESC").fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def counts(self) -> dict[str, int]:
        with self._connect() as db:
            return {
                "runs": db.execute("SELECT count(*) FROM runs").fetchone()[0],
                "findings": db.execute("SELECT count(*) FROM findings").fetchone()[0],
                "evidence": db.execute("SELECT count(*) FROM evidence").fetchone()[0],
                "workflows": db.execute("SELECT count(*) FROM workflows").fetchone()[0],
                "audit_events": db.execute("SELECT count(*) FROM audit_events").fetchone()[0],
            }
