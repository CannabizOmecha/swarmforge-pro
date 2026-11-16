from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from typing import Any

from .models import EvidenceRecord, Finding, RunRecord


WORKFLOW_TRANSITIONS = {
    "accepted": {"authorized", "rejected"},
    "authorized": {"executed", "exhausted"},
    "executed": {"committed"},
    "rejected": set(),
    "exhausted": set(),
    "committed": set(),
}


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
            """)

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
            if cursor.rowcount != 1:
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
            if cursor.rowcount != 1:
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
            }
